# Generated by Django 4.0.1 on 2022-03-30 17:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0019_alter_pipelineenv_cf_commit_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineenv',
            name='cf_commit_count',
            field=models.PositiveIntegerField(blank=True),
        ),
    ]
