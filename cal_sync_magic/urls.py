from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from cal_sync_magic import views

// See https://developers.google.com/identity/protocols/oauth2/web-server#python
urlpatterns = [
    path("/google-authorize", views.GoogleAuthView.as_view(), name="google-authorize"),
    path("/google-oauth-callback", views.GoogleCallBackView.as_view(), name="google-oauth-callback"),
    
]
