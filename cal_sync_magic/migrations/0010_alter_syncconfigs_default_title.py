# Generated by Django 4.1.5 on 2023-01-31 06:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cal_sync_magic', '0009_syncconfigs_default_title_syncconfigs_hide_details_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='syncconfigs',
            name='default_title',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]