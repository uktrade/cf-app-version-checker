from django.conf import settings

from github import Github
from cloudfoundry_client.client import CloudFoundryClient
from datetime import datetime
import yaml
from dataclasses import dataclass


def get_pipeline_configs(repo):
    yaml_file_list=[]
    for content_file in repo.get_contents(""):
        if ".yaml" in content_file.path:
            yaml_file_list.append(content_file.path)
    return yaml_file_list  


def get_cf_org_guid(cf, org_name):
    for cf_orgs in cf.v3.organizations.list(names=org_name):
        return cf_orgs['guid']


def get_cf_space_guid(cf, org_guid, space_name):
    for cf_spaces in cf.v3.spaces.list(names=space_name, organization_guids=org_guid):
        return cf_spaces['guid']


def get_cf_app_guid(cf, org_guid, space_guid, app_name):
    for cf_apps in cf.v3.apps.list(names=app_name, space_guids=space_guid, organization_guids=org_guid):
        return cf_apps['guid']


def get_app_config_yaml(repo, config_file):
    config_text = repo.get_contents(config_file).decoded_content.decode()
    config_yaml = yaml.load(config_text, Loader=yaml.FullLoader)
    for git_cleanup in settings.GIT_CLEANUP_LIST:
        config_yaml["scm"] = config_yaml["scm"].replace(git_cleanup, "")
    return config_yaml


def get_config_environment_names(config_yaml):
    environments=[]
    for environment_yaml in config_yaml["environments"]:
        environments.append(environment_yaml["environment"])
    return environments


@dataclass
class PipelineApp:
    config_filename: str
    config: str = None
