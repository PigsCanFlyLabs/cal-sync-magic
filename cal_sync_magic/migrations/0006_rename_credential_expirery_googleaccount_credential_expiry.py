# Generated by Django 4.1.5 on 2023-01-15 01:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cal_sync_magic", "0005_googleaccount_credential_expirery"),
    ]

    operations = [
        migrations.RenameField(
            model_name="googleaccount",
            old_name="credential_expirery",
            new_name="credential_expiry",
        ),
    ]
