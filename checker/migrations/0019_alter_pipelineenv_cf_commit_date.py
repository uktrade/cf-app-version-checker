# Generated by Django 4.0.1 on 2022-03-30 17:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0018_alter_pipelineenv_drift_time_merge_base_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_commit_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
