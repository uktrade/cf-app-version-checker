# Generated by Django 4.0.1 on 2022-03-30 17:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0023_alter_pipelineapp_scm_repo_archived_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
