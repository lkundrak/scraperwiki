#!/bin/sh
# Execute
# Run a script by passing to the local scriptmgr.
# scriptmgr should be already running.

usage="execute.sh [-s] [-l php|python|ruby] code"

sync=
language=python

# Option parsing
while true
do
  case $1 in
    (-s) sync=yes;shift 1;;
    (-l) language=$2;shift 2;;
    *) break;;
  esac
done

Execute () {
    # Send the Execute command to the scripmgr server, using $1
    # as the body of the command.
    set -x
    curl -d "$1" http://127.0.0.1:9001/Execute
    set +x
}

id="test-$$"


# We need to quote the code, because it will appear inside a
# JSON string.  Not sure this is completely robust, but it's a
# start.
code=$(echo -n "$1" | sed 's/[\\"]/\\&/g')
# Templated JSON object passed to Execute
data=$( cat <<!
{
    "runid" : "$id",
    "code": "$code",
    "scrapername": "test",
    "scraperid": "$id",
    "language": "$language"
}
!
)

if [ -n "$sync" ]
then
    Execute "$data"
else
    Execute "$data" &
fi
