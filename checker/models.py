from django.db import models


class PipelineApp(models.Model):
    scan_start_time = models.CharField(max_length=255)
    repo_scan_start_time = models.CharField(max_length=255)
    config_filename = models.CharField(max_length=255)
    config = models.CharField(max_length=255)
    scm_repo_name = models.CharField(max_length=255)
    scm_repo_id = models.CharField(max_length=255)
    scm_repo_private = models.CharField(max_length=255)
    scm_repo_archived = models.CharField(max_length=255)
    scm_repo_default_branch_name = models.CharField(max_length=255)
    scm_repo_default_branch_head_commit_sha = models.CharField(max_length=255)
    scm_repo_default_branch_head_commit_count = models.CharField(max_length=255)
    scm_repo_default_branch_head_commit_date = models.CharField(max_length=255)
    scm_repo_default_branch_head_commit_author = models.CharField(max_length=255)
    scm_repo_default_branch_head_commit_committer = models.CharField(max_length=255)

    def set_log_attribute(self, attribute, value, log, log_level=20):
        setattr(self, attribute, value)
        log.log(log_level,
            "{} : {}".format(attribute, getattr(self, attribute)) 
        )

class PipelineEnv(models.Model):
    config_env = models.CharField(max_length=255)
    cf_full_name = models.CharField(max_length=255)
    cf_app_type = models.CharField(max_length=255)
    cf_org_name = models.CharField(max_length=255)
    cf_org_guid = models.CharField(max_length=255)
    cf_space_name = models.CharField(max_length=255)
    cf_space_guid = models.CharField(max_length=255)
    cf_app_name = models.CharField(max_length=255)
    cf_app_guid = models.CharField(max_length=255)
    cf_app_git_branch = models.CharField(max_length=255)
    cf_app_git_commit = models.CharField(max_length=255)
    cf_commit_date = models.CharField(max_length=255)
    cf_commit_author = models.CharField(max_length=255)
    cf_commit_count = models.CharField(max_length=255)
    drift_time_simple = models.CharField(max_length=255)
    git_compare_ahead_by = models.CharField(max_length=255)
    git_compare_behind_by = models.CharField(max_length=255)
    git_compare_merge_base_commit = models.CharField(max_length=255)
    git_compare_merge_base_commit_date = models.CharField(max_length=255)
    drift_time_merge_base = models.CharField(max_length=255)
    log_message = models.CharField(max_length=255)
