# Generated by Django 4.0.1 on 2022-04-05 17:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0026_rename_pipelineapp_fk_pipelineenv_pipeline_app_fk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineapp',
            name='config',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
