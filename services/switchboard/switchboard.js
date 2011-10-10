/******************************************************************************
* switchboard.js
*
* A simple switchboard that accepts input from N writers and streams it all to
* M registered readers, all based on a key - the run_id. When a client wants 
* to run a script it can be told where to call (as a writer) and have the data
* written to any client who has registered as a reader with the run_id. If 
* there are no registered readers then data is likely to be dropped onto the 
* floor, after the initial buffer has been accepted and filled.
* 
******************************************************************************/
var path = require('path');
var http = require('http');
var url  = require('url');
var _    = require('underscore')._;
var opts = require('opts');
var sio  = require('socket.io');

var registry = require(path.join(__dirname,'registry'));
var logging = require( path.join(__dirname,'logging'))


// Handle uncaught exceptions and make sure they get logged
process.on('uncaughtException', function (err) {
  util.log.fatal('Caught exception: ' + err);
  if ( settings.devmode ) console.log( err.stack );
});


var options = [
  { short       : 'c', 
	long        : 'config',
    description : 'Specify the configuration file to use',
	value : true 
  }
];
opts.parse(options, true);

var config_path = opts.get('config') || './appsettings.switchboard.js';
var settings = require(config_path).settings;

logging.setup( settings.logfile, settings.loglevel );
registry.set_max( settings.max_readers, settings.max_writers );

var io = sio.listen( settings.read_port )

/**********************************************************************
* Socket.io connections are readers only
* The client JS will be delivered
*       via http://server:settings.read_port/socket.io/socket.io.js
**********************************************************************/
io.sockets.on('connection', function (socket) {
	socket.on('register', function (data) {
	    // read the run_id and connect to the main registry
	    // we'll then use socket.emit to write the response
	    // socket.emit('news', { hello: 'world' });
		var key = data['runid'];
		if ( ! registry.bind( key, socket, register.ConnectionTypeEnum.READER ) ) {

		} else {
	
		}
	});
});