def run_github(log):

    scan_start_time=datetime.now()

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
    log.info("Config Repo: {}".format(pipeline_config_repo.name))
    log.info("Default branch: {}".format(pipeline_config_repo.default_branch))
    pipeline_files=get_pipeline_configs(pipeline_config_repo)
    log.debug("Pipelines: {}".format(pipeline_files))

    # Process pipelines
    for pipeline_file in pipeline_files:

        repo_scan_start_time=datetime.now()
        log.info("START Processing pipeline file: {}".format(pipeline_file))
        log.info("Scan job started: {}".format(scan_start_time))
        log.info("Repo scan started: {}".format(repo_scan_start_time))

        pipeline_app.config = get_app_config_yaml(pipeline_config_repo, pipeline_file)
        log.info("Pipeline SCM: {}".format(pipeline_app.config["scm"]))
        if "uktrade" not in pipeline_app.config["scm"]:
            log.warning("Not a UKTRADE repo: {}".format(pipeline_app.config["scm"]))
            continue
        
        # Read pipeline environments
        log.info("Pipeline environments: {}".format(get_config_environment_names(pipeline_app.config)))

        # Read pipeline app SCM repo
        pipeline_repo = g.get_repo(pipeline_app.config["scm"])
        pipeline_app.scm_repo_name = pipeline_repo.name
        log.info("Repo Name: {}".format(pipeline_app.scm_repo_name))
        pipeline_app.scm_repo_id = pipeline_repo.id
        log.info("Repo ID: {}".format(pipeline_app.scm_repo_id))
        pipeline_app.scm_repo_private = pipeline_repo.private
        log.info("Repo Private: {}".format(pipeline_app.scm_repo_private))
        pipeline_app.scm_repo_archived = pipeline_repo.archived
        log.info("Repo archived: {}".format(pipeline_repo.archived))
        pipeline_app.scm_repo_default_branch_name = pipeline_repo.default_branch
        log.info("Repo default branch: {}".format(pipeline_app.scm_repo_default_branch_name))

        # Read pipeline app SCM repo default branch
        pipeline_repo_default_branch=pipeline_repo.get_branch(pipeline_app.scm_repo_default_branch_name)
        pipeline_app.scm_repo_default_branch_head_commit_sha = pipeline_repo_default_branch.commit.sha
        log.info("HEAD commit sha: {}".format(pipeline_app.scm_repo_default_branch_head_commit_sha))
        
        # Read pipeline app SCM repo default branch commits
        pipeline_repo_default_branch_commits=pipeline_repo.get_commits(pipeline_app.scm_repo_default_branch_name)
        pipeline_app.scm_repo_default_branch_head_commit_count = pipeline_repo_default_branch_commits.totalCount
        log.info("Default branch commit count: {}".format(pipeline_app.scm_repo_default_branch_head_commit_count))

        # Read pipeline app SCM repo default branch head commit
        pipeline_repo_default_branch_head_commit=pipeline_repo.get_commit(pipeline_app.scm_repo_default_branch_head_commit_sha)
        pipeline_app.scm_repo_default_branch_head_commit_date = datetime.strptime(pipeline_repo_default_branch_head_commit.last_modified, settings.GIT_DATE_FORMAT)
        log.info("Last modified: {}".format(pipeline_app.scm_repo_default_branch_head_commit_date))
        try:
            pipeline_app.scm_repo_default_branch_head_commit_author = pipeline_repo_default_branch_head_commit.author.login
        except AttributeError:
            log.warn("Author cannot be read")
            pipeline_app.scm_repo_default_branch_head_commit_author="N/A"
        except Exception as ex:
            log.warn("Exception: {0} {1!r}".format(type(ex).__name__, ex.args))
            pipeline_app.scm_repo_default_branch_head_commit_author="N/A"
        log.info("Author: {}".format(pipeline_app.scm_repo_default_branch_head_commit_author))
        try:
            pipeline_app.scm_repo_default_branch_head_commit_committer = pipeline_repo_default_branch_head_commit.committer.login
        except AttributeError:
            log.warn("Author cannot be read")
            pipeline_app.scm_repo_default_branch_head_commit_committer="N/A"
        except Exception as ex:
            log.warn("Exception: {0} {1!r}".format(type(ex).__name__, ex.args))
            pipeline_app.scm_repo_default_branch_head_commit_committer="N/A"
        log.info("Committer: {}".format(pipeline_app.scm_repo_default_branch_head_commit_committer))


        # Process each environment
        for environment_yaml in pipeline_app.config["environments"]:
            # Read the CF path from the pipeline yaml
            pipeline_app.cf_full_name = environment_yaml["app"]
            log.info("CloudFoundry Path: {}".format(pipeline_app.cf_full_name))

            pipeline_app.cf_app_type = environment_yaml["type"]
            log.info("App Type: {}".format(pipeline_app.cf_app_type))
            if pipeline_app.cf_app_type != "gds":
                log.warning("App type is '{}'. Only processing 'gds' type apps here.".format(pipeline_app.cf_app_type))
                continue

            # Check CF application path has exactly 2 "/" characters - i.e. "org/spoace/app"
            if pipeline_app.cf_full_name.count("/") != 2:
                log.error("Invalid app path: {}!".format(pipeline_app.cf_full_name))
                continue

            # Read the org, spoace and app for this environment
            pipeline_app.cf_org_name = pipeline_app.cf_full_name.split("/")[0]
            log.info("Org: {}".format(pipeline_app.cf_org_name))
            pipeline_app.cf_org_guid = get_cf_org_guid(cf, pipeline_app.cf_org_name)
            log.info("Org Guid: {}".format(pipeline_app.cf_org_guid))

            pipeline_app.cf_space_name = pipeline_app.cf_full_name.split("/")[1]
            log.info("Space: {}".format(pipeline_app.cf_space_name))
            pipeline_app.cf_space_guid = get_cf_space_guid(cf, pipeline_app.cf_org_guid, pipeline_app.cf_space_name)
            log.info("Space Guid: {}".format(pipeline_app.cf_space_guid))

            pipeline_app.cf_app_name = pipeline_app.cf_full_name.split("/")[2]
            log.info("App: {}".format(pipeline_app.cf_app_name))
            pipeline_app.cf_app_guid = get_cf_app_guid(cf, pipeline_app.cf_org_guid, pipeline_app.cf_space_guid, pipeline_app.cf_app_name)
            log.info("App Guid: {}".format(pipeline_app.cf_app_guid))

            # App GUID validation
            try:
                log.debug(cf.v3.apps.get(pipeline_app.cf_app_guid))
            except:
                log.error("Cannot read app '{}' with guid '{}'!".format(pipeline_app.cf_app_name, pipeline_app.cf_app_guid))
                continue
            
            # Get app environment configuration
            cf_app_env=cf.v3.apps.get_env(application_guid=pipeline_app.cf_app_guid)
            try:
                pipeline_app.cf_app_git_branch = cf_app_env["environment_variables"]["GIT_BRANCH"]
                log.info("CF GIT_BRANCH: {}".format(pipeline_app.cf_app_git_branch))
                pipeline_app.cf_app_git_commit = cf_app_env["environment_variables"]["GIT_COMMIT"]
                log.info("CF GIT_COMMIT: {}".format(pipeline_app.cf_app_git_commit))
            except:
                log.error("No SCM Branch or Commit Hash in app environmant!")
                continue

            # Get commit details of CF commit and calculate drift days
            try:
                cf_commit=pipeline_repo.get_commit(pipeline_app.cf_app_git_commit)
                pipeline_app.cf_commit_date = datetime.strptime(cf_commit.last_modified, settings.GIT_DATE_FORMAT)
                log.info("Last modified: {}".format(pipeline_app.cf_commit_date))
                pipeline_app.cf_commit_author = cf_commit.author.login
                log.info("Modified by: {}".format(pipeline_app.cf_commit_author))
                pipeline_app.cf_commit_count = pipeline_repo.get_commits(pipeline_app.cf_app_git_commit)
                log.info("Branch commits: {}".format(pipeline_app.cf_commit_count))

                cf_compare=pipeline_repo.compare(pipeline_repo_default_branch.commit.sha, pipeline_app.cf_app_git_commit)
                log.info("Ahead by: {}".format(cf_compare.ahead_by))
                log.info("Behind by: {}".format(cf_compare.behind_by))
                log.info("Merge Base Commit: {}".format(cf_compare.merge_base_commit))
                cf_compare_base_merge=pipeline_repo.get_commit(cf_compare.merge_base_commit.sha)
                cf_compare_base_merge_date=datetime.strptime(cf_compare_base_merge.last_modified, settings.GIT_DATE_FORMAT)
                log.info("Merge Base Commit Date: {}".format(cf_compare_base_merge_date))
            except:
                log.error("Cannot read commit {}!".format(pipeline_app.cf_app_git_commit))
                continue
            drift_time=pipeline_app.cf_commit_date-pipeline_app.scm_repo_default_branch_head_commit_date
            log.info("Drift: {} days".format(drift_time.days))
            drift_time_v2=cf_compare_base_merge_date-pipeline_app.scm_repo_default_branch_head_commit_date
            log.info("Drift v2: {} days".format(drift_time_v2.days))

        log.info("DONE Processing pipeline file: {}".format(pipeline_file))

    exit()
