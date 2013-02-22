"""Tests all the datastore functions in the save module of datastore"""

from scraperwiki.datastore import retrieve, delete, insert, save
from scraperwiki.utils import log
import time
import datetime

def CheckDatastoreList(matchrecord, records):
    dates_scraped = [ ]
    log("Checking %s" % matchrecord)
    drecords = retrieve(matchrecord)
    for drecord in drecords:
        dates_scraped.append(drecord.pop("date_scraped"))
        #del drecord["run_id"] # other choss
    
        # sort out the discrepancy of dates converting to datetimes in the datastore
        if type(drecord.get("date")) == datetime.datetime:  # and type(record.get("date")) == datetime.date:
            ddate = drecord.get("date")
            if ddate.hour == 0 and ddate.minute == 0 and ddate.second == 0:
                drecord["date"] = datetime.date(ddate.year, ddate.month, ddate.day)
    
    drecords.sort()
    records.sort()
    if drecords != records:
        log("Error mismatch: %s != %s" % (drecords, records))
    return dates_scraped

        
# data to use in the test
d1, d2, d3, d10, d20, d30, d100, d200, d300 = "d1", "d2", "d3", "d10", "d20", "d30", "d100", "d200", "d300"
latlng1 = (11, 55)
latlng2 = (22, 66)
date1 = datetime.date(2000, 10, 10)
record1 = {"A":d1, "B":d2, "C":d3, "latlng":latlng1}
record2 = {"A":d1, "B":d20, "E":d30, "latlng":latlng2}
record2a = {"A":d1, "B":d20, "E":d300, "latlng":latlng2}
record3 = {"A":d100, "B":d2, "C":d300, "date":date1}
record1a = {"A":d100, "B":d2, "C":d3}

# clear the datastore
delete({})

# add and verify a single record
insert(record1)
CheckDatastoreList({}, [record1])
insert(record2)
CheckDatastoreList({}, [record1, record2])

CheckDatastoreList({"B":d20}, [record2])
CheckDatastoreList({"A":None}, [record1, record2])
CheckDatastoreList({"A":d1}, [record1, record2])
CheckDatastoreList({"A":d10}, [])

CheckDatastoreList({"C":None}, [record1])
save(["B", "C"], record3)    # new record
CheckDatastoreList({"C":None}, [record1, record3])
time.sleep(1)
save(["B", "C"], record1a)   # over-write record1
time.sleep(1)
CheckDatastoreList({"C":None}, [record1a, record3])
delete({"C":None})

# now check the over-writing only changes the date_scraped if there has been a change
dates_scraped1 = CheckDatastoreList({}, [record2])
time.sleep(1)
save(["A"], record2)   # over-write record1
dates_scraped2 = CheckDatastoreList({}, [record2])
time.sleep(1)
save(["A"], record2a)   # over-write record1
dates_scraped3 = CheckDatastoreList({}, [record2a])
log("what ther")
time.sleep(0.2)
log(str(dates_scraped1))
time.sleep(0.2)
log(str(dates_scraped2))
time.sleep(0.2)
log(str(dates_scraped3))
time.sleep(1)

if dates_scraped1 != dates_scraped2:
    log("Error: dates scraped not equal")
if dates_scraped2 == dates_scraped3:
    log("Error: dates scraped should not be equal")
delete({})

time.sleep(1)

print "Done"

​