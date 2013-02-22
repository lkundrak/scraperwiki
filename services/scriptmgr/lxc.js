/**********************************************************************
* lxc.js
*
* An abstraction of an execution engine, using LXC instances to
* run code.
*
* We make sure at initialisation that all of the LXCs that we
* expect are created and running.
* 
**********************************************************************/
var _    = require('underscore')._;
var mu   = require('mu');
var fs   = require('fs');
var spawn = require('child_process').spawn;
var path  = require('path');
var util  = require( path.join(__dirname,'utils.js') );

// All of our virtual machines
var vms = [ ]; // vm name -> objects

var vms_by_ip    = [ ]; // maps of ip -> vm name
var vms_by_runid = [ ]; // maps of runid -> vm name

var root_folder = '';

var config_tpl = '';
var fstab_tpl  = '';


/**********************************************************************
* Initialise the LXC handling by storing some properties and caching
* some templates (only until we have created the relevant config
* files).
**********************************************************************/
exports.init = function(start, count, lxc_root_folder, settings_) {
	root_folder = lxc_root_folder;
	
	config_tpl = fs.readFileSync( path.join(__dirname,'templates/config.tpl'), "utf-8");
	fstab_tpl = fs.readFileSync( path.join(__dirname,'templates/fstab.tpl'), "utf-8");

	console.log('Creating VMs from ' + start +
          ' to ' + ((start + count)));
	var ids = _.range(start, (start + count) + 1);
	for ( var idx in ids ) {
		var i = parseInt(ids[idx]);
		var name = 'vm' + i;
	    vms[name] = create_vm(name);
	}
	console.log( vms );
};


/**********************************************************************
* Allocate an instance and clean it, prior to executing code.
* *script* is a script object, passed from executor.js.
* An object is returned, use its name property for the VM name.
**********************************************************************/
exports.alloc = function(script) {
	// execute lxc-execute on a vm, after we've been allocated on
	var v = allocate_vm( script );

	// Make sure we have a clean environment before we run.
	var cf = get_code_folder(v);
	util.cleanup( cf );
	
	return v;
};

/*  Spawn a process inside the vm; this is the
 *  runscript shell script.
 */
exports.spawn = function(vm, script) {
    var extension = util.extension_for_language(script.language);
    var cfgpath = '/mnt/' + vm.name + '/config';
    var scraper_name = script.scraper_name || "@noscrapername@";

    var args = [ '-n', vm.name, '-f', cfgpath, '--',
      "/home/startup/runscript", extension,
        "--scraper=" + scraper_name];
    var child = spawn(
      '/var/www/scraperwiki/services/scriptmgr/cleanfd.py',
      ['/usr/bin/lxc-execute'].concat(args));
    return child;
}


/**********************************************************************
* Kill the LXC instance that is currently running the provided script
**********************************************************************/
exports.kill = function( vm ) {
    var e;
    util.log.debug('Killing ' + vm.name );
    try {
            e = spawn('/usr/bin/lxc-stop', ['-n', vm.name]);
    } catch(e) {
            util.log.debug(e);
    }
};


exports.code_folder = get_code_folder = function(vm) {
    return path.join(root_folder, vm.name + '/code/');
}

exports.ip_for_vm = function(vm) {
    var num = parseInt( vm.name.substring(2) );
    return '10.0.1.' + (num + 1).toString();
}

/*********************************************************************
* Create a new VM based on newly created config files,
* if not already created.
**********************************************************************/
function create_vm ( name ) {

    var v = {
        'name': name,
        'running': false,
        'script': null,     
    }
    
    // if name exists then just return, otherwise integrate templates and then
    // lxc-create.  Bear in mind that currently (and naffly) the IP address 
    // will be the vm number + 1 (as vm0 has ip 10.0.1.1 )

    // write config and fstab to ...    
    var folder = path.join(root_folder, name);
    
    num = parseInt( name.substring(2) );
    
    // TODO: Fix me
    var ctx = {'name': name, 'ip': '10.0.1.' + (num + 1).toString(), "scrapername": "__public__" }


    var compiled = _.template( config_tpl );
    var cfg = compiled( ctx );
    
    var fs_compiled = _.template( fstab_tpl );
    var fstab = fs_compiled( ctx );
    
    path.exists(root_folder, function (exists) {    
        if ( ! exists ) {
            fs.mkdirSync( root_folder, "0777" );
        }   
    });
    
    
    path.exists(folder, function (exists) {
        if ( ! exists ) {
            fs.mkdirSync( folder, "0777" );
        } else {
            return;
        }

        // Mount the code folder
        var cfolder = get_code_folder(v);
        path.exists(cfolder, function (exists) {
            if (!exists) {
                fs.mkdirSync( cfolder, "0757" );
	    }
        });

        var tgt = path.join(folder, 'config')
        fs.writeFile(tgt, cfg, function(err) {
            if(err) {
                util.log.fatal('Failed to write config file, err: ' + err);
            } else {
                // call lxc-create -n name -f folder/config
                e = spawn('/usr/bin/lxc-create', ['-n', name, '-f', tgt]);
		e.stderr.on('data', function(stuff) {
		    util.log.debug('stderr from lxc-create: ' + stuff);
	        });
                e.on('exit', function (code, signal) {
                    if ( code && code == 127 ) {
                        util.log.fatal('LXC-Create exited with code ' + code);
                    } else {
                        util.log.info('LXC-Create exited with code ' + code);
                    }
                });
            }
        });
                    
        tgt = path.join(folder, 'fstab');
        fs.writeFile(tgt, fstab, function(err) {
            if(err) {
                util.log.fatal('Failed to write fstab file, err: ' + err);
            }
        }); 
    });
    
    return v;
}



/*********************************************************************
* Release the VM using the provided script. 
*********************************************************************/
exports.release_vm = function(script_, vm) {
    var err;
    var name = vm.name;
    util.log.debug('Releasing ' + name);
    var v = vms[name];
    if (!v) {
        return;
    }

    // Remove it from the two lookup tables
    delete vms_by_runid[ v.script.run_id ]
    delete vms_by_ip[ v.script.ip ]
    
    v.running = false;
    v.script = null;
    vms[v.name] = v;
    
    // Make sure we have a clean environment after a release.
    try {
        var cf = get_code_folder(vm);
        util.cleanup(cf);
    } catch(err) {}
}

/*********************************************************************
* Allocate a vm to the calling script.  We will check to find one
* that isn't running and either allocate it or return null if
* none are found.
*
* TODO: Fix this and use detect
* for example
* var even = _.detect([1, 2, 3, 4, 5, 6], function(num){ return num % 2 == 0; });
* => 2
**********************************************************************/
function allocate_vm(script) {
    var v;

    for (var k in vms) {
        v = vms[k];
        if (! v.running) {
                break;
        }
    }

    // Pretty sure that this test, for when we have no VMs
    // free, is wrong.
    if ( ! v ) return null;

    v.running = true;
    v.script = script;
    // Pretty sure that this assignment is redundant.
    vms[v.name] = v;

    util.log.debug('Allocating ' + v.name );	
    return v;
}
