from django.conf import settings

from github import Github
from cloudfoundry_client.client import CloudFoundryClient
from datetime import datetime
import yaml


def get_pipeline_configs(repo):
    yaml_file_list=[]
    for content_file in repo.get_contents(""):
        if ".yaml" in content_file.path:
            yaml_file_list.append(content_file.path)
    return yaml_file_list  


def get_cf_app_environments(repo, pipeline_yaml):
    environments=[]
    pipeline_config = repo.get_contents(pipeline_yaml).decoded_content.decode()
    pipeline_config_yaml = yaml.load(pipeline_config, Loader=yaml.FullLoader)
    for i, environment_yaml in enumerate(pipeline_config_yaml["environments"]):
        environments.append(environment_yaml["environment"])
    return environments


def get_cf_org_guid(cf, org_name):
    for cf_orgs in cf.v3.organizations.list(names=org_name):
        return cf_orgs['guid']


def get_cf_space_guid(cf, org_guid, space_name):
    for cf_spaces in cf.v3.spaces.list(names=space_name, organization_guids=org_guid):
        return cf_spaces['guid']


def get_cf_app_guid(cf, org_guid, space_guid, app_name):
    for cf_apps in cf.v3.apps.list(names=app_name, space_guids=space_guid, organization_guids=org_guid):
        return cf_apps['guid']


def run_github(log):

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

        log.info("START Processing pipeline file: {}".format(pipeline_file))

        # Read pipeline SCM details
        pipeline_config_text = pipeline_config_repo.get_contents(pipeline_file).decoded_content.decode()
        pipeline_config_yaml = yaml.load(pipeline_config_text, Loader=yaml.FullLoader)
        pipeline_config_scm = pipeline_config_yaml["scm"]
        for git_cleanup in settings.GIT_CLEANUP_LIST:
            pipeline_config_scm = pipeline_config_scm.replace(git_cleanup, "")
        log.info("Pipeline SCM: {}".format(pipeline_config_scm))
        if "uktrade" not in pipeline_config_scm:
            log.warning("Not a UKTRADE repo")
            continue
        
        # Read pipeline environments
        pipeline_environments=get_cf_app_environments(pipeline_config_repo, pipeline_file)
        log.info("Pipeline environments: {}".format(pipeline_environments))

        # Read pipeline SCM repo default branch head commit and modification info
        pipeline_repo = g.get_repo(pipeline_config_scm)
        scm_default_branch=pipeline_repo.default_branch
        log.info("Pipeline default branch: {}".format(scm_default_branch))
        branch=pipeline_repo.get_branch(scm_default_branch)
        log.info("Default branch ({}) HEAD commit: {}".format(scm_default_branch, branch.commit.sha))
        commits=pipeline_repo.get_commits(scm_default_branch)
        log.info("Default branch commits: {}".format(commits.totalCount))
        commit=pipeline_repo.get_commit(branch.commit.sha)
        commit_date=datetime.strptime(commit.last_modified, settings.GIT_DATE_FORMAT)
        log.info("Last modified: {}".format(commit_date))
        try:
            commit_author=commit.author.login
        except:
            log.warn("Commit author cannot be read")
            commit_author="N/A"
        log.info("Modified by: {}".format(commit_author))

        # Process each environment
        for i, environment_yaml in enumerate(pipeline_config_yaml["environments"]):
            # Read the CF path from the pipeline yaml
            pipeline_config_app=environment_yaml["app"]
            log.info("CloudFoundry Path: {}".format(pipeline_config_app))

            # Check CF application path has exactly 2 "/" characters - i.e. "org/spoace/app"
            if pipeline_config_app.count("/") != 2:
                log.error("Invalid app path: {}!".format(pipeline_config_app))
                continue

            app_org_guid = get_cf_org_guid(cf, pipeline_config_app.split("/")[0])
            app_space_guid = get_cf_space_guid(cf, app_org_guid, pipeline_config_app.split("/")[1])
            app_guid = get_cf_app_guid(cf, app_org_guid, app_space_guid, pipeline_config_app.split("/")[2])

            # App GUID validation
            log.debug(app_guid)
            try:
                log.debug(cf.v3.apps.get(app_guid))
            except:
                log.error("Cannot read app with guid '{}'!".format(app_guid))
                continue
            
            # Get app environment configuration
            cf_app_env=cf.v3.apps.get_env(application_guid=app_guid)
            try:
                cf_app_scm_branch = cf_app_env["environment_variables"]["GIT_BRANCH"]
                log.info("SCM Branch: {}".format(cf_app_scm_branch))
                cf_app_scm_commit = cf_app_env["environment_variables"]["GIT_COMMIT"]
                log.info("SCM Commit: {}".format(cf_app_scm_commit))
            except:
                log.error("No SCM Branch or Commit Hash in app environmant!")
                continue

            # Get commit details of CF commit and calculate drift days
            cf_commit=pipeline_repo.get_commit(cf_app_scm_commit)
            cf_commit_date=datetime.strptime(cf_commit.last_modified, settings.GIT_DATE_FORMAT)
            log.info("Last modified: {}".format(cf_commit_date))
            log.info("Modified by: {}".format(cf_commit.author.login))
            drift_time=cf_commit_date-commit_date
            log.info("Drift: {} days".format(drift_time.days))

        log.info("DONE Processing pipeline file: {}".format(pipeline_file))

    exit()
