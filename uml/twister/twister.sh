#!/bin/sh

cd /var/www/scraperwiki/uml
. /var/www/scraperwiki/bin/activate
exec ./twister/twister.py $*
