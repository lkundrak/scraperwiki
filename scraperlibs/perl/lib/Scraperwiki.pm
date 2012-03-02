package Scraperwiki;

use strict;
use warnings;

use Data::Dumper;
use JSON;
use IO::Handle;
use LWP::UserAgent;
use HTTP::Request::Common;
use URI::Escape;
use JSON;

use Scraperwiki::Datastore;

our $logfd = *STDOUT;

sub dumpMessage
{
	my $msg = encode_json ({@_});
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

	return dumpMessage (message_type => 'data',
		content => 'EMPTY SAVE IGNORED')
		unless $args{data};

	return dumpMessage (message_type => 'data',
		content => 'Your data sucks like a collapsed star')
		unless ref $args{data};

	$args{data} = [ $args{data} ]
		unless ref $args{data} eq 'ARRAY';

	my $datastore = $::store || new Scraperwiki::Datastore;

	$datastore->request (maincommand => 'save_sqlite',
		unique_keys => $args{unique_keys},
		data => $args{data},
		swdatatblname => $args{table_name});

	dumpMessage (message_type => 'data', content => $args{data})
		if $args{verbose} and $args{verbose} >= 2;
}

our @attachlist;
sub attach
{
	my %args = @_;

	push @attachlist, { name => $args{name}, asname => $args{asname} };
	my $datastore = $::store || new Scraperwiki::Datastore;
	my $res = $datastore->request (maincommand => 'sqlitecommand',
		command => 'attach',
		name => $args{name},
		asname => $args{asname});

	# TODO: Bless the error message with error class?
	die $res->{error} if exists $res->{error};

	dumpMessage (message_type => 'sqlitecall', command => 'attach',
		val1 => $args{name}, val2 => $args{asname})
		if $args{verbose} and $args{verbose} >= 2;

	return $res;
}

sub select
{
	my %args = @_;

	return sqliteexecute (sqlquery => 'select '.$args{sqlquery},
		data => $args{data},
		verbose => $args{verbose});
}

sub sqliteexecute
{
	my %args = @_;

	my $datastore = $::store || new Scraperwiki::Datastore;
	my $res = $datastore->request (maincommand => 'sqliteexecute',
		sqlquery => $args{sqlquery},
		data => $args{data},
		attachlist => \@attachlist);

	# TODO: Bless the error message with error class?
	die $res->{error} if exists $res->{error};

	dumpMessage (message_type => 'sqlitecall', command => 'execute',
		val1 => $args{name}, val2 => $args{asname})
		if $args{verbose} and $args{verbose} >= 2;

	return $res;
}

sub commit
{
	my $datastore = $::store || new Scraperwiki::Datastore;
	$datastore->request (maincommand => 'sqlitecommand',
		command => 'commit');
}

sub show_tables
{
	my %args = @_;
        my $name = $args{dbname}
		? $args{dbname}.'.sqlite_master'
		: 'sqlite_master';

	my $res = sqliteexecute (sqlquery => "select tbl_name, sql from $name where type='table'");
	return { map { @$_ } @{$res->{data}} };
}

sub table_info
{
	my %args = @_;
	$args{name} =~ /(.*\.|)(.*)/;
	my $res = sqliteexecute (sqlquery => "PRAGMA $1table_info(`$2`)");

	my @ret;
	foreach my $row (@{$res->{data}}) {
		push @ret, {map { $res->{keys}[$_] => $row->[$_] } 0..$#$row};
	}

	return \@ret;
}

sub save_var
{
	my %args = @_;

	my $vtype = ref $args{value};
	my $svalue = $args{value};

	if ($vtype) {
		warn "$vtype was stringified";
		$svalue .= '';
	}

	my $data = { name => $args{name}, value_blob => $svalue, type => $vtype };
        save_sqlite (unique_keys => ['name'],
		data => $data,
		table_name => 'swvariables',
		verbose => $args{verbose});
}

sub get_var
{
	my %args = @_;

	my $res = eval {
		sqliteexecute (sqlquery => 'select value_blob, type from swvariables where name=?',
			data => [$args{name}],
			verbose => $args{verbose})
	};
	if ($@) {
		return $args{default} if $@ =~ /sqlite3.Error: no such table/;
		die;
	}
	return $args{default} unless @{$res->{data}};

	my ($svalue, $vtype) = @{$res->{data}[0]};
	return $svalue;
}

sub httpresponseheader
{
	my %args = @_;

	dumpMessage (message_type => 'httpresponseheader',
		headerkey => $args{headerkey},
		headervalue => $args{headervalue});
}

sub gb_postcode_to_latlng
{
	my %args = @_;

	my $sres = scrape ('https://views.scraperwiki.com/run/uk_postcode_lookup/?postcode='.uri_escape ($args{postcode}));
	my $jres = decode_json ($sres);

	return [$jres->{lat}, $jres->{lng}]
		if exists $jres->{lat} and exists $jres->{lng};

	return undef;
}

1;
