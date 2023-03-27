# Generated by Django 3.2.17 on 2023-03-27 15:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0027_task_abort'),
    ]

    operations = [
        migrations.AddField(
            model_name='landmarks',
            name='metadata',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='landmarks',
            name='project',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='landmarks',
                to='core.project',
            ),
        ),
    ]
