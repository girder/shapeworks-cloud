# Generated by Django 3.2.13 on 2022-09-15 13:15

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import s3_file_field.fields


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0011_timestamped_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='CachedAnalysisModePCA',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('pca_value', models.FloatField()),
                ('lambda_value', models.FloatField()),
                ('file', s3_file_field.fields.S3FileField()),
            ],
        ),
        migrations.CreateModel(
            name='CachedAnalysisMode',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('mode', models.IntegerField()),
                ('eigen_value', models.FloatField()),
                ('explained_variance', models.FloatField()),
                ('cumulative_explained_variance', models.FloatField()),
                ('pca_values', models.ManyToManyField(to='core.CachedAnalysisModePCA')),
            ],
        ),
        migrations.CreateModel(
            name='CachedAnalysis',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('mean_shape', s3_file_field.fields.S3FileField()),
                ('charts', models.JSONField()),
                ('modes', models.ManyToManyField(to='core.CachedAnalysisMode')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='project',
            name='last_cached_analysis',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to='core.cachedanalysis'
            ),
        ),
    ]
