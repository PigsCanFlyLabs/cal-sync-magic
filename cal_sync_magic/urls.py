from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from cal_sync_magic import views

urlpatterns = [
    path("google-authorize", views.GoogleAuthView.as_view(), name="google-authorize"),
    path("google-oauth-callback", views.GoogleCallBackView.as_view(), name="google-oauth-callback"),
    path("sync-config", views.ConfigureSyncs.as_view(), name="sync-config"),
]
