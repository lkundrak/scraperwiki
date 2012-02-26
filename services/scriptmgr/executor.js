/******************************************************************************
* executor.js
*
* A running script is indexed by its run_id but looks similar to
* the following for both status and kill calls.
* 
*   script = { run_id : request_data.run_id, 
*               scraper_name : request_data.scrapername,
*               scraper_guid : request_data.scraperid,
*               query : request_data.urlquery, 
*               pid: -1, 
*               vm: '', 
*               language: request_data.language || 'python',
*               ip: ''};
* 
******************************************************************************/
var _    = require('underscore')._;
var qs  = require('querystring');
var fs  = require('fs');
// depending on version we should include sys or util, keep
// both having the same name.
var sysname;
if ( process.versions.node.indexOf('0.6') == 0 ) {
    sysname = 'util';
} else {
    sysname = 'sys';
}
var sys = require(sysname);

var spawn = require('child_process').spawn;
var path  = require('path');
var lxc = require( path.join(__dirname,'lxc') );
var util = require( path.join(__dirname,'utils') );
var crypto = require('crypto');

var use_lxc = true;
var extra_path;
var code_folder = '/tmp';

// A table of all of the currently running scripts, indexed by
// their run_id which usually comes from the runid property of
// the original /Execute request.
var scripts = {};
// Number of entries in *scripts* table
function count_scripts() {
    return Object.keys(scripts).length
}
var scripts_ip = [ ];
var max_runs = 100;
var dataproxy = '';
var httpproxy;
var secret = '';
var fstab_tpl;

/******************************************************************************
* Called to configure the executor, allowing it to determine whether
* we are using LXC, or whether it is on a local dev machine.
******************************************************************************/
exports.init = function( settings ) {
    use_lxc = ! settings.devmode;

    if ( use_lxc ) {
        lxc.init(settings.vm_start || 1,
          settings.vm_count, settings.mount_folder);
    }

    if ( settings.devmode ) {
        httpproxy = settings.httpproxy;
    };

    secret = settings.secret || '';
    
    code_folder = settings.code_folder;
    dataproxy = settings.dataproxy;
    extra_path = settings.extra_path;
    max_runs = settings.vm_count;
    
    fstab_tpl = fs.readFileSync( path.join(__dirname,'templates/fstab.tpl'), "utf-8");                
}


/******************************************************************************
* Attempts to kill the script that is running with the specified
* run id whether it is an lxc instance (lxc-kill) or a local process
* (kill by pid).
******************************************************************************/
exports.kill_script = function( run_id ) {
    var s = scripts[run_id];    
    if ( ! use_lxc ) {
        if ( s ) {
            pid = s.pid;
            process.kill(pid, 'SIGKILL');
            s = scripts[run_id];
            delete scripts[run_id];
            delete scripts_ip[s.ip];
            
            util.log.debug('Killed process PID: ' + pid);                   
            return true;
        };
    } else {
        util.log.debug('Attempting to kill LXC ' + s.vm)
        lxc.kill(s);
    }
    
    return false;
}

exports.known_ips = function() {
    return scripts_ip;
}

/******************************************************************************
* Iterates through the list of scripts that we know is running and
* outputs them in the old format of runID=&scrapername=
******************************************************************************/
exports.get_status = function(response) {
    for(var runID in scripts) {
        var script = scripts[runID];
        response.write('runID=' + runID +
          "&scrapername=" + script.scraper_name + "\n");
    }   
}


/******************************************************************************
* Displays what we know about all of the current scripts that are running, 
* if any as a HTML display
******************************************************************************/
exports.script_info = function(response) {
    util.log.debug("+ Returning script info");  
    for(var runID in scripts) {
        var script = scripts[runID];
        var cloned = {
            run_id: script.run_id,
            scraper_name : script.scraper_name,
            scraper_guid : script.scraperid,
            vm: script.vm || "",
            language: script.language,
            ip: script.ip
        }
        response.write( JSON.stringify(cloned) + "\n");
    }   
}

