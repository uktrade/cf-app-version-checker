# Generated by Django 4.0.1 on 2022-04-05 15:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0025_rename_config_id_fk_pipelineenv_pipelineapp_fk'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pipelineenv',
            old_name='pipelineapp_fk',
            new_name='pipeline_app_fk',
        ),
    ]