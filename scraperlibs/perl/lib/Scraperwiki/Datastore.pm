package Scraperwiki::Datastore;

use strict;
use warnings;

use JSON;
use IO::Socket::INET;
use URI;

sub new
{
	my $class = shift;

	my $self = { socket => undef };
	$self->{host} = shift || 'localhost';
	$self->{port} = shift || 9003;
	$self->{scrapername} = shift || '';
	$self->{runid} = shift || '';
	$self->{attachables} = shift || [];
	$self->{verification_key} = shift || '';

	return bless $self => $class;

}

sub ensure_connected
{
	my $self = shift;

	return if $self->{socket};

	my $sock = $self->{socket} = new IO::Socket::INET (
		PeerAddr => $self->{host},
		PeerPort => $self->{port},
		Proto => 'tcp')
		or die "Could not connect: $!";

	my $uri = new URI ('/');
	$uri->query_form (uml => 'lxc',
		port => $self->{port},
		vscrapername => $self->{scrapername},
		vrunid => $self->{runid},
		verify => $self->{verification_key},
		progress_ticks => 'yes');

	print $sock 'GET '.$uri." HTTP/1.1\r\n\r\n";
	my $result = decode_json (<$sock> || die "Could not read response: $!");

	die $result->{error} if exists $result->{error};
	die $result->{status} unless $result->{status} eq 'good';
}

sub request
{
	my $self = shift;
	my %args = @_;

	$self->ensure_connected;
	my $sock = $self->{socket};

	print $sock encode_json (\%args)."\n";
	return decode_json (<$sock> || die "Could not read response: $!");
}

1;
