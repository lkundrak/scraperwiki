from recuro import xero

session = None

def setup():
    global session
    session = xero.XeroPrivateClient()

def it_can_import_xero():
    from recuro import xero

def it_can_authorise_with_xero():
    assert session

def it_can_call_a_xero_function():
    # Is allowed access to internal _request method; it's
    # irrelevant which method gets called.  Don't think that this
    # allowance extends to you.
    resp, content = session._xero_request('/Contacts')
    print repr(content)
    assert resp['status'] == '200'

def it_can_post_an_xml_contact():
    from recuro.recurly_parser import Contact
    from recurly_parse_spec import recurly_contact
    contact = Contact(recurly_contact)
    contact.get_address()
    resp, content = contact.save()
    assert resp['status'] == '200'

def it_can_post_an_xml_contact_with_an_ampersand_in():
    from recuro.recurly_parser import Contact
    from recurly_parse_spec import recurly_contact
    contact = Contact(recurly_contact)
    contact.get_address()
    contact.name = "Test & Testerson Limited"
    resp, content = contact.save()
    assert resp['status'] == '200'

def it_can_post_an_xml_invoice_with_tax():
    from recuro.recurly_parser import Invoice
    from recurly_parse_spec import recurly_successful_payment
    invoice = Invoice(recurly_successful_payment)
    invoice.get_tax_details()
    resp, content = invoice.save()
    assert resp['status'] == '200'

def it_can_post_an_xml_invoice_without_tax():
    from recuro.recurly_parser import Invoice
    from recurly_parse_spec import recurly_successful_payment
    invoice = Invoice(recurly_successful_payment)
    invoice.get_tax_details()
    invoice.vat_number = None
    invoice.tax_in_cents = 0
    resp, content = invoice.save()
    print repr(content)
    assert resp['status'] == '200'
