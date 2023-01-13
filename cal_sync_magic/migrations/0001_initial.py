# Generated by Django 4.1.4 on 2023-01-10 01:51

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GoogleAccount",
            fields=[
                ("account_id", models.AutoField(primary_key=True, serialize=False)),
                ("google_user_email", models.CharField(max_length=250)),
                ("credentials", models.CharField(max_length=1000)),
                ("last_refreshed", models.DateTimeField(default=datetime.datetime.now)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserCalendar",
            fields=[
                (
                    "internal_calendar_id",
                    models.AutoField(primary_key=True, serialize=False),
                ),
                ("google_calendar_id", models.CharField(max_length=500)),
                (
                    "google_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="cal_sync_magic.googleaccount",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SyncConfigs",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sink_calendars",
                    models.ManyToManyField(
                        related_name="sink_calendars", to="cal_sync_magic.usercalendar"
                    ),
                ),
                (
                    "src_calendars",
                    models.ManyToManyField(
                        related_name="src_calendars", to="cal_sync_magic.usercalendar"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
