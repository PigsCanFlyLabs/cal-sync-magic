from django.test import TestCase


class TestGoogle(TestCase):
    def test_trivial(self):
        self.assertEqual(True, True)
