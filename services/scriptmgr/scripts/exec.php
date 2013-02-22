#!/usr/bin/env php
<?php

// set the include paths to scraperlibs from an environment variable
// (this can be done automatically for python and ruby)
foreach (split(':', getenv('PHPPATH')) as $dir)
    ini_set('include_path',  ini_get('include_path') . PATH_SEPARATOR . $dir) ;

$logfd = STDOUT; 

require_once 'scraperwiki.php';
require_once 'scraperwiki/datastore.php';
require_once 'scraperwiki/stacktrace.php';

ob_implicit_flush(true);

$script 	 = null;

// Load launch.json

for ($idx = 1; $idx < count($argv); $idx += 1)
{
   $arg  = $argv[$idx] ;

   if (substr ($arg, 0,  9) == '--script=')
      $script = substr ($arg, 9);
}

$contents    = file_get_contents( dirname($script) . '/launch.json');
$launch      = json_decode( $contents, true );
$datastore   = $launch['datastore'];
$scrapername = $launch['scrapername'];
$runid 	     = $launch['runid'];
$querystring = $launch['querystring'];
$attachables = $launch['attachables'];
$verification_key = $launch['verification_key'];

if ( strlen($querystring) > 0 ) {
	putenv("QUERY_STRING=" . $querystring);
	putenv("URLQUERY=" . $querystring);
}

if ( strlen($verification_key) > 0 ) {
	putenv('VERIFICATION_KEY='. $verification_key);
}


function shutdown(){
    $isError = false;

    if ($error = error_get_last()){
        switch($error['type']){
			case E_ERROR:
            case E_CORE_ERROR:
            case E_COMPILE_ERROR:
            case E_USER_ERROR:	
            case E_PARSE:
                $isError = true;
                break;
    }
                                             }
    if ($isError){
		$etb = errorParserNoStack($error['type'], $error['message'], $error['file'], $error['line']); 
    	scraperwiki::sw_dumpMessage($etb); 	
    }
}
register_shutdown_function('shutdown');



// make the $_GET array
$QUERY_STRING = getenv("QUERY_STRING");
$QUERY_STRING_a = explode('&', $QUERY_STRING);
$_GET = array(); 
for ($i = 0; $i < count($QUERY_STRING_a); $i++)
{
    $QUERY_STRING_b = split('=', $QUERY_STRING_a[$i]);
	if ( count( $QUERY_STRING_b ) > 1 ) {
    	$_GET[urldecode($QUERY_STRING_b[0])] = urldecode($QUERY_STRING_b[1]); 
	}
}


$dsinfo = split (':', $datastore) ;
SW_DataStoreClass::create ($dsinfo[0], $dsinfo[1], $scrapername, $runid, $attachables,$verification_key);

// the following might be the only way to intercept syntax errors
//$errors = array(); 
//parsekit_compile_file($script, $errors); 

// intercept errors for stack dump
// refer to http://php.net/manual/en/function.set-error-handler.php
function errorHandler($errno, $errstr, $errfile, $errline)
{
    // if error has been surpressed with an @
    // see: http://php.net/manual/en/function.set-error-handler.php
    if (error_reporting() == 0) {
        return;
    }

    global $script; 
    $etb = errorParserStack($errno, $errstr, $script); 
    scraperwiki::sw_dumpMessage($etb); 
    return true; 
}

set_error_handler("errorHandler", E_ALL & ~E_NOTICE);  // this is for errors, not exceptions (eg 1/0)
error_reporting(E_NOTICE); // don't display default error messages for ones we are sending via errorHandler, avoiding duplicates

set_time_limit(160); 

date_default_timezone_set('Europe/London');

try
{
    // works also as include or eval.  However no way to trap syntax errors
    require $script;
}
catch(Exception $e)
{
    $etb = exceptionHandler($e, $script);
    scraperwiki::sw_dumpMessage($etb); 
}
?>
