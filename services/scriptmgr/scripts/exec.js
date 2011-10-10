#!/usr/bin/env node

var fs = require('fs');

var script = '/home/scriptrunner/script.js';
// if not exist then try /tmp/script.js

var launch = JSON.parse( fs.readFileSync('launch.json', 'utf-8') );
var datastore = launch['datastore'];
var runid = launch['runid'];
var scrapername = launch['scrapername'];
var querystring = launch['querystring'];
var attachables = launch['attachables'];
var webstore_port = launch['webstore_port'];

var sw = require('scraperwiki');
var parts = datastore.split(':');
sw.sqlite.init(parts[0], parts[1], scrapername, runid);

process.on('SIGXCPU', function () {
	throw 'ScraperWiki CPU time exceeded';
});

process.on('uncaughtException', function (err) {
	sw.dumpMessage( err );
});

var scriptfile = script;
try {
	// Load and run the script provided to us
	require( scriptfile );
} catch( err ) {
	sw.parseError( err );
	process.exit(1);
}
