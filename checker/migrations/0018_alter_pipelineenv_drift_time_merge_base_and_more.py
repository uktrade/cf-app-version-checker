# Generated by Django 4.0.1 on 2022-03-30 17:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0017_alter_pipelineenv_cf_commit_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineenv',
            name='drift_time_merge_base',
            field=models.DurationField(blank=True),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='drift_time_simple',
            field=models.DurationField(blank=True),
        ),
    ]
