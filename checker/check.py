from django.conf import settings
from django.db import models

from github import Github
from cloudfoundry_client.client import CloudFoundryClient
from datetime import datetime
import yaml
import csv
import json
from .models import PipelineApp, PipelineEnv

import logging

log = logging.getLogger(__name__)


def get_pipeline_configs(repo):
    yaml_file_list = []
    for content_file in repo.get_contents(""):
        if ".yaml" in content_file.path:
            yaml_file_list.append(content_file.path)
    return yaml_file_list


def get_app_config_yaml(repo, config_file):
    config_text = repo.get_contents(config_file).decoded_content.decode()
    config_yaml = yaml.safe_load(config_text)
    for git_cleanup in settings.GIT_CLEANUP_LIST:
        config_yaml["scm"] = config_yaml["scm"].replace(git_cleanup, "")
    return config_yaml


def get_config_environment_names(config_yaml):
    environments = []
    for environment_yaml in config_yaml["environments"]:
        environments.append(environment_yaml["environment"])
    return environments


def record_json(record):
    record_dict = {}
    for field in record._meta.get_fields():
        if not isinstance(field, models.ManyToOneRel):
            record_dict[field.name] = str(getattr(record, field.name))
    return json.dumps(record_dict)


def write_record(record):
    try:
        record.save()
    except:
        log.error(f"Error saving record id {record.id}")
        return
    log.debug(record_json(record))


