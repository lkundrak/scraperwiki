#!/bin/sh
# hardkilllocal.sh

# Find all lost processes in the system and kill them.  
# Necessary when killlocal might have hit errors during execution.

# Note: Just a newline.
IFS='
'

killed_count=1
while [ $killed_count -gt 0 ]
do
    printf "checking none left ...\n"
    killed_count=0
    for t in twister www/scraperwiki/uml scriptmgr.js
    do
        for s in $(ps -Af | grep -e "$t" | grep -v "grep ")
        do
            printf "killing %s\n" "$s"
            ( IFS=' '
              set -- $s
              kill -9 $2 )
            killed_count=$((killed_count + 1))
        done
    done
done

printf "... all killed\n"

