# Generated by Django 4.0.1 on 2022-03-30 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0003_alter_pipelineenv_config_id_fk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineapp',
            name='repo_scan_start_time',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scan_start_time',
            field=models.DateTimeField(),
        ),
    ]