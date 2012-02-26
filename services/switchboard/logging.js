var streamLogger = require('streamlogger');
var logger;

/******************************************************************************
* Set up logging to the specific file with the level where level = 
* debug: 0, info: 1, warn: 2, fatal: 3  
******************************************************************************/
exports.setup = function( logfile, level ) {
	logger = new streamLogger.StreamLogger( logfile );	
	logger.level = level;
	
	process.on('SIGHUP', function () {
  		logger.reopen();
	});
	
	exports.log = logger;
};
