import scraperwiki

# converter here http://www.rutter.uklinux.net/ostowiki.html
g1 = scraperwiki.geo.WGS84(56.0, -5.00, 200)
g2 = scraperwiki.geo.OSGB("NS 13021 82624")
print g1, g2

scraperwiki.delete({})
scraperwiki.save(["A"], {"A":"d1", "pt":g1.latlng()})
scraperwiki.save(["A"], {"A":"d2"}, latlng=g2.latlng())
    
print scraperwiki.retrieve({"A":None})