def run_check():
    scan_start_time = datetime.now()

    # Initialise Github object
    g = Github(settings.GITHUB_TOKEN)

    # Initialise CloudFoundry object
    cf_username = settings.CF_USERNAME
    cf_password = settings.CF_PASSWORD
    target_endpoint = settings.CF_ENDPOINT
    cf = CloudFoundryClient(target_endpoint, proxy=dict(http=settings.CF_PROXY, https=settings.CF_PROXY))
    cf.init_with_user_credentials(cf_username, cf_password)

    # Read the pipeline configs
    pipeline_config_repo = g.get_repo(settings.GIT_PIPELINE_REPO)
    log.info(f"Config Repo: {pipeline_config_repo.name}")
    pipeline_files = get_pipeline_configs(pipeline_config_repo)
    log.debug(f"Pipelines: {pipeline_files}")

    for pipeline_file in pipeline_files:
        # Process pipelines
        log.info(f"{pipeline_file} - START Processing pipeline file")
        pipeline_app = PipelineApp()
        setattr(pipeline_app, "config_filename", pipeline_file)
        setattr(pipeline_app, "scan_start_time", scan_start_time)
        setattr(pipeline_app, "repo_scan_start_time", datetime.now())

        # Read config and check for a "uktrade" repo
        setattr(pipeline_app, "config", get_app_config_yaml(pipeline_config_repo, pipeline_app.config_filename))
        if "uktrade" not in pipeline_app.config["scm"]:
            pipeline_env = PipelineEnv()
            pipeline_env.log_message = (f"Not a UKTRADE repo: {pipeline_app.config['scm']}")
            log.warning(pipeline_env.log_message)
            write_record(pipeline_app)
            continue

        # Read pipeline app SCM repo
        pipeline_repo = g.get_repo(pipeline_app.config["scm"])
        setattr(pipeline_app, "scm_repo_name", pipeline_repo.name)
        setattr(pipeline_app, "scm_repo_id", pipeline_repo.id)
        setattr(pipeline_app, "scm_repo_private", pipeline_repo.private)
        setattr(pipeline_app, "scm_repo_archived", pipeline_repo.archived)

        # Read branches and set branch to compare for code-drift calculations
        pipeline_repo_branch_list = [ branch.name for branch in pipeline_repo.get_branches() ]
        setattr(pipeline_app, "scm_repo_branch_list", pipeline_repo_branch_list)
        setattr(pipeline_app, "scm_repo_default_branch_name", pipeline_repo.default_branch)
        # Override primary branch with "master" or "main" if they exist (prefer "main")
        for branch_list in [pipeline_repo.default_branch, "master", "main"]:
            if branch_list in pipeline_app.scm_repo_branch_list:
                setattr(pipeline_app, "scm_repo_primary_branch_name", branch_list)

        # Read pipeline app SCM repo primary branch
        pipeline_repo_primary_branch = pipeline_repo.get_branch(pipeline_app.scm_repo_primary_branch_name)
        setattr(pipeline_app, "scm_repo_primary_branch_head_commit_sha", pipeline_repo_primary_branch.commit.sha)
        
        # Read pipeline app SCM repo primary branch commits
        pipeline_repo_primary_branch_commits = pipeline_repo.get_commits(pipeline_app.scm_repo_primary_branch_name)
        setattr(pipeline_app, "scm_repo_primary_branch_head_commit_count", pipeline_repo_primary_branch_commits.totalCount)

        # Read pipeline app SCM repo primary branch head commit
        pipeline_repo_primary_branch_head_commit = pipeline_repo.get_commit(pipeline_app.scm_repo_primary_branch_head_commit_sha)
        setattr(pipeline_app, "scm_repo_primary_branch_head_commit_date", datetime.strptime(pipeline_repo_primary_branch_head_commit.last_modified, settings.GIT_RESPONSE_DATE_FORMAT))
        try:
            setattr(pipeline_app, "scm_repo_primary_branch_head_commit_author", pipeline_repo_primary_branch_head_commit.author.login)
        except AttributeError:
            setattr(pipeline_app, "scm_repo_primary_branch_head_commit_author", None)
            log.warn("Author cannot be read")
        except Exception as ex:
            setattr(pipeline_app, "scm_repo_primary_branch_head_commit_author", None)
            log.error("Exception: {0} {1!r}".format(type(ex).__name__, ex.args))
        try:
            setattr(pipeline_app, "scm_repo_primary_branch_head_commit_committer", pipeline_repo_primary_branch_head_commit.committer.login)
        except AttributeError:
            setattr(pipeline_app, "scm_repo_primary_branch_head_commit_committer", None)
            log.warn("Committer cannot be read")
        except Exception as ex:
            setattr(pipeline_app, "scm_repo_primary_branch_head_commit_committer", None)
            log.error("Exception: {0} {1!r}".format(type(ex).__name__, ex.args))

        write_record(pipeline_app)

        # Process each environment
        for environment_yaml in pipeline_app.config["environments"]:
            log.info(f"{pipeline_file} - Processing environment '{environment_yaml['environment']}'")
            pipeline_env = PipelineEnv()
            setattr(pipeline_env, "config_id_fk", pipeline_app)
            setattr(pipeline_env, "config_env", environment_yaml["environment"])
            setattr(pipeline_env, "cf_app_type", environment_yaml["type"])
            if pipeline_env.cf_app_type != "gds":
                pipeline_env.log_message = f"App type is '{pipeline_env.cf_app_type}'. Only processing 'gds' type apps here."
                log.warning(pipeline_env.log_message)
                write_record(pipeline_env)
                continue

            # Read the CF path from the pipeline yaml
            setattr(pipeline_env, "cf_full_name", environment_yaml["app"])

            # Check CF application path has exactly 2 "/" characters - i.e. "org/spoace/app"
            if pipeline_env.cf_full_name.count("/") != 2:
                pipeline_env.log_message = f"Invalid app path: {pipeline_env.cf_full_name}"
                log.error(pipeline_env.log_message)
                write_record(pipeline_env)
                continue

            # Read the org, space and app for this environment
            # Read the org
            setattr(pipeline_env, "cf_org_name", pipeline_env.cf_full_name.split("/")[0])
            for cf_orgs in cf.v3.organizations.list(names=pipeline_env.cf_org_name):
                setattr(pipeline_env, "cf_org_guid", cf_orgs["guid"])
            # Read the space
            setattr(pipeline_env, "cf_space_name", pipeline_env.cf_full_name.split("/")[1])
            for cf_spaces in cf.v3.spaces.list(names=pipeline_env.cf_space_name, organization_guids=pipeline_env.cf_org_guid):
                setattr(pipeline_env, "cf_space_guid", cf_spaces["guid"])
            # Read the app
            setattr(pipeline_env, "cf_app_name", pipeline_env.cf_full_name.split("/")[2])
            for cf_apps in cf.v3.apps.list(names=pipeline_env.cf_app_name, space_guids=pipeline_env.cf_space_guid, organization_guids=pipeline_env.cf_org_guid):
                setattr(pipeline_env, "cf_app_guid", cf_apps["guid"])
            
            # App GUID validation
            if not pipeline_env.cf_app_guid:
                pipeline_env.log_message = f"Cannot read app '{pipeline_env.cf_app_name}' with guid '{pipeline_env.cf_app_guid}'"
                log.error(pipeline_env.log_message)
                write_record(pipeline_env)
                continue
            
            # Get app environment configuration
            cf_app_env = cf.v3.apps.get_env(application_guid=pipeline_env.cf_app_guid)
            try:
                setattr(pipeline_env, "cf_app_git_branch", cf_app_env["environment_variables"]["GIT_BRANCH"])
                setattr(pipeline_env, "cf_app_git_commit", cf_app_env["environment_variables"]["GIT_COMMIT"])
            except:
                pipeline_env.log_message = ("No SCM Branch or Commit Hash in app environmant")
                log.error(pipeline_env.log_message)
                write_record(pipeline_env)
                continue

            try:
                # Get commit details of CF commit sha
                cf_commit = pipeline_repo.get_commit(pipeline_env.cf_app_git_commit)
                setattr(pipeline_env, "cf_commit_date", datetime.strptime(cf_commit.last_modified, settings.GIT_RESPONSE_DATE_FORMAT))
                setattr(pipeline_env, "cf_commit_author", cf_commit.author.login)
                setattr(pipeline_env, "cf_commit_count", pipeline_repo.get_commits(pipeline_env.cf_app_git_commit).totalCount)
            except:
                pipeline_env.log_message = f"Cannot read commit {pipeline_env.cf_app_git_commit}"
                log.error(pipeline_env.log_message)
                write_record(pipeline_env)
                continue

            # Calculate "simple" drift days - between head commit date and CF commit date
            drift_time_simple = pipeline_env.cf_commit_date - pipeline_app.scm_repo_primary_branch_head_commit_date
            setattr(pipeline_env, "drift_time_simple", drift_time_simple)

            # Calculate merge-base drift days - between primary branch head commit date and date of last common ancestor (head and cf)
            cf_compare = pipeline_repo.compare(pipeline_repo_primary_branch.commit.sha, pipeline_env.cf_app_git_commit)
            setattr(pipeline_env, "git_compare_ahead_by", cf_compare.ahead_by)
            setattr(pipeline_env, "git_compare_behind_by", cf_compare.behind_by)
            setattr(pipeline_env, "git_compare_merge_base_commit", cf_compare.merge_base_commit.sha)
            merge_base_commit = pipeline_repo.get_commit(pipeline_env.git_compare_merge_base_commit)
            setattr(pipeline_env, "git_compare_merge_base_commit_date", datetime.strptime(merge_base_commit.last_modified, settings.GIT_RESPONSE_DATE_FORMAT))
            drift_time_merge_base = pipeline_env.git_compare_merge_base_commit_date - pipeline_app.scm_repo_primary_branch_head_commit_date
            setattr(pipeline_env, "drift_time_merge_base", drift_time_merge_base)

            # Write completed record
            write_record(pipeline_env)
            log.info(f"{pipeline_app.config_filename} - Done (id={pipeline_env.id})")

        log.info(f"{pipeline_app.config_filename} - DONE Processing pipeline file (id={pipeline_app.id})")

    exit()
