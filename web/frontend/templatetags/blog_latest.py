import feedparser
from BeautifulSoup import BeautifulSoup
from django import template
from django.http import HttpResponse
from django.conf import settings
from django.core.cache import cache

register = template.Library()

@register.inclusion_tag('frontend/templatetags/blog_latest.html')

def blog_latest():
    
    #get the feed - either from the cache or straight from rss
    feed = cache.get('blog_feed', False)
    if not feed:
        feed = feedparser.parse(settings.BLOG_FEED)        
        cache.set('blog_feed', feed, 120)

    if feed.entries:
        #get the headline story and attempt to strip an image out of it
        headline = feed.entries[0]
        headline_image_url = ''
        soup = BeautifulSoup(headline.content[0].value)
        img_tags = soup.findAll('img')
        if len(img_tags) > 0:
            if img_tags[0]['src'].find('http://feeds.wordpress.com') == -1:
                headline_image_url = img_tags[0]['src']

        #make it https://, as everything on page needs to be
        headline_image_url = headline_image_url.replace('http://', 'https://')
        headline.summary = headline.summary.replace('http://stats.wordpress.com/', 'https://stats.wordpress.com/')

        #get a few other recent stories
        subs = []
        subs.append(feed.entries[1])
        subs.append(feed.entries[2])
        #subs.append(feed.entries[3])        
        return {'headline': headline, 'headline_image_url': headline_image_url, 'subs': subs}
