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
var _   = require('underscore')._;
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

var path  = require('path');
var lxc = require( path.join(__dirname,'lxc') );
var util = require( path.join(__dirname,'utils') );
var crypto = require('crypto');

var use_lxc = true;

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
var secret = '';
var fstab_tpl;

/******************************************************************************
* Called to configure the executor, allowing it to determine whether
* we are using LXC, or whether it is on a local dev machine.
******************************************************************************/
exports.init = function( settings ) {
    use_lxc = ! settings.devmode;

    if(!use_lxc) {
        // Replace with the fakelxc.
        lxc = require(path.join(__dirname,'fakelxc'));
    }

    // Consider just passing the *settings* object and nothing else.
    lxc.init(settings.vm_start || 1,
      settings.vm_count,
      settings.mount_folder,
      settings);

    secret = settings.secret || '';
    
    dataproxy = settings.dataproxy;
    max_runs = settings.vm_count;
    
    fstab_tpl = fs.readFileSync( path.join(__dirname,'templates/fstab.tpl'), "utf-8");                
}


/**********************************************************************
* Attempts to kill the script by run_id.
**********************************************************************/
exports.kill_script = function(run_id) {
    var s = scripts[run_id];    
    var vm = s.lxcVM;
    util.log.debug('Requested to kill ' + run_id +
      ' on ' + s.vm)
    lxc.kill(vm);
    return false;
}

exports.known_ips = function() {
    return scripts_ip;
}

/**********************************************************************
* Iterates through the list of scripts that we know is running and
* outputs them in the old format of runID=&scrapername=
**********************************************************************/
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

/**********************************************************************
* Get script details by IP or by runid.
**********************************************************************/
exports.get_details = function(details) {
    if ( details.ip ) {
        util.log.debug('Looking for ip ' + details.ip +
          ' in ' + Object.keys(scripts_ip));
        return scripts_ip[details.ip];
    } else if (details.runid) {
        util.log.debug('Looking for runid ' + details.runid +
          ' in ' + Object.keys(scripts));        
        return scripts[details.runid];
    }
    
    util.log.debug('Failed to find a script for details: ' +
      details );
    return null;
}


/******************************************************************************
* Works out from the incoming request what it is that needs executing,
* if we can find it from the post data.
******************************************************************************/
exports.run_script = function(http_request, http_response) {
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
        util.log.debug('End of HTTP request for /Execute');     
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
    
    var script = { run_id: request_data.runid, 
                scraper_name: request_data.scrapername || "",
                scraper_guid: request_data.scraperid,
                username: request_data.username || "",
                query: request_data.urlquery, 
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
    
    var vm = lxc.alloc(script);
    if (vm == null) {
        util.log.warning('scraper ' + script.scraper_name +
          ' failed to allocate VM');
        var r = {"error": "No virtual machines available"};
        http_res.end( JSON.stringify(r) );
        return;             
    }
    util.log.debug('scraper ' + script.scraper_name +
      ' running on ' + vm.name);      

    var extension = util.extension_for_language(script.language);
    
    var tmpfile = path.join(lxc.code_folder(vm),
      "script." + extension);
    fs.writeFile(tmpfile, request_data.code, function(err) {
        if(err) {
            util.log.debug("scraper " + script.scraper_name +
              " failed to write code");
            var r = {"error": "Failed to write file to local disk",
              "headers": http_req.headers, "lengths":  -1 };
            http_res.end( JSON.stringify(r) );
            return;             
        } 
        util.log.debug('scraper ' + script.scraper_name +
          ' file written to ' + tmpfile );

        // Details such as data proxy and runid are passed
        // to the script by writing to a launch.json file in
        // its filesystem.
        writeLaunchFile( path.join(lxc.code_folder(vm), "launch.json"), 
          dataproxy, 
          script.run_id, 
          script.scraper_name, 
          script.query,
          script.attachables);


        // Set up a close handler to kill the child; we spawn
        // the child just after this.
        
        var kill_on_close = function() {
            // Connection from original requester has closed;
            // For example, a KILL from the Status panel.
            util.log.debug(
              "Issuing KILL for " + script.scraper_name +
              ' running on ' + vm.name + 
              ' with id ' + script.run_id);
            lxc.kill(vm);
        };
        http_req.connection.addListener('close', kill_on_close);

        var child = lxc.spawn(vm, script);

        util.log.debug(script.scraper_name +
          ' run id ' + script.run_id +
          " spawned using " + vm.name);

        // Enable this message?; see
        // https://bitbucket.org/ScraperWiki/scraperwiki/issue/715/
        // json_msg = json.dumps({'message_type': 'executionstatus', 'content': 'startingrun', 'runID': runID, 'uml': scraperstatus["uname"]})
        
        // script.vm is the name of the VM.  Will be either
        // 'vmNN' (for LXC), or 'pidNNN' (for fakelxc).  The
        // kill_script function requires the actual vm object,
        // which is stored in script.lxcVM.
        script.vm = vm.name;
        script.lxcVM = vm;
        script.ip = lxc.ip_for_vm(vm);
            
        scripts[ script.run_id ] = script;
        scripts_ip[ script.ip ] = script;

        var resp = http_res;
        
        child.stdout.on('data', function (data) {
            util.write_to_caller(resp, data.toString());
        });             
        child.stderr.on('data', function (data) {
            util.write_to_caller(resp, data.toString());
        });             
    
        child.addListener('exit', function (code, signal) {
            util.log.debug(script.vm + ' exited with code ' + code);
            http_req.removeListener('close', kill_on_close);
            var conn = http_req.connection;
            if(conn.writable) {
                var address = http_req.connection.address().address;
                var port = http_req.connection.address().port;
                http_req.connection.addListener('close', function () {
                    util.log.debug(
                      '/Execute connection closed after child exit.  ' +
                      'Address ' + address + ' port ' + port);
                });
            }
            onexit(code, signal, script);
        });
    });
}

// Called when a script (child process) exits.
// *code* and *signal* come from the Node 'exit'
// handler, *script* is the script object.
function onexit(code, signal, script)
{
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
    util.log.debug('scraper ' + script.scraper_name +
      ' on ' + script.vm + ' elapsed ' + elapsed);

    // If we have something left in the buffer we really should flush
    // it about now. Suspect this will only be PHP (but
    // actually, all scripts seem to leave a single empty record in
    // the buffer).
    if ( script.response.jsonbuffer &&
      script.response.jsonbuffer.length > 0 )
    {
        util.log.debug('Buffer for ' + script.scraper_name +
          ' still has ' +
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

    if (script && script.response) {
        script.response.end( JSON.stringify( result ) + "\n" );
        util.log.debug('Written end message for ' + script.vm);
    } else { 
        util.log.debug('Script is null?' + script);
        util.log.debug('Script has been disconnected from caller?' +
          script.response );                   
    }

    lxc.release_vm(script, script.lxcVM);

    if (script) {
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



