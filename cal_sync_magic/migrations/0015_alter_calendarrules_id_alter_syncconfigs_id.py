# Generated by Django 4.1.5 on 2023-02-10 22:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cal_sync_magic", "0014_alter_googleaccount_credentials"),
    ]

    operations = [
        migrations.AlterField(
            model_name="calendarrules",
            name="id",
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="syncconfigs",
            name="id",
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
