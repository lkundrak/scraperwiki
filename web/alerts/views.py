from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from codewiki.models.vault import Vault
from codewiki.models import Scraper, ScraperRunEvent


def compose_email(runevents, vault):
    context = locals()

    text_content = render_to_string('emails/vault_exceptions.txt', context) 
    html_content = render_to_string('emails/vault_exceptions.html', context)
    #print text_content
    return {'text': text_content, 'html': html_content}

def alert_vault_members_of_exceptions(vault):
    result = []

    subject ='Script errors in your %s ScraperWiki vault' % vault.name

    runevents = select_exceptions_that_have_not_been_notified(vault)
    if len(runevents) > 0:
        for member in vault.members.all():
            content = compose_email(runevents, vault)
            msg = EmailMultiAlternatives(subject, content['text'],
                'ScraperWiki Alerts <noreply@scraperwiki.com>', to=[member.email])
            msg.attach_alternative(content['html'], "text/html")
 
            try:
                msg.send(fail_silently=False)
 
            except EnvironmentError as e:
                print 'EnvironmentError in alert_vault_members_of_exceptions'
                result.append({
                    'recipient': member.email,
                    'status' : 'fail',
                    'error' : "Couldn't send email",
                })

            else:
                result.append({
                    'recipient': member.email,
                    'status': 'okay'
                })
                map(lambda one_runevent: one_runevent.set_notified(), runevents)

    return result

def select_exceptions_that_have_not_been_notified(vault):
    l = []
    for scraper in Scraper.objects.filter(vault=vault).exclude(privacy_status="deleted"):
        runevents = ScraperRunEvent.objects.filter(scraper=scraper).order_by('-run_started')[:1]
        #print runevents
        if not runevents:
            continue
        mostrecent = runevents[0]
        if mostrecent.exception_message and not mostrecent.notified:
            l.append(mostrecent)
    return l
