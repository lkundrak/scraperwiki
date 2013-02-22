"""Tests all the functions in the savepage module of datastore"""

from scraperwiki.datastore import *

text1 = "ggy" * 100
text2 = "&^%$__--=  " * 200
text3 = "33333" * 20
tag1 = "tag1"
tag2 = "tag2"
name1 = "name1"
name2 = "name2"
name3 = "name3"

# clear the database of pages
deletepagesbytag("")
assert len(getnamesfromtag("")) == 0

# set up three pages
savepage(tag1, name1, text1)
savepage(tag1, name2, text2)
savepage(tag2, name3, text3)

# positive function calls
assert len(getnamesfromtag("")) == 3
assert len(getnamesfromtag(tag1)) == 2
assert getnamesfromtag(tag2) == [name3]
deletepagebyname(name1)
assert getnamesfromtag(tag1) == [name2]
assert gettagbyname(name3) == tag2
deletepagesbytag(tag2)
assert getnamesfromtag("") == [name2]
assert getpagebyname(name2) == text2

# negative function calls
assert not getnamesfromtag(tag2)
assert not gettagbyname(name1)
assert not getpagebyname(name1)

# clear the three entries again
deletepagebyname(name2)
assert not getnamesfromtag("")
print "Done"


