package Scraperwiki::Datastore;

use strict;
use warnings;

use JSON;
use IO::Socket::INET;
use URI;

sub new
{
	my $class = shift;
	my $self = shift || {};

	$self->{m_socket} ||= undef;
#	$self->{m_host} ||= undef;
#	$self->{m_port} ||= undef;
	$self->{m_host} ||= 'localhost';
	$self->{m_port} ||= 9003;
	$self->{m_scrapername} ||= '';
	$self->{m_runid} ||= '';
	$self->{m_attachables} ||= [];
	$self->{m_webstore_port} ||= 0;

	return bless $self => $class;

}

sub ensure_connected
{
	my $self = shift;

	return if $self->{m_socket};

	my $sock = $self->{m_socket} = new IO::Socket::INET (
		PeerAddr => $self->{m_host},
		PeerPort => $self->{m_port},
		Proto => 'tcp')
		or die "Could not connect: $!";

	my $uri = new URI ('/');
	$uri->query_form (uml => 'lxc',
		port => $self->{m_port},
		vscrapername => $self->{m_scrapername},
		vrunid => $self->{m_runid});

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
	my $sock = $self->{m_socket};

	print $sock encode_json (\%args);
	return decode_json (<$sock> || die "Could not read response: $!");
}

1;
