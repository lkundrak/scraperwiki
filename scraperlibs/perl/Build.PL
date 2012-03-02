use strict;
use warnings;

use Module::Build;

my $build = Module::Build->new(
	module_name	=> 'Scraperwiki',
	license		=> 'perl',
	dist_author	=> 'Lubomir Rintel <lkundrak@v3.sk>',
	dist_version	=> '0.1',
	requires	=> {
		'LWP::Simple'	=> 0,
	},
	build_requires => {
		'Test::More'	=> 0,
	}
);

$build->create_build_script;
