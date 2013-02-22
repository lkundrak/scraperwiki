#!/usr/bin/env python

from django import template
register = template.Library()

from documentation.titles import page_titles

@register.simple_tag
def doc_link_full(template_name, language, title=None, text=None):
    template_name = template_name.replace('LANG', language)
    if not text:
        text = page_titles[template_name][0]
    if title:
        return '''<a href="/docs/%s/%s" title="%s">%s</a>''' % (language, template_name, title, text)
    else:
        return '''<a href="/docs/%s/%s">%s</a>''' % (language, template_name, text)

@register.simple_tag
def doc_link_toc(template_name, language, description=None, text=None):
    template_name = template_name.replace('LANG', language)
    text = text or page_titles[template_name][0]
    html = '''<a href="/docs/%s/%s"><h4>%s</h4>''' % (language, template_name, text)
    if description:
        html += ''' <span>%s</span>''' % (description)
    return '<li>' + html + '</a></li>'

@register.simple_tag
def doc_change_lang(request, from_lang, to_lang):
    return request.path.replace(from_lang, to_lang)




