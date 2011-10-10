package Scraperwiki;

use strict;
use warnings;

use Data::Dumper;
use JSON;
use IO::Handle;
use LWP::UserAgent;
use HTTP::Request::Common;

use Scraperwiki::Datastore;

our $logfd = *STDOUT;

sub dumpMessage
{
	my $msg = encode_json (shift);
	print $logfd 'JSONRECORD('.length ($msg)."):$msg\n";
        $logfd->flush;
}

sub scrape
{
	my $url = shift;
	my %params = @_;

	my $response = new LWP::UserAgent->request (
		%params ? POST ($url => %params) : GET ($url));

	return $response->decoded_content if $response->is_success;
	die $response->status_line;
}

sub save_sqlite
{
	my %args = @_;

	$args{table_name} ||= 'swdata';

	return dumpMessage ({message_type => 'data',
		content => 'EMPTY SAVE IGNORED'})
		unless $args{data};

	return dumpMessage ({message_type => 'data',
		content => 'Your data sucks like a collapsed star'})
		unless ref $args{data};

	$args{data} = [ $args{data} ]
		unless ref $args{data} eq 'ARRAY';

	my $datastore = $::store || new Scraperwiki::Datastore;

	$datastore->request (maincommand => 'save_sqlite',
		unique_keys => $args{unique_keys},
		data => $args{data},
		swdatatblname => $args{table_name});

	dumpMessage ({message_type => 'data', content => $args{data}});
}

1;
