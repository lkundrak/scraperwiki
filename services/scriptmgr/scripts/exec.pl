#!/usr/bin/perl

use strict;
use warnings;

package ConsoleStream;

sub TIEHANDLE { return bless {}, shift; }
sub PRINT { Scraperwiki::dumpMessage (message_type => 'console', content => $_[1]); }
sub CLOSE {}
sub flush {}

package main;

use Scraperwiki;
use Getopt::Long;
use File::Basename;
use File::Spec::Functions;
use File::Slurp;
use BSD::Resource;
use JSON;

$Scraperwiki::logfd = undef;
open ($Scraperwiki::logfd, '>>&=', \*STDOUT);
tie (*STDERR, 'ConsoleStream');
tie (*STDOUT, 'ConsoleStream');

my $name;
GetOptions ('script=s', \$name) or die 'Bad options';
die 'No script' unless $name;

my $d = decode_json (read_file (catfile (dirname ($name) => 'launch.json')));
my $datastore = $d->{datastore};
my $runid = $d->{runid};
my $scrapername = $d->{scrapername};
my $querystring = $d->{querystring};
my @attachables = @{$d->{attachables} || []};
my $verification_key = $d->{verification_key} || '';

$ENV{QUERY_STRING} = $ENV{URLQUERY} = $querystring
	if $querystring;

my ($host, $port) = split /:/, $datastore;

$::store = new Scraperwiki::Datastore ($host, $port, $scrapername, $runid, \@attachables, $verification_key);

$SIG{XCPU} = sub { die 'ScraperWiki CPU time exceeded' };
setrlimit ('RLIMIT_CPU', 80, 82);
eval read_file ($name);
die if $@;
