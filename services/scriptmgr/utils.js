/******************************************************************************
* utils.js
*
* Utility functions for working with the processes locally
******************************************************************************/
var path  = require('path');
var fs = require('fs'),
_ = require('underscore');

/******************************************************************************
* Write the response to the caller, or in this case write it back down the long
* lived socket that connected to us.
******************************************************************************/
exports.write_to_caller = function(http_res, output) {
	if ( ! http_res.jsonbuffer )
		http_res.jsonbuffer = [];
		
	var msg = output.toString();
	var parts = msg.split("\n");		
    http_res.jsonbuffer.push(parts.shift());

	logger.debug("WTC:1:" +  msg );
	logger.debug("WTC:2:Buffer items count:" + http_res.jsonbuffer.length  );
	
	while (parts.length > 0) {
	    var element = http_res.jsonbuffer.join(""); 

		logger.debug("WTC:3:" +  element );
	
		var rp = element.match(/^JSONRECORD\((\d+)\)/);
		if ( rp != null ) {
			logger.debug("WTC:5:" + rp  );			
			// rp is [ matched text, captured data, ... ]
			var size = rp[1];
			logger.debug("WTC:5:SIZE:" + rp[1]  );		
			logger.debug("WTC:5:TAG:" + rp[0]  );	
			logger.debug("C: " + element.slice(rp[0].length + 1).length + " " + size);

			// if the text after JSONRECORD(x): is the length we expect, then write it
			if ( element.slice(rp[0].length + 1).length == size ) {
				// we have valid data to write to the client
				logger.debug('ABOUT TO WRITE:' + element.slice(rp[0].length + 1) + ":");
				http_res.write( element.slice(rp[0].length + 1) + "\n");
				http_res.jsonbuffer = [parts.shift()];			
			} else {
				http_res.jsonbuffer.push( parts.shift() );		
			} 
		} else {
			logger.debug("WTC:4:No match we think this is not JSON");			

			var m = element.toString().match(/^JSONRECORD\(\d+\)/);
			if ( m == null ) {
				var partial = JSON.stringify( {'message_type': 'console', 'content': element.toString()} ) + "\n";
				http_res.write( partial );
				http_res.jsonbuffer = [parts.shift()]; // reset the buffer
			} else {
				http_res.jsonbuffer.push( parts.shift() );		
			}
		}

		logger.debug("WTC:4:Buffer is now " + http_res.jsonbuffer);					
	}

	
}

/*	var msg = output.toString();
	var parts = msg.split("\n");	

	if ( ! http_res.jsonbuffer ) {
		http_res.jsonbuffer = [];
	}
	
    http_res.jsonbuffer.push(parts.shift());

	while (parts.length > 0) {
	   var element = http_res.jsonbuffer.join(""); 
		
		var rp = element.match(/^JSONRECORD\((s)\)/);
		if ( rp != null ) {
			// rp is [ matched text, captured data, ... ]
			var size = rp[1];
			// if the text after JSONRECORD(x): is the length we expect, then write it
			if ( element.slice(0, rp[0].length + 1).length ) {
				// we have valid data to write to the client
			}
		}
		
	   http_res.jsonbuffer = [ parts.shift() ];
	}



	for (var i=0; i < parts.length; i++) {
		if ( parts[i].length > 0 ) {
			if ( parts[i].indexOf("JSONRECORD(") == 0) { // If we start with JSON RECORD
				// Check the size (+tag) and if all there then write it, otherwise store in 
				// buffer.
				
			} else {
				// If we have a buffer then prepend the buffer 
				
				
				// or if we have no buffer and no tag, then wrap it in a 'console message'
			}
			
		}
		*/
/*		if ( parts[i].length > 0 ) {
			try {
				s = JSON.parse(parts[i]);
				if ( s && typeof(s) == 'object' ) {
					logger.debug('We have been given JSON and so will feed it back' + parts[i] );
					http_res.write( parts[i] + "\n");
				} else {
					logger.debug('Not an object' + parts[i] );
				}
			}catch(err) {
				logger.debug('Not JSON, so encoding in wrapper and returning - ' + parts[i])
				http_res.write( JSON.stringify( {'message_type': 'console', 'content': parts[i] }) + "\n");											
			}
		}
	};
}*/


var streamLogger = require('streamlogger');
var logger;

/******************************************************************************
* Set up logging to the specific file with the level where level = 
* debug: 0, info: 1, warn: 2, fatal: 3  
******************************************************************************/
exports.setup_logging = function( logfile, level ) {
	logger = new streamLogger.StreamLogger( logfile );	
	logger.level = level;
	
	process.on('SIGHUP', function () {
  		logger.reopen();
	});
	
	exports.log = logger;
};



var exts = {
	'python' : 'py', 
	'ruby'   : 'rb', 	
	'php'   : 'php', 		
	'javascript' : 'js',
}

/******************************************************************************
* Silly look up to get the extension for the language we are executing
******************************************************************************/
exports.extension_for_language = function( lang ) {
	return exts[lang];
};

/******************************************************************************
* Works out what environment variables we want to pass to the script
******************************************************************************/
exports.env_for_language = function( lang, extra_path ) {
	var ep = path.join(__dirname, extra_path);
	ep = path.join(ep, lang);
	if ( lang == 'python' ) {
		return {PYTHONPATH: ep, PYTHONUNBUFFERED: 'true'};
	} else if ( lang == 'ruby') {
		ep = path.join(ep, "scraperwiki/lib");
		return { RUBYLIB: ep + ":" + process.env.RUBYLIB };		
	} else if ( lang == 'php') {
		return { PHPPATH: ep};		
	} else if ( lang == 'javascript' ) {
		return { NODE_PATH: process.env.NODE_PATH + ":" + ep + ":/usr/local/lib/node_modules" };
	}	
};

				
exports.dumpError = function(err) {
  if (typeof err === 'object') {
    if (err.message) {
      util.log.warn('Message: ' + err.message)
    }
    if (err.stack) {
      util.log.warn(err.stack);
    }
  } else {
    console.log('dumpError :: argument is not an object');
  }
}



/******************************************************************************
* Empty all files (and created folders) within a specific directory
******************************************************************************/
exports.cleanup = function(filep) {
	removeDirForce(filep);
	logger.debug('Cleanup up folder ' + filep);
}

function removeDirForce(filep) {
	var files = fs.readdirSync(filep);
    _.each(files, function(file) {
    	var filePath = path.join(filep,file);
		var stats = fs.statSync(filePath);
		if (stats.isDirectory()) {
			removeDirForce(filePath);
		} 
		if (stats.isFile()) {
			fs.unlinkSync(filePath);
		}
	});
}
