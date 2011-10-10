/******************************************************************************
* scriptmgr.js
*
* Provides script management services to a dispatching service to allow for the 
* execution of code from webapp users within an LXC (when not in dev mode). The
* behaviour of the service is the same as the original UML controller.py and 
* accepts url requests in the same format with the same parameters.
*
* Acceptable urls are listed below, but see the relevant functions for the
* expected parameters:
*
*	/run    - Run the provided code within an LXC container and return all of 
*			  the output on the same connection (as our response).
*	/kill   - Kill the specified scraper (by stopping its container)
*	/status - Return a list of all of the current containers and the 
*			  information about what is running
* 	/ident  - Accept an ident request from the httpproxy so that it can 
*			  determine the source of the request
* 	/notify - Called by the httpproxy to let us know what URL the scraper
*			  has requested (so we can send it back and add to the sources
*			  tab in the editor)
* 
******************************************************************************/
var path  = require('path');
var http = require('http');
var url  = require('url');
var _    = require('underscore')._;
var qs   = require('querystring');
var exec = require( path.join(__dirname,'executor') );
var util = require( path.join(__dirname,'utils'))

_routemap = {
	'/Execute'   : handleRun,
	'/Kill'  : handleKill,
	'/Status': handleStatus,
	'/ScriptInfo': handleScriptInfo,	
	'/Ident' : handleIdent,
	'/Notify': handleNotify,
	'/'      : handleUrlError,
};

/******************************************************************************
* Initialises the http server used for accepting (and then processing) requests
* from a remote dispatcher service.  In general once a request has been 
* accepted it is long running until the connection is closed, or local script
* execution is stopped.
******************************************************************************/
var opts = require('opts');
var options = [
  { short       : 'c', 
	long        : 'config',
    description : 'Specify the configuration file to use',
	value : true 
  }
];
opts.parse(options, true);

var config_path = opts.get('config') || './appsettings.scriptmgr.js';
var settings = require(config_path).settings;

// Load settings and store them locally
exec.init( settings );

util.setup_logging( settings.logfile, settings.loglevel );
if (settings.devmode) {
	util.log.emitter.addListener('loggedMessage', function(message,levelName) {
    	console.log(levelName.toUpperCase() + ": " + message);
  	});
};

// Handle uncaught exceptions and make sure they get logged
process.on('uncaughtException', function (err) {
  util.log.fatal('Caught exception: ' + err);
  if ( settings.devmode ) console.log( err.stack );
});


http.createServer(function (req, res) {
	// Decide whether we will accept the connection (from twister machine and 
	// local dataproxy/httpproxy only)
	
	
	var handler = _routemap[url.parse(req.url).pathname] || _routemap['/'];
	handler(req,res);
}).listen(settings.port, settings.listen_on || "0.0.0.0");

// Log information to the logfile.
util.log.info('Server started listening on port ' + settings.port );

/******************************************************************************
* Handles a run request when a client POSTs code to be executed along with a 
* run id, a scraper id and the scraper name
******************************************************************************/
function handleRun(req,res) {
	util.log.debug( 'Starting run request' );
	exec.run_script( req, res);
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
* Returns the status of the service, which is essentially just a list of run
* ids and names.  This is the same regardless of execution method.
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
	util.log.debug('Ident request')
	
	// Why oh why oh why do we use ?sdfsdf instead of a proper 
	// query string. Sigh.
	var s;
	for ( var v in urlObj.query )
		s = v.substring( 0, v.indexOf(':'))
	
	var script = exec.get_details( { ip: s } );
	util.log.debug(script)
	if ( script ){
		util.log.debug(script.run_id);
		util.log.debug(script.scraper_name);		
		
		res.write( 'scraperid=' + script.scraper_guid + "\n");
		res.write( 'runid=' + script.run_id  + "\n");		
		res.write( 'scrapername=' + script.scraper_name + "\n");	
		res.end('\n')
	}
	else {
		util.log.debug("Unable to find script for IP " + s + " we have " + exec.known_ips());
		write_error( res, "Unable to find script for IP " + s + " we have " + exec.known_ips());
	}
}

/******************************************************************************
* Handle notify callback from http proxy by telling the caller what we have 
* just fetched.
******************************************************************************/
function handleNotify(req,res) {
	
	var urlObj = url.parse(req.url, true);	
	util.log.debug( 'Notify request ' + req.url);
	
	script = exec.get_details( {runid: urlObj.query.runid } );		
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
		
	r = {"error": msg, "headers": headers || '' , "lengths":  -1 };
	res.end( JSON.stringify(r) );
}