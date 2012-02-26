#!/bin/sh
#
#  Script to run orbited. Supports options to run as a subprocess and/or as
#  a daemon.
#
subproc=
daemon=
uid=
gid=
vardir=/var
USAGE="[-s] [-d] [-u uid] [-g gid] [-v vardir]"

while getopts "dsu:g:v:" opt
do
	case $opt in
		s)	subproc=-s	;;
		d)	daemon=-d	;;
		u)	uid=$OPTARG	;;
		g)	gid=$OPTARG	;;
		v)	vardir=$OPTARG	;;
		*)
			echo usage: $USAGE
			exit 1
			;;
	esac
done

#  execute
#  -------
#  Contains the actual command to run
#
execute(){

#    cd /var/www/scraperwiki/uml
#    . /var/www/scraperwiki/bin/activate
#    exec orbited --config ./twister/orbited.cfg

    cd /var/www/scraperwiki
    . /var/www/scraperwiki/bin/activate
    exec orbited --config ./uml/twister/orbited.cfg
}

#  process
#  -------
#  Command processor, runs "execute" directly or as a subprocess. If as a
#  subprocess then trap SIGINT and SIGTERM so that the subprocess can be
#  killed first.
#
process(){

	if [ "$subproc" = "-s" ]
	then
		while true
		do
			execute &
			trap    "kill $! ; rm -f $vardir/run/orbited.pid ; exit" INT TERM
			wait    $!
		done
	else
		execute
	fi
}

#  If running as a daemon then execute a subshell and run process within
#  that in the background. Stdout and stderr are redirected to the log
#  file, stdin is closed, and the process ID of the process is stored in the
#  run file.
#
if [ "$daemon" = "-d" ]
then
	(
        process > $vardir/log/orbited 2>&1 <&- &
		echo $! > $vardir/run/orbited.pid
	)
else
	process
fi