/******************************************************************************
* 
* 
******************************************************************************/
exports.get_details = function(details) {
    if ( details.ip ) {
        util.log.debug('Looking for ip ' + details.ip + ' in ' + scripts_ip);
        return scripts_ip[details.ip];
    } else if ( details.runid ) {
        util.log.debug('Looking for runid ' + details.runid + ' in ' + scripts);        
        return scripts[details.runid];
    }
    
    util.log.debug('Failed to find a script: ' );
    util.log.debug( details );
    return null;
}


/******************************************************************************
* Works out from the incoming request what it is that needs executing,
* if we can find it from the post data.
******************************************************************************/
exports.run_script = function( http_request, http_response ) {
    var r;
    
    http_request.setEncoding('utf8');
    
    if ( count_scripts() >= max_runs ) {
        r = {"error":"Too busy",
          "headers": http_request.headers,
          "lengths":  -1 };
        http_response.end( JSON.stringify(r) );
        return;
    }
    
    var len = http_request.headers['content-length'] || -1;
    var body = '';

    http_request.on('data', function (data) {
        body += data;
    });
    
    http_request.on('end', function () {
        if ( body.length == 0 ||
             body.length != len )
        {
            r = {"error":"incoming message incomplete",
              "headers": http_request.headers,
              "lengths":  len.toString() };
            http_response.end( JSON.stringify(r) );
            return;
        };

        execute(http_request, http_response, body);
        util.log.debug('Done calling execute');     
    });
        
};

function hashkey( name ) {
    return crypto.createHash("sha256").update( name + secret ).digest("hex");
}


function writeLaunchFile( f, ds, runid, scrapername, querystring, attachables ) {
    var launch = {
        'datastore': ds,
        'runid': runid,
        'scrapername': scrapername || '',
        'querystring': querystring || '',
        'attachables': attachables || [],
        'verification_key': hashkey(scrapername || '')
    }
    
    var data = JSON.stringify( launch );
    fs.writeFileSync(f, data, encoding='utf8');
}

