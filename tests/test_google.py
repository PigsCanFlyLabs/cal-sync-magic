from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class TestGoogle(TestCase):
    """ Test our Google integration. """
    def setUp(self):
        user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')
        user.save()
        self.user = user

    def test_not_logged_in(self):
        endpoint = "google-authorize"
        client = Client()
        client.logout()
        # Follow false does not seem to work so set follow to true and check the rdr chain
        response = client.get(reverse(endpoint), follow=True)
        chain = response.redirect_chain
        self.assertIn("/accounts/login/", chain[0][0])
        

    def test_logged_in_nop(self):
        endpoint = "sync-config"
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse(endpoint), follow=True)
        
    def test_redirect_to_google(self):
        endpoint = "google-authorize"
        client = Client()
        client.force_login(self.user)
        # Follow false does not seem to work so set follow to true and check the rdr chain
        response = client.get(reverse(endpoint), follow=True)
        chain = response.redirect_chain


