from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class GoogleAccount(models.Model):
    account_id = models.AutoField(primary_key=True, null=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    google_user_email = models.CharField(max_length=250, null=False)
    credentials = models.CharField(max_length=1000, null=False)
    last_refreshed = models.DateTimeField(default=datetime.now)
    unique_together = ["user", "google_user_email"]

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
