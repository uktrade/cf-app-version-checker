# Generated by Django 4.0.1 on 2022-03-30 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0008_alter_pipelineapp_scm_repo_primary_branch_head_commit_author_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_app_guid',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_app_name',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_app_type',
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_org_guid',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_org_name',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_space_guid',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_space_name',
            field=models.CharField(max_length=64),
        ),
    ]
