/***********************************************************************
* scriptmgr.js
*
* Provides script management services to a dispatching service to allow
* for the execution of code from webapp users within an LXC
* (when not in dev mode).
*
* The behaviour of the service is the same as the original UML
* controller.py and accepts url requests in the same format with
* the same parameters (probably not any more, drj 2012-02).
*
* Acceptable urls are listed below, but see _routemap and the
* relevant functions for the "truth":
*
*  /Execute - Run the provided code within an LXC container and return
*    all of the output on the same connection (as our response).
*  /Kill    - Kill the specified scraper (by stopping its container).
*  /Status  - Return a list of all of the current containers and the 
*    information about what is running
*  /Ident   - Accept an ident request from the httpproxy so that it can 
*    determine the source of the request
*  /Notify  - Called by the httpproxy to let us know what URL the
*    scraper has requested (so we can send it back and add to the
*    sources tab in the editor).
* 
***********************************************************************/
var path  = require('path');
var http = require('http');
var url  = require('url');
var _    = require('underscore')._;
var qs   = require('querystring');
var exec = require( path.join(__dirname,'executor') );
var util = require( path.join(__dirname,'utils'))

_routemap = {
	'/Execute'   : handleExecute,
	'/Kill'  : handleKill,
	'/Status': handleStatus,
	'/ScriptInfo': handleScriptInfo,
	'/Ident' : handleIdent,
	'/Notify': handleNotify,
	'/'      : handleUrlError,
};

/******************************************************************************
* Initialises the http server used for accepting (and then processing)
* requests from a remote dispatcher service.  In general once a request
* has been accepted it is long running until the connection is closed,
* or local script execution is stopped.
******************************************************************************/
var opts = require('opts');
var options = [
  { short       : 'c', 
    long        : 'config',
    description : 'Specify the configuration file to use',
    value       : true 
  }
];
opts.parse(options, true);

var config_path = opts.get('config') || './appsettings.scriptmgr.js';
var settings = require(config_path).settings;
util.setup_logging(settings.logfile, settings.loglevel);
if (settings.devmode) {
    util.log.emitter.addListener('loggedMessage',
      function(message, levelName) {
        console.log(levelName.toUpperCase() + ": " + message);
    });
};
// Handle uncaught exceptions and make sure they get logged
process.on('uncaughtException', function (err) {
  util.log.fatal('Caught exception: ' + err);
  if ( settings.devmode ) console.log( err.stack );
});

// Pass settings and initialise exec module.
exec.init( settings );

http.createServer(function (req, res) {
    // Decide whether we will accept the connection (from twister machine and 
    // local dataproxy/httpproxy only)
    // allowed_ips: ["127.0.0.1"],	
    if ( settings.allowed_ips ) {
        var allowed = false;

        for (x in settings.allowed_ips) {
            var ip = settings.allowed_ips[x];
            allowed = req.connection.remoteAddress == ip;
            if ( allowed )
                    break;
        }

        if ( ! allowed ) {
            write_error(res, "Not allowed to connect from " +
              req.connection.remoteAddress );
            return;
        }
    }

    var handler = _routemap[url.parse(req.url).pathname] || _routemap['/'];
    handler(req,res);
}).listen(settings.port, settings.listen_on || "0.0.0.0");

// Log information to the logfile.
util.log.info('Server started listening on port ' + settings.port );

/******************************************************************************
* Handles a run request when a client POSTs code to be executed.
* See exec.js for details.
******************************************************************************/
function handleExecute(req,res) {
    var address = req.connection.address().address;
    var port = req.connection.address().port;

    util.log.debug('/Execute request.  Address ' +
      req.connection.address().address + ' port ' +
      req.connection.address().port + ' remote ' +
      req.connection.remoteAddress)
    req.connection.addListener('close', function () {
        util.log.debug(
          '/Execute connection closed before child exit.  ' +
          'Address ' + address + ' port ' + port);
    });

    // A 1-day timeout for running scripts.  If we don't set
    // this, we get a 2 minute timeout provided by Node's
    // http library; which is too short.  See ticket #864.
    req.connection.setTimeout(24*3600*1000);
    exec.run_script(req, res);
}

