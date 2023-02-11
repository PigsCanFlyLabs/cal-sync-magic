# Generated by Django 4.1.5 on 2023-02-11 08:04

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("cal_sync_magic", "0019_alter_usercalendar_last_error"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usercalendar",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
