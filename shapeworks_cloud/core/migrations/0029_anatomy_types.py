# Generated by Django 3.2.17 on 2023-03-29 01:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0028_landmarks_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='constraints',
            name='anatomy_type',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='landmarks',
            name='anatomy_type',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='optimizedparticles',
            name='anatomy_type',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='optimizedparticles',
            name='subject',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='particles',
                to='core.subject',
            ),
        ),
    ]
