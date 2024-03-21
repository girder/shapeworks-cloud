# Generated by Django 3.2.25 on 2024-03-21 15:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0037_landmarks_constraints'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskprogress',
            name='message',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='taskprogress',
            name='error',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='taskprogress',
            name='project',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to='core.project'
            ),
        ),
    ]
