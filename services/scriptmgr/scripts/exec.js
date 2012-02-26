#!/usr/local/bin/node

var fs = require('fs');
var path = require('path');

var script = '/home/scriptrunner/script.js';
if ( ! path.existsSync(script) )
	script = '/tmp/script.js'

var launch_path = '/home/scriptrunner/launch.json';
if ( ! path.existsSync(launch_path) )
	launch_path = '/tmp/launch.json';

var launch = JSON.parse( fs.readFileSync(launch_path, 'utf-8') );
var datastore = launch['datastore'];
var runid = launch['runid'];
var scrapername = launch['scrapername'];
var querystring = launch['querystring'];
var attachables = launch['attachables'];
var verification_key = launch['verification_key']

var sw = require('scraperwiki');
var parts = datastore.split(':');
sw.sqlite.init(parts[0], parts[1], scrapername, runid,verification_key);

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
