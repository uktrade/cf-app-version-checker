# Generated by Django 4.0.1 on 2022-03-30 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0013_alter_pipelineenv_config_env'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineenv',
            name='git_compare_merge_base_commit',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='git_compare_merge_base_commit_date',
            field=models.DateTimeField(),
        ),
    ]
