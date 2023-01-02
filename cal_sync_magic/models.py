from django.db import models
from datetime import datetime
from django.contrib.auth.models import User

class GoogleAccount(models.Model):
    account_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    token = models.CharField(max_length=250, null=False)
    refresh_token = models.CharField(max_length=250, null=False)
    token_uri = models.CharField(max_length=250, null=False)
    client_id = models.CharField(max_length=250, null=False)
    client_secret = models.CharField(max_length=250, null=False)
    scopes = models.CharField(max_length=250, null=False)
    last_refreshed = models.DateTimeField(default=datetime.now)


class UserCalendar(models.Model):
    internal_calendar_id = models.AutoField(primary_key=True)
    google_account = models.ForeignKey(GoogleAccount, on_delete=models.CASCADE)


class SyncConfigs(models.Model):
    src_calendars = models.ManyToManyField(
        'UserCalendar', related_name='src_calendars')
    sink_calendars = models.ManyToManyField(
        'UserCalendar', related_name='sink_calendars')
