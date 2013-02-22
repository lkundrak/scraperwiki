#!/usr/bin/env python

import urllib2
from lxml import etree

class Person(object):
    def __init__(self, xml):
        self.xml = xml

    @property
    def first_name(self):
        return self.xml.xpath('first-name')[0].text

    @property
    def last_name(self):
        return self.xml.xpath('last-name')[0].text

    @property
    def id(self):
        return self.xml.xpath('id')[0].text

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'%s %s (%s)' % (self.first_name, self.last_name, self.id)


class TaskCategory(object):
    def __init__(self, xml):
        self.xml = xml

    @property
    def name(self):
        return self.xml.xpath('name')[0].text

    @property
    def id(self):
        return self.xml.xpath('id')[0].text

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.id)

class Tag(object):
    def __init__(self, xml):
        self.xml = xml

    @property
    def name(self):
        return self.xml.xpath('name')[0].text

    @property
    def id(self):
        return self.xml.xpath('id')[0].text

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.id)

class User(object):
    def __init__(self, xml):
        self.xml = xml

    @property
    def name(self):
        return self.xml.xpath('name')[0].text

    @property
    def email(self):
        return self.xml.xpath('email-address')[0].text

    @property
    def id(self):
        return self.xml.xpath('id')[0].text

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'%s <%s> (%s)' % (self.name, self.email, self.id)

class HighRiseException(Exception): pass

class HighRise(object):
    note_xml_template = '<note><body>%s</body></note>'
    #task_xml_template = '<task><body>%s</body><frame>%s</frame><owner-id type="integer">%s</owner-id>%s%s</task>'
    task_xml_template = '<task><body>%s</body><frame>%s</frame>%s%s<owner-id type="integer">%s</owner-id></task>'
    tag_xml_template = '<name>%s</name>'
    person_xml_template = '''
<person>
  <first-name>%s</first-name>
  <last-name>%s</last-name>
  <contact-data>
    <email-addresses>
      <email-address>
        <address>%s</address>
        <location>Other</location>
      </email-address>
    </email-addresses>
  </contact-data>
</person>
    '''

    def __init__(self, project, api_key):
        self.base_url = 'https://%s.highrisehq.com' % project
        
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, self.base_url, api_key, 'X')

        authhandler = urllib2.HTTPBasicAuthHandler(passman)

        opener = urllib2.build_opener(authhandler)

        urllib2.install_opener(opener)

    def get_task_category_by_name(self, name):
        for c in self.list_task_categories():
            if c.name == name:
                return c
        return None

    def list_task_categories(self):
        url = self.base_url + '/task_categories.xml'
        resp = urllib2.urlopen(url)
        if resp.code != 200:
            raise HighRiseException("Error listing categories")
        xml = resp.read()
        doc = etree.XML(xml)
        categories = doc.xpath('/task-categories/task-category')
        return [TaskCategory(c) for c in categories]

    def get_tag_by_name(self, name):
        for t in self.list_tags():
            if t.name == name:
                return t
        return None

    def list_tags(self):
        url = self.base_url + '/tags.xml'
        resp = urllib2.urlopen(url)
        if resp.code != 200:
            raise HighRiseException("Error listing tags")
        xml = resp.read()
        doc = etree.XML(xml)
        tags = doc.xpath('/tags/tag')
        return [Tag(t) for t in tags]

    def get_user_by_email(self, email):
        for u in self.list_users():
            if u.email == email:
                return u
        return None

    def list_users(self):
        url = self.base_url + '/users.xml'
        resp = urllib2.urlopen(url)
        if resp.code != 200:
            raise HighRiseException("Error listing users")
        xml = resp.read()
        doc = etree.XML(xml)
        users = doc.xpath('/users/user')
        return [User(u) for u in users]

    def search_people_by_email(self, email):
        url = self.base_url + '/people/search.xml?criteria[email]=%s' % email
        resp = urllib2.urlopen(url)
        if resp.code != 200:
            raise HighRiseException("Error searching for people")
        xml = resp.read()
        doc = etree.XML(xml)
        people = doc.xpath('/people/person')
        return [Person(p) for p in people]

    def get_person_by_id(self, person_id):
        pass

    def create_note_for_person(self, note, person_id):
        url = self.base_url + '/people/%s/notes.xml' % person_id
        xml_note = self.note_xml_template % note
        req = urllib2.Request(url, xml_note, {"Content-type": "application/xml"})
        resp = urllib2.urlopen(req)
        if resp.code != 201:
            raise HighRiseException("Error creating note")
        xml = resp.read()

    def create_task_for_person(self, task, person_id, category_id=None, subject_id='', frame='this_week'):
        url = self.base_url + '/tasks.xml'
        if category_id:
            category = '<category-id type="integer">%s</category-id>' % category_id
        else:
            category = ''

        if subject_id:
            subject = '<subject-type>Party</subject-type><subject-id>%s</subject-id>' % subject_id
        else:
            subject = ''

        xml_task = self.task_xml_template % (task, frame, category, subject, person_id)
        req = urllib2.Request(url, xml_task, {"Content-type": "application/xml"})
        resp = urllib2.urlopen(req)
        if resp.code != 201:
            raise HighRiseException("Error creating task")
        xml = resp.read()
        print xml

    def tag_person(self, person_id, tag_text):
        url = self.base_url + '/people/%s/tags.xml' % person_id
        xml_note = self.tag_xml_template % tag_text
        req = urllib2.Request(url, xml_note, {"Content-type": "application/xml"})
        resp = urllib2.urlopen(req)
        if resp.code != 201:
            raise HighRiseException("Error tagging person")
        doc = etree.XML(resp.read())
        return Tag(doc)

    def create_person(self, first_name, last_name, email):
        url = self.base_url + '/people.xml'
        xml_person = self.person_xml_template % (first_name, last_name, email)
        req = urllib2.Request(url, xml_person, {"Content-type": "application/xml"})
        resp = urllib2.urlopen(req)
        if resp.code != 201:
            raise HighRiseException("Error creating person")
        doc = etree.XML(resp.read())
        return Person(doc)
