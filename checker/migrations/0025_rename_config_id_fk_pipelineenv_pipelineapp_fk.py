# Generated by Django 4.0.1 on 2022-04-05 15:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0024_alter_pipelineapp_scm_repo_primary_branch_head_commit_count_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pipelineenv',
            old_name='config_id_fk',
            new_name='pipelineapp_fk',
        ),
    ]
