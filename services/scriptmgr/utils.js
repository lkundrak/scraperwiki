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
    
    while (parts.length > 0) {
        var element = http_res.jsonbuffer.join(""); 

        var rp = element.match(/^JSONRECORD\((\d+)\)/);
        if ( rp != null ) {
            // rp is [ matched text, captured data, ... ]
            var size = rp[1];

            // if the text after JSONRECORD(x): is the length we expect, then write it
            if ( element.slice(rp[0].length + 1).length == size ) {
                // we have valid data to write to the client
                http_res.write( element.slice(rp[0].length + 1) + "\n");
                http_res.jsonbuffer = [parts.shift()];          
            } else {
                http_res.jsonbuffer.push( parts.shift() );      
            } 
        } else {
            var m = element.toString().match(/^JSONRECORD\(\d+\)/);
            if ( m == null ) {
                var partial = JSON.stringify( {'message_type': 'console', 'content': element.toString()} ) + "\n";
                http_res.write( partial );
                http_res.jsonbuffer = [parts.shift()]; // reset the buffer
            } else {
                http_res.jsonbuffer.push( parts.shift() );      
            }
        }
    }
}


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
* Silly look up to get the extension for the language we are executing, not sure 
* why we don't just export the exts dict (er I mean object)
******************************************************************************/
exports.extension_for_language = function( lang ) {
    if ( !lang ) 
        return 'py';
    
    return exts[lang.toLowerCase()];
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
      logger.warn('Message: ' + err.message)
    }
    if (err.stack) {
      logger.warn(err.stack);
    }
  } else {
    console.log('dumpError :: argument is not an object');
  }
}



/******************************************************************************
* Empty all files (and created folders) within a specific directory
******************************************************************************/
exports.cleanup = function(filep) {

    //removeDirForce(filep);
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
