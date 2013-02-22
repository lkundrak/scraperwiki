from django.conf import settings

from recuro.views import notify
from recuro.xero import XeroPrivateClient

import helper
from mock import Mock, patch

recurly_xml = """
    <?xml version="1.0" encoding="UTF-8"?> <new_account_notification> <account> <account_code>3-test-20120424T152301</account_code> <username nil="true"></username> <email>test@testerson.com</email> <first_name>Test</first_name> <last_name>Testerson</last_name> <company_name></company_name> </account> </new_account_notification>
      """

@patch('recuro.recurly_parser.parse')
def it_should_pass_the_notification_to_the_notification_parser(mock_parse):
    class TestObject:
        def save(self):
            return [{'status':'200'}, None]

    rf = helper.RequestFactory()
    mock_parse.return_value = TestObject()
    mock_request = rf.post('/notify/', dict(body=recurly_xml))
    response = notify(mock_request, settings.RECURLY_API_KEY)
    assert response.status_code == 200
    assert mock_parse.called

@patch.object(XeroPrivateClient, 'save')
def it_should_call_save_on_the_contact(mock_save):
    rf = helper.RequestFactory()
    mock_save.return_value = [{'status':'200'}, None]
    mock_request = rf.post('/notify/', dict(body=recurly_xml))
    response = notify(mock_request, settings.RECURLY_API_KEY)
    assert response.status_code == 200
    assert mock_save.called

@patch.object(XeroPrivateClient, 'save')
def it_should_call_save_on_the_invoice(mock_save):
    from recurly_parse_spec import recurly_successful_payment
    mock_save.return_value = [{'status':'200'}, None]
    rf = helper.RequestFactory()
    mock_request = rf.post('/notify/',
      dict(body=recurly_successful_payment))
    response = notify(mock_request, settings.RECURLY_API_KEY)
    assert response.status_code == 200
    assert mock_save.called

def it_errors_if_apikey_wrong():
    from recurly_parse_spec import recurly_successful_payment
    rf = helper.RequestFactory()
    mock_request = rf.post('/notify/',
      dict(body=recurly_successful_payment))
    response = notify(mock_request, "sdfsdfsd")
    assert response.status_code == 403
