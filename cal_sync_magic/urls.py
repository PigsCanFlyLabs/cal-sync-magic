from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from cal_sync_magic import views

urlpatterns = [
    path("google-authorize/", views.GoogleAuthView.as_view(), name="google-authorize"),
    path("google-oauth-callback", views.GoogleCallBackView.as_view(), name="google-oauth-callback"),
    path("sync-config", views.ConfigureSyncs.as_view(), name="sync-config"),
    path("update-calendars", views.UpdateUserCalendars.as_view(), name="update-user-calendars"),
    path("update-gaccount-settings", views.UpdateGoogleAccounts.as_view(), name="update-gaccount-settings"),
    path("del-rule", views.DelRule.as_view(), name="del-rule"),
    path("del-sync", views.DelSync.as_view(), name="del-sync"),
    path("add-cal-rule", views.AddCalendarRule.as_view(), name="add-cal-rule"),
    path("add-sync", views.AddSync.as_view(), name="add-sync"),
    path("view-calendar-raw-events/<int:internal_id>", views.ShowRawEvents.as_view(), name="view-calendar-raw-events")
]
