import os

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "cal_sync_magic",
    "testapp",
]
SITE_ID = 1

ROOT_URLCONF = "testapp.urls"

DEBUG = True

STATIC_URL = "/static/" 
