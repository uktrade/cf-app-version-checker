# Generated by Django 4.0.1 on 2022-03-30 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0021_alter_pipelineenv_cf_commit_count_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineenv',
            name='git_compare_ahead_by',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='git_compare_behind_by',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]