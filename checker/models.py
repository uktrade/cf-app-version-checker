from django.db import models

import logging

log = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

class PipelineApp(models.Model):
    scan_start_time = models.DateTimeField()
    repo_scan_start_time = models.DateTimeField()
    config_filename = models.CharField(max_length=64)
    config = models.CharField(max_length=255)
    scm_repo_name = models.CharField(max_length=64)
    scm_repo_id = models.CharField(max_length=16)
    scm_repo_private = models.BooleanField(null=True, blank=True)
    scm_repo_archived = models.BooleanField(null=True, blank=True)
    scm_repo_branch_list = models.CharField(max_length=255)
    scm_repo_default_branch_name = models.CharField(max_length=64)
    scm_repo_primary_branch_name = models.CharField(max_length=64)
    scm_repo_primary_branch_head_commit_sha = models.CharField(max_length=64)
    scm_repo_primary_branch_head_commit_count = models.PositiveIntegerField(null=True, blank=True)
    scm_repo_primary_branch_head_commit_date = models.DateTimeField(null=True, blank=True)
    scm_repo_primary_branch_head_commit_author = models.CharField(max_length=64)
    scm_repo_primary_branch_head_commit_committer = models.CharField(max_length=64)

    def set_attribute(self, attribute, value, log_level=20):
        setattr(self, attribute, value)
        log.log(log_level,
            f"{self.config_filename} - {attribute} : {getattr(self, attribute)}"
        )

class PipelineEnv(models.Model):
    config_id_fk = models.ForeignKey(PipelineApp, to_field='id', on_delete=models.CASCADE)
    config_env = models.CharField(max_length=64)
    cf_full_name = models.CharField(max_length=255)
    cf_app_type = models.CharField(max_length=32)
    cf_org_name = models.CharField(max_length=64)
    cf_org_guid = models.CharField(max_length=64)
    cf_space_name = models.CharField(max_length=64)
    cf_space_guid = models.CharField(max_length=64)
    cf_app_name = models.CharField(max_length=64)
    cf_app_guid = models.CharField(max_length=64)
    cf_app_git_branch = models.CharField(max_length=64)
    cf_app_git_commit = models.CharField(max_length=64)
    cf_commit_date = models.DateTimeField(null=True, blank=True)
    cf_commit_author = models.CharField(max_length=64)
    cf_commit_count = models.PositiveIntegerField(null=True, blank=True)
    drift_time_simple = models.DurationField(null=True, blank=True)
    git_compare_ahead_by = models.PositiveIntegerField(null=True, blank=True)
    git_compare_behind_by = models.PositiveIntegerField(null=True, blank=True)
    git_compare_merge_base_commit = models.CharField(max_length=64)
    git_compare_merge_base_commit_date = models.DateTimeField(null=True, blank=True)
    drift_time_merge_base = models.DurationField(null=True, blank=True)
    log_message = models.CharField(max_length=255)

    def set_attribute(self, attribute, value, config_filename, log_level=20):
        setattr(self, attribute, value)
        log.log(log_level,
            f"{config_filename} - {self.config_env} - {attribute} : {getattr(self, attribute)}"
        )
