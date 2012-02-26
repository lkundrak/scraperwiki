// ScraperWiki language support for JavaScript scrapers.
// David Jones, ScraperWiki Limited

// http://jsdom.org/
var jsdom = require('jsdom');
var request = require('request');
var dp = require('./dataproxy');
var fs = require('fs');
var path  = require('path');

exports.version = '1.0.0';
exports.sqlite = new DataProxyClient();

exports.dumpMessage = dumpMessage = function(msg) {
	console.log( "JSONRECORD(" + msg.length.toString() + "):" + msg.toString() + "\n" );
}

exports.parseError = parseError = function(err) {
	// parse err.stack for nice clean presentation. We still need line 
	// numbers adding here.
	var stack = [];
	var lines = err.stack.split('\n');

	// Get line number from lines[1] which looks a bit like
	// at Object.<anonymous> (/private/tmp/script.js:3:9)
	var linenum = lines[1].match(/\d+/)[0];

	stack.push( {"duplicates": 0, "linetext": lines[0].trim(), "file": "<string>", "linenumber": parseInt(linenum)} )
	
	for ( var p = 1; p < lines.length; p++ ) {
		var m = lines[p].trim();
		if ( m.length > 0 )
			stack.push( { "file": m, "linetext" : m, "linenumber": parseInt(linenum)}  );
	}
	
	var result = { "message_type": "exception",  
				   "linenumber": parseInt(linenum),
				   "stackdump": stack };	
	dumpMessage( JSON.stringify(result) );    
}


exports.scrape = function( url, func ) {
    var jp = path.join(__dirname, "jquery.1.7.0.min.js");

    request({ uri: url }, function (error, response, body) {
        if (error && response.statusCode !== 200) {
            console.log('Error when contacting site')
        } else {
            jsdom.env({
                  html: body,
                  scripts: [ jp ],
                }, 
                function (err, window) {
                   var $ = window.$;
                   func($, body, err);
                }
            );
        }
    });
}
