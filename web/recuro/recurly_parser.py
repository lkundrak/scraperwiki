import string

from django.conf import settings
from lxml import etree,html
import recurly
from jinja2 import Template

from recuro.xero import XeroPrivateClient

def parse(body):
    if '<new_account_notification>' in body:
        contact = Contact(body)
        contact.get_address()
        return contact
    if '<successful_payment_notification>' in body:
        invoice = Invoice(body)
        invoice.get_tax_details()
        return invoice

class Contact(XeroPrivateClient):
    def __init__(self, xml=None, **k):
        # Example XML in specs/recurly_parse_spec.py
        doc = html.fromstring(xml)
        self.number = doc.xpath('//account_code')[0].text
        self.name = doc.xpath('//company_name')[0].text
        self.first_name = doc.xpath('//first_name')[0].text
        self.last_name = doc.xpath('//last_name')[0].text
        self.email = doc.xpath('//email')[0].text

        self.address1 = None
        self.address2 = None
        self.city = None
        self.state = None
        self.country =  None
        self.zip = None
        self.vat_number = None

        if self.name is None:
            self.name = "%s %s" % (self.first_name, self.last_name)
        super(Contact, self).__init__(**k)

    def get_address(self):
        recurly.API_KEY = settings.RECURLY_API_KEY
        acc = recurly.Account.get(self.number)
        billing = acc.billing_info
        self.address1 = billing.address1
        self.address2 = billing.address2
        self.city = billing.city
        self.state = billing.state
        self.country = billing.country
        self.zip = billing.zip
        self.vat_number = billing.vat_number

    def to_xml(self):
        template = Template( """
            <Contact>
                <ContactNumber>{{number}}</ContactNumber>
                <Name>{{name|e}}</Name>
                <FirstName>{{first_name|e}}</FirstName>
                <LastName>{{last_name|e}}</LastName>
                <EmailAddress>{{email}}</EmailAddress>
                {% if vat_number %}
                <TaxNumber>{{vat_number}}</TaxNumber>
                {% endif %}
                <Addresses>
                    <Address>
                        <AddressType>STREET</AddressType>
                        <AddressLine1>{{address1|e}}</AddressLine1>
                        {% if address2 %}
                        <AddressLine2>{{address2|e}}</AddressLine2>
                        {% endif %}
                        <City>{{city|e}}</City>
                        <Region>{{state}}</Region>
                        <Country>{{country}}</Country>
                        <PostalCode>{{zip}}</PostalCode>
                    </Address>
                </Addresses>
            </Contact>
            """ )
        return template.render(number=self.number, name=self.name,
                        first_name=self.first_name, last_name=self.last_name,
                        email=self.email, vat_number=self.vat_number,
                        address1=self.address1, address2=self.address2,
                        city=self.city, state=self.state, country=self.country,
                        zip=self.zip).encode('utf-8')

class Invoice(XeroPrivateClient):
    def __init__(self, xml=None, **k):
        # Example XML in specs/recurly_parse_spec.py
        doc = html.fromstring(xml.encode('UTF-8'))
        # Map recurly account code to xero contact number.
        self.contact_number = doc.xpath('//account_code')[0].text
        self.amount_in_cents = int(
          doc.xpath("//amount_in_cents")[0].text)
        self.invoice_date = doc.xpath('//date')[0].text
        self.status = 'UNKNOWN'
        if 'successful_payment_notification' in xml:
            self.status = 'PAID'
        self.invoice_number = doc.xpath('//invoice_number')[0].text
        self.invoice_ref = 'RECURLY' + self.invoice_number
        self.account_code = settings.XERO_ACCOUNT_CODE

        self.vat_number = None
        self.subtotal_in_cents = 0
        self.tax_in_cents = 0
        self.total_in_cents = 0

        super(Invoice, self).__init__(**k)

    def get_tax_details(self):
        recurly.API_KEY = settings.RECURLY_API_KEY
        invoice = recurly.Invoice.get(self.invoice_number)
        self.vat_number = invoice.vat_number
        self.subtotal_in_cents = invoice.subtotal_in_cents
        self.tax_in_cents = invoice.tax_in_cents
        self.total_in_cents = invoice.total_in_cents

    def to_xml(self):
        template = Template("""
          <Invoice>
            <InvoiceNumber>{{invoice_ref}}</InvoiceNumber>
            <Type>ACCREC</Type>
            <Contact>
              <ContactNumber>{{contact_number}}</ContactNumber>
            </Contact>
            <Date>{{short_date}}</Date>
            <DueDate>{{short_date}}</DueDate>
            <CurrencyCode>USD</CurrencyCode>
            <LineItems>
              <LineItem>
                <Description>ScraperWiki Vault</Description>
                <Quantity>1</Quantity>
                <UnitAmount>{{price}}</UnitAmount>
                <AccountCode>{{account_code}}</AccountCode>
                <TaxType>{{tax_type}}</TaxType>
              </LineItem>
            </LineItems>
          </Invoice>
          """)

        price = "%.2f" % (self.subtotal_in_cents/100.0)
        tax = "%.2f" % (self.tax_in_cents/100.0)
        short_date = self.invoice_date[:10]
        tax_type = "OUTPUT2"
        if self.tax_in_cents == 0:
            tax_type = "NONE"

        return template.render(price=price, short_date=short_date,
          tax_type=tax_type, **self.__dict__).encode('utf-8')