/******************************************************************************
* Actually extracts the code and then checks config to determine
* whether we should run this as if on a developer machine or whether
* to run as if on an actual server.
*
* The *raw_request_data* parameter (which usually comes from the
* body of the HTTP request) should contain a JSON object with
* the properties (many optional):

code
runid
scrapername
scraperid
username
urlquery
language
beta_user
attachables
scheduled_run
permissions

* TODO: Refactor executor to be two classes one for local and
* one for lxc.
******************************************************************************/
function execute(http_req, http_res, raw_request_data) {
    var r;

    http_res.writeHead(200, {'Content-Type': 'text/plain'});
    
    try {
        request_data = JSON.parse( raw_request_data );
    } catch ( err )
    {
        util.dumpError( err );
    }
    
    var script = { run_id : request_data.runid, 
                scraper_name : request_data.scrapername || "",
                scraper_guid : request_data.scraperid,
                username: request_data.username || "",
                query : request_data.urlquery, 
                pid: -1, 
                vm: '', 
                language: request_data.language || 'python',
                ip: '',
                response: http_res,
                black: request_data.black || '',   // not used
                white: request_data.white || '',   // not used
                beta_user: request_data.beta_user || false,
                attachables: request_data.attachables || [],
                scheduled_run: request_data.scheduled_run || false,
                permissions: request_data.permissions || [] };
    script.start_time = new Date();
    
    if ( ! use_lxc ) {
        // Execute the code locally using the relevant file (exec.whatever)
        var tmpfile = path.join( code_folder, "script." + util.extension_for_language(script.language) );
        fs.writeFile(tmpfile, request_data.code, function(err) {
            
            writeLaunchFile( path.join( code_folder, "launch.json"), 
                             dataproxy, 
                             script.run_id, 
                             script.scraper_name, 
                             script.query, 
                             script.attachables);
            
            if(err) {
                r = {"error":"Failed to write file to local disk",
                     "headers": http_req.headers , "lengths":  -1 };
                http_res.end( JSON.stringify(r) );
                return;             
            }
            var args;
            if ( script.language == 'ruby' ||
              script.language == 'php' )
            {
                args = ['--script=' + tmpfile,]
            } else {
                args = ['--script', tmpfile]
            }
            
            var exe = './scripts/exec.' + util.extension_for_language(script.language);

            var environ = util.env_for_language(script.language, extra_path);
            
            if (script.query) {
                environ['QUERY_STRING'] = script.query;
            }
            
            if (httpproxy) {
                environ['http_proxy'] = 'http://' + httpproxy;
            }
            
            util.log.debug( 'spawning ' + exe + ' args '  + args);
            var e = spawn(exe, args, { env: environ});
            script.pid = e.pid;
            script.ip = '127.0.0.1';
            
            scripts[ script.run_id ] = script;
            scripts_ip[ script.ip ] = script;

            http_req.connection.addListener('close', function () {
                // Let's handle the user quitting early it might be
                // a KILL command from the dispatcher.
                util.log.debug(
                  "Connection closed for script id " +
                  script.run_id +
                  " pid " + script.pid)
                if ( e ) {
                    e.kill('SIGKILL');
                }
                if ( script ) {
                    delete scripts[script.run_id];                  
                    delete scripts_ip[ script.ip ];                 
                }
            });
        
            util.log.debug( "Script " + script.run_id +
              " executed with pid " + script.pid );

            var resp = http_res;
            e.stdout.on('data', function (data) {
                util.write_to_caller( http_res, data.toString());           
            });             

            e.stderr.on('data', function (data) {
                util.write_to_caller( http_res, data.toString());           
            });             
            
            e.on('exit', function (code, signal) {
                onexit(code, signal, script, function(){
                  // no release to do
                  })
            });
        }); // end of writefile
    } else {
        // use_lxc
        //
        // :todo: We can clearly refactor this into something
        // class-based and easier to understand.
        // There is more in common with the previous branch than
        // different.
        //  
        var res = lxc.exec( script, request_data.code );
        if ( res == null ) {
            var r = {"error": "No virtual machines available"}
            http_res.end( JSON.stringify(r) );
            return;             
        }
        util.log.debug( 'Running on ' + res );      
                
/*                
        // Write out a new FSTAB for this run using the template, so that we can later 
        // add/modify the fstab template.
 	    var ctx = {'name': res, 'scrapername':  script.scraper_name || "__public__" }
	    var fs_compiled = _.template( fstab_tpl );
	    var fstab = fs_compiled( ctx );
        util.log.debug('Writing fstab to ' + '/mnt/' + res + '/fstab')
	    var f = fs.openSync('/mnt/' + res + '/fstab', 'w');
	    fs.writeSync(f, fstab);
	    fs.closeSync( f );
*/

        var extension = util.extension_for_language(script.language);
        
        // /var/www/scraperwiki/resourcedir/<%= scrapername >/
        // instead of 
        // lxc.code_folder(res)
        var tmpfile = path.join(lxc.code_folder(res), "script." + extension );
        var rVM = res;
        fs.writeFile(tmpfile, request_data.code, function(err) {
            if(err) {
                var r = {"error":"Failed to write file to local disk",
                  "headers": http_req.headers, "lengths":  -1 };
                http_res.end( JSON.stringify(r) );
                return;             
            } 

            writeLaunchFile( path.join(lxc.code_folder(res),
              "launch.json"), 
              dataproxy, 
              script.run_id, 
              script.scraper_name, 
              script.query,
              script.attachables);

            util.log.debug('File written to ' + tmpfile );

            // Pass the data proxy and runid to the script that will
            // trigger the exec.py
            var cfgpath = '/mnt/' + rVM + '/config';

            var args = [ '-n', rVM, '-f', cfgpath,
              "/home/startup/runscript", extension];
            var e = spawn(
              '/var/www/scraperwiki/services/scriptmgr/cleanfd.py',
              ['/usr/bin/lxc-execute'].concat(args));

            // json_msg = json.dumps({'message_type': 'executionstatus', 'content': 'startingrun', 'runID': runID, 'uml': scraperstatus["uname"]})
            
            script.vm = rVM;
            script.ip = lxc.ip_for_vm(rVM);
                
            scripts[ script.run_id ] = script;
            scripts_ip[ script.ip ] = script;
    
            http_req.connection.addListener('close', function () {
                // Let's handle the user quitting early it might be a KILL
                // command from the dispatcher
                lxc.kill( rVM );
            });
            
            var resp = http_res;
            
            e.stdout.on('data', function (data) {
                util.write_to_caller( resp, data.toString());
            });             
            
            e.stderr.on('data', function (data) {
                util.write_to_caller( resp, data.toString());
            });             
        
            var local_script = script;  
            e.on('exit', function (code, signal) {
                onexit(code, signal, script, function(){
                  lxc.release_vm( script, rVM );})
            });
        });
    }
}

