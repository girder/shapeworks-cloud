# Generated by Django 3.2.10 on 2021-12-09 17:41

from django.db import migrations
import s3_file_field.fields


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='file',
            field=s3_file_field.fields.S3FileField(null=True),
        ),
    ]