/******************************************************************************
* When provided with a Run ID (run_id) then it will attempt to kill the script
* by sending the request on to the executor which will either lxc-kill or 
* sigkill the relevant script.
******************************************************************************/
function handleKill(req,res) {
	util.log.debug( 'Handling kill request' );

	var url_parts = url.parse(req.url, true);
	var query = url_parts.query;
	
	if ( ! query.run_id ) {
		write_error( res, "Missing parameter" );
		return;
	}

	util.log.debug( 'Killing ' + query.run_id );

	var result = exec.kill_script( query.run_id );
	if ( ! result ) {
		write_error( res, "Failed to kill script, may no longer be running" );
		return;
	}
	res.end();	
}

/******************************************************************************
* Returns the status of the service, which is essentially just a list
* of run ids and names.  This is the same regardless of execution
* method.
******************************************************************************/
function handleStatus(req,res) {
	
	exec.get_status(res);
	res.end('');	
}

/******************************************************************************
* Returns information on all of the scrapers currently running
******************************************************************************/
function handleScriptInfo(req,res) {
	exec.script_info(res);
	res.end('');	
}

/******************************************************************************
* Handle ident callback from http proxy
*
******************************************************************************/
function handleIdent(req,res) {
	
 	var urlObj = url.parse(req.url, true);	
	util.log.debug('Ident request ' + req.url);
	
	// Why oh why oh why do we use ?sdfsdf instead of a proper 
	// query string. Sigh.
	var s;
	for (var v in urlObj.query) {
            s = v.substring(0, v.indexOf(':'));
        }
	
	var script = exec.get_details( { ip: s } );
	if (script) {
		util.log.debug('Found script '+ script.scraper_name +
                  ' runid ' + script.run_id);
		
		res.write( 'scraperid=' + script.scraper_guid + "\n");
		res.write( 'runid=' + script.run_id  + "\n");		
		res.write( 'scrapername=' + script.scraper_name + "\n");
		
		// If we have a username, we know that a user is running it in 
		// the editor, so when it isn't *SCHEDULED* (nice magic string)	
		// we should force it to cache
		if ( script.username != '*SCHEDULED*' ) {
			res.write( 'option=webcache:10\n');				
		}
		res.end('\n')
	}
	else {
		util.log.debug("Unable to find script for IP " + s +
                  " we have " + exec.known_ips());
		write_error( res, "Unable to find script for IP " + s
                  + " we have " + exec.known_ips());
	}
}

/******************************************************************************
* Handle notify callback from http proxy by telling the caller what we have 
* just fetched.
******************************************************************************/
function handleNotify(req,res) {
	
	var urlObj = url.parse(req.url, true);	
	util.log.debug( 'Notify request ' + req.url);
	
	var arg;
	if ( urlObj.query.remote_ip && urlObj.query.remote_ip.length > 0 ) {
		arg = { ip: urlObj.query.remote_ip }
	} else {
		arg = { runid: urlObj.query.runid }		
	}
	
	// todo: check the scraper name against the one provided????
	var script = exec.get_details( arg );		
	if ( script ) {
		delete urlObj.query.runid;
		s = JSON.stringify( urlObj.query );
		util.log.debug( 'Notify request sending ' + s);
		script.response.write( s + "\n");
	}
	
	res.end('');	
}
	

/******************************************************************************
* Unknown URL called.  Will return 404 to denote that it wasn't found rather 
* than it not being valid somehow.
******************************************************************************/
function handleUrlError(req,res) { 
	util.log.debug('404 ' + req.url );
	
	res.writeHead(404, {'Content-Type': 'text/html'}); 
	res.end('URL not found'); 
}	

/******************************************************************************
* Write the error message in our standard (ish) json format
******************************************************************************/
function write_error(res, msg, headers) {
	util.log.warn( msg );
		
	var r = {"error": msg, "headers": headers || '' , "lengths":  -1 };
	res.end( JSON.stringify(r) );
}
