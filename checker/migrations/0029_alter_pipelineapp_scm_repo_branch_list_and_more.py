# Generated by Django 4.0.1 on 2022-04-06 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0028_alter_pipelineapp_scm_repo_branch_list'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_branch_list',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_default_branch_name',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_author',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_committer',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_sha',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_name',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]