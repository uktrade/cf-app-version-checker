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


def get_config_environments(config_yaml):
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
        log.info("Pipeline environments: {}".format(get_config_environments(pipeline_app.config)))

        # Read pipeline SCM repo default branch head commit and modification info
        pipeline_repo = g.get_repo(pipeline_app.config["scm"])
        log.info("Repo Name: {}".format(pipeline_repo.name))
        log.info("Repo ID: {}".format(pipeline_repo.id))
        log.info("Repo Private: {}".format(pipeline_repo.private))
        log.info("Repo archived: {}".format(pipeline_repo.archived))

        scm_default_branch=pipeline_repo.default_branch
        log.info("Pipeline default branch: {}".format(scm_default_branch))
        branch=pipeline_repo.get_branch(scm_default_branch)
        log.info("Default branch ({}) HEAD commit: {}".format(scm_default_branch, branch.commit.sha))
        commits=pipeline_repo.get_commits(scm_default_branch)
        log.info("Default branch commits: {}".format(commits.totalCount))
        commit=pipeline_repo.get_commit(branch.commit.sha)
        commit_date=datetime.strptime(commit.last_modified, settings.GIT_DATE_FORMAT)
        log.info("Last modified: {}".format(commit_date))
        log.info("Author: {}".format(commit.author))
        log.info("Committer: {}".format(commit.committer))
        try:
            commit_author=commit.author.login
        except AttributeError:
            log.warn("Commit author cannot be read")
            commit_author="N/A"
        except Exception as ex:
            log.warn("Exception: {0} {1!r}".format(type(ex).__name__, ex.args))
            commit_author="N/A"
        log.info("Modified by: {}".format(commit_author))

        # Process each environment
        for environment_yaml in pipeline_app.config["environments"]:
            # Read the CF path from the pipeline yaml
            pipeline_config_app=environment_yaml["app"]
            log.info("CloudFoundry Path: {}".format(pipeline_config_app))

            pipeline_config_app_type=environment_yaml["type"]
            log.info("App Type: {}".format(pipeline_config_app_type))
            if pipeline_config_app_type != "gds":
                log.warning("App type is '{}'. Only processing 'gds' type apps here.".format(pipeline_config_app_type))
                continue

            # Check CF application path has exactly 2 "/" characters - i.e. "org/spoace/app"
            if pipeline_config_app.count("/") != 2:
                log.error("Invalid app path: {}!".format(pipeline_config_app))
                continue

            # Read the org, spoace and app for this environment
            log.info("Org: {}".format(pipeline_config_app.split("/")[0]))
            app_org_guid = get_cf_org_guid(cf, pipeline_config_app.split("/")[0])
            log.info("Org Guid: {}".format(app_org_guid))

            log.info("Space: {}".format(pipeline_config_app.split("/")[1]))
            app_space_guid = get_cf_space_guid(cf, app_org_guid, pipeline_config_app.split("/")[1])
            log.info("Space Guid: {}".format(app_space_guid))

            log.info("App: {}".format(pipeline_config_app.split("/")[2]))
            app_guid = get_cf_app_guid(cf, app_org_guid, app_space_guid, pipeline_config_app.split("/")[2])
            log.info("App Guid: {}".format(app_guid))

            # App GUID validation
            try:
                log.debug(cf.v3.apps.get(app_guid))
            except:
                log.error("Cannot read app '{}' with guid '{}'!".format(pipeline_config_app.split("/")[2], app_guid))
                continue
            
            # Get app environment configuration
            cf_app_env=cf.v3.apps.get_env(application_guid=app_guid)
            try:
                cf_app_scm_branch = cf_app_env["environment_variables"]["GIT_BRANCH"]
                log.info("CF GIT_BRANCH: {}".format(cf_app_scm_branch))
                cf_app_scm_commit = cf_app_env["environment_variables"]["GIT_COMMIT"]
                log.info("CF GIT_COMMIT: {}".format(cf_app_scm_commit))
            except:
                log.error("No SCM Branch or Commit Hash in app environmant!")
                continue

            # Get commit details of CF commit and calculate drift days
            try:
                cf_commit=pipeline_repo.get_commit(cf_app_scm_commit)
                cf_commit_date=datetime.strptime(cf_commit.last_modified, settings.GIT_DATE_FORMAT)
                log.info("Last modified: {}".format(cf_commit_date))
                log.info("Modified by: {}".format(cf_commit.author.login))
                cf_commits=pipeline_repo.get_commits(cf_app_scm_commit)
                log.info("Branch commits: {}".format(cf_commits.totalCount))
                cf_compare=pipeline_repo.compare(branch.commit.sha, cf_app_scm_commit)
                log.info("Ahead by: {}".format(cf_compare.ahead_by))
                log.info("Behind by: {}".format(cf_compare.behind_by))
                log.info("Merge Base Commit: {}".format(cf_compare.merge_base_commit))
            except:
                log.error("Cannot read commit {}!".format(cf_app_scm_commit))
                continue
            drift_time=cf_commit_date-commit_date
            log.info("Drift: {} days".format(drift_time.days))

        log.info("DONE Processing pipeline file: {}".format(pipeline_file))

    exit()
