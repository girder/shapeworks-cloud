# Generated by Django 3.2.20 on 2023-08-18 18:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0033_project_readonly'),
    ]

    operations = [
        migrations.AddField(
            model_name='cachedanalysis',
            name='good_bad_angles',
            field=models.JSONField(default=list),
        ),
    ]
