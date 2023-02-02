# Generated by Django 3.2.16 on 2022-12-16 14:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0019_cam_pca_particles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='constraints',
            name='optimized_particles',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='constraints',
                to='core.optimizedparticles',
            ),
        ),
    ]
