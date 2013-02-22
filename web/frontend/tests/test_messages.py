from django.test import TestCase
from frontend.models import Message
from datetime import datetime, timedelta

class TestGetActiveMessage(TestCase):
    def setUp(self):
        self.date = datetime(2010, 12, 14, 18, 14, 4, 774094)
        self.message1 = Message.objects.create(text="AAA")

    def test_get_solo_message(self):
        active_message = Message.objects.get_active_message(self.date)
        self.failUnlessEqual(self.message1.text, active_message.text)

    def test_get_latest_message(self):
        message2 = Message.objects.create(text="BBB")
        active_message = Message.objects.get_active_message(self.date)
        self.failUnlessEqual(message2.text, active_message.text)

    def test_get_latest_message_with_dates(self):
        message3 = Message.objects.create(text="CCC", 
                                          start=self.date - timedelta(days=10),
                                          finish=self.date + timedelta(days=10))
        active_message = Message.objects.get_active_message(self.date)
        self.failUnlessEqual(message3.text, active_message.text)

    def test_ignore_future_messages(self):
        future_message = Message.objects.create(text="DDD", 
                                                start=self.date + timedelta(days=10))
        active_message = Message.objects.get_active_message(self.date)
        self.failUnlessEqual(self.message1.text, active_message.text)

    def test_ignore_past_messages(self):
        future_message = Message.objects.create(text="EEE", 
                                                finish=self.date - timedelta(days=10))
        active_message = Message.objects.get_active_message(self.date)
        self.failUnlessEqual(self.message1.text, active_message.text)
