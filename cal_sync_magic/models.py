from datetime import datetime

from django.conf import settings
from django.utils.timezone import activate
from django.contrib.auth import get_user_model
from django.db import models
import json

import google.auth.transport.requests
import google.oauth2.credentials
from googleapiclient.discovery import build

User = get_user_model()

# Google related views
# See https://developers.google.com/identity/protocols/oauth2/web-server#python
scopes = ["https://www.googleapis.com/auth/calendar.events",
          "https://www.googleapis.com/auth/userinfo.email",
          "https://www.googleapis.com/auth/calendar.calendarlist",
          "openid"]
API_SERVICE_NAME = "calendar"
API_VERSION = "v3"

class GoogleAccount(models.Model):
    account_id = models.AutoField(primary_key=True, null=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    google_user_email = models.CharField(max_length=250, null=False)
    credentials = models.CharField(max_length=1000, null=False)
    credential_expiry = models.DateTimeField(null=True)
    last_refreshed = models.DateTimeField(default=datetime.now)
    unique_together = ["user", "google_user_email"]

    def get_credentials(self):
        stored_creds = json.loads(self.credentials)
        print(stored_creds)
        # Get expirery so we can figure out if we need a refresh
        if self.credential_expiry is not None:
            stored_creds["expiry"] = self.credential_expirery
        else:
            stored_creds["expiry"] = datetime.now()
        user_credentials = google.oauth2.credentials.Credentials(**stored_creds)
        # Callind expired gives a bunch of TZ errors so do the check ourself
        if stored_creds["expiry"].timestamp() <= datetime.now().timestamp():
            http_request = google.auth.transport.requests.Request()
            user_credentials.refresh(http_request)
        self.credentials = user_credentials.to_json()
        self.expiry = user_credentials.expiry
        self.save()
        return user_credentials

    def calendar_service(self):
        return build(API_SERVICE_NAME, API_VERSION, credentials=self.get_credentials())

    def refresh_calendars(self):
        """Refresh the user calendars. Defined here so we can share refresh logic."""
        current_cals = self.calendar_service().calendarList().list().execute()
        print(current_cals['items'])
        for cal in current_cals['items']:
            print(cal)
            deleted = "deleted" in cal and cal["deleted"]
            UserCalendar.objects.update_or_create(
                user=self.user,
                google_account=self,
                google_calendar_id=cal['id'],
                defaults={"deleted": deleted, "name": cal['summary']})


    class Meta:
        app_label = "cal_sync_magic"


class UserCalendar(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False)
    internal_calendar_id = models.AutoField(primary_key=True)
    google_account = models.ForeignKey(GoogleAccount, on_delete=models.CASCADE, null=False)
    google_calendar_id = models.CharField(max_length=500, null=False)
    name = models.CharField(max_length=500, null=True, blank=True)
    last_error = models.DateTimeField(null=True)
    deleted = models.BooleanField(default=False)
    last_sync_token = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        app_label = "cal_sync_magic"


class SyncConfigs(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False)
    src_calendars = models.ManyToManyField(
        'UserCalendar', related_name='src_calendars')
    sink_calendars = models.ManyToManyField(
        'UserCalendar', related_name='sink_calendars')

    class Meta:
        app_label = "cal_sync_magic"
