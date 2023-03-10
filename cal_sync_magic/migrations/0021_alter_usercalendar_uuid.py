# Generated by Django 4.1.5 on 2023-02-11 08:24

from django.db import migrations, models

import cal_sync_magic.models


class Migration(migrations.Migration):

    dependencies = [
        ("cal_sync_magic", "0020_alter_usercalendar_uuid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usercalendar",
            name="uuid",
            field=models.UUIDField(
                default=cal_sync_magic.models.UserCalendar.hex_uuid, unique=True
            ),
        ),
    ]
