# Generated by Django 4.0.1 on 2022-03-30 14:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0007_alter_pipelineapp_scm_repo_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_author',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_committer',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_count',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='pipelineapp',
            name='scm_repo_primary_branch_head_commit_date',
            field=models.DateTimeField(),
        ),
    ]
