#!/bin/bash
for i in {1..90}
do
	echo 'Running' $i
	echo "Content-Length: 110"  -d "code=import time;print 1-2;time.sleep(10);print 'hello'&run_id="$i"&scrapername=test&scraper_id="$i"&language=python"
	curl -H "Content-Length: 110"  -d "code=import time;print 1-2;time.sleep(10);print 'hello'&run_id="$i"&scrapername=test&scraper_id="$i"&language=python" http://127.0.0.1:8001/run &
done

echo ''
echo ''