// Called when a script exits (in either LXC or local process
// case).  *code* and *signal* come from the Node 'exit'
// handler, *script* is the script object, *release* is a function
// to call to release the VM (only used for LXC).
function onexit(code, signal, script, release)
{
    var pid = 'child process pid ' + script.pid;
    if ( code == null ) {
        util.log.debug(pid + ' exited with null code.')
    } else {
        util.log.debug(
          pid + ' exited with code ' + code);
    }

    // If code is 137 then it is probably an out of memory error;
    // LXC has decided to just kill it?
    var exitError;
    if ( code == 137 ) {
        // :todo: Check *signal* to double-check what signal killed us
        var exitError = "[Warning] The script was killed, it may have exceeded the memory limit";
        if ( script.response.jsonbuffer ) {
            script.response.jsonbuffer.push(exitError)
        }
    }

    var endTime = new Date();
    var elapsed = (endTime - script.start_time) / 1000;
    util.log.debug(pid + ' elapsed ' + elapsed );

    // If we have something left in the buffer we really should flush
    // it about now. Suspect this will only be PHP (but
    // actually, all scripts seem to leave a single empty record in
    // the buffer).
    if ( script.response.jsonbuffer &&
      script.response.jsonbuffer.length > 0 )
    {
        util.log.debug('Buffer still has ' +
          script.response.jsonbuffer.length +
          ' entries');
        util.log.debug( script.response.jsonbuffer );
    
        var left = script.response.jsonbuffer.join("");                       
        if ( left && left.length > 0 ) {
            // reset the buffer for the final run
            script.response.jsonbuffer = [];
            var m = left.toString().match(/^JSONRECORD\((\d+)\)/);
            if ( m == null ) {
                util.log.debug(
                  "Looks like the remaining data is not JSON so need to wrap");
                var partial = JSON.stringify(
                  {'message_type': 'console', 'content': left} );
                partial = "JSONRECORD(" +
                  partial.length.toString() + "):" + partial + "\n";                    
                util.write_to_caller(script.response, partial);
            } else {
                util.log.debug(
                  "Looks like the remaining data is JSON so sending as is");                      
                util.write_to_caller(script.response, left.toString());
            }                   
        }                       
    }

    // 'CPU_seconds': 1, Temporarily removed
    var result =  { 'message_type':'executionstatus',
      'content':'runcompleted', 
      'elapsed_seconds': elapsed
    };
    result.exit_status = code;

    if ( script && script.response ) {
        script.response.end( JSON.stringify( result ) + "\n" );
        util.log.debug('Have just written end message to the vm ' + script.vm );
    } else { 
        util.log.debug('Script is null?' + script);
        util.log.debug('Script has been disconnected from caller?' + script.response );                   
    }

    release();

    if ( script) {
        delete scripts[script.run_id];
        delete scripts_ip[ script.ip ];
    }
    util.log.debug('script list now has ' +
      count_scripts() + ' entries')
                    
    if (script) { 
        util.log.debug('Finished writing responses for ' +
          script.vm);
    } else {
        util.log.debug('Finished writing a response');
    }
}



