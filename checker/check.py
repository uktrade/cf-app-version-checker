from django.conf import settings

from github import Github
from cloudfoundry_client.client import CloudFoundryClient
from datetime import datetime
import yaml
import csv
from .models import PipelineApp, PipelineEnv


def get_pipeline_configs(repo):
    yaml_file_list=[]
    for content_file in repo.get_contents(""):
        if ".yaml" in content_file.path:
            yaml_file_list.append(content_file.path)
    return yaml_file_list  


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


def write_csv(write_mode, columns):
    f = open(settings.CSV_OUTPUT_FILENAME, write_mode)
    writer = csv.writer(f)
    writer.writerow(columns)
    f.close()

def write_headers(App, Env):
    write_csv("w",
        [ field.name for field in App._meta.get_fields() ] + 
        [ field.name for field in Env._meta.get_fields() ]
    )

def write_record(app, env, log):
    write_csv("a",
        [ getattr(app,field.name) for field in app._meta.get_fields() ] +
        [ getattr(env,field.name) for field in env._meta.get_fields() ]
    )
    app.save()
    log.info("{} - Saved app record. ID is {}.".format(app.config_filename, app.id))
    env.save()
    log.info("{} - Saved env record. ID is {}.".format(app.config_filename, env.id))


def run_check(log):
    scan_start_time=datetime.now()
    write_headers(PipelineApp, PipelineEnv)

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

    for pipeline_file in pipeline_files:
        # Process pipelines
        pipeline_app = PipelineApp()
        pipeline_app.set_log_attribute("config_filename", pipeline_file, log)
        pipeline_app.set_log_attribute("scan_start_time", scan_start_time, log)
        pipeline_app.set_log_attribute("repo_scan_start_time", datetime.now(), log)

        pipeline_app.config_filename = pipeline_file
        log.info("START Processing pipeline file: {}".format(pipeline_app.config_filename))
        pipeline_app.scan_start_time = scan_start_time
        log.info("Scan job started: {}".format(pipeline_app.scan_start_time))
        pipeline_app.repo_scan_start_time=datetime.now()
        log.info("Repo scan started: {}".format(pipeline_app.repo_scan_start_time))

        # Read config and check for a "uktrade" repo
        pipeline_app.set_log_attribute("config", get_app_config_yaml(pipeline_config_repo, pipeline_app.config_filename), log)
        log.info("{} - config['scm']: {}".format(pipeline_app.config_filename, pipeline_app.config["scm"]))
        if "uktrade" not in pipeline_app.config["scm"]:
            pipeline_env = PipelineEnv()
            pipeline_env.log_message="Not a UKTRADE repo: {}".format(pipeline_app.config["scm"])
            log.error(pipeline_env.log_message)
            write_record(pipeline_app, pipeline_env, log)
            continue

        # Read pipeline environments
        log.info("{} - config['environments']: {}".format(pipeline_app.config_filename, get_config_environment_names(pipeline_app.config)))

        # Read pipeline app SCM repo
        pipeline_repo = g.get_repo(pipeline_app.config["scm"])
        pipeline_app.set_log_attribute("scm_repo_name", pipeline_repo.name, log)
        pipeline_app.set_log_attribute("scm_repo_id", pipeline_repo.id, log)
        pipeline_app.set_log_attribute("scm_repo_private", pipeline_repo.private, log)
        pipeline_app.set_log_attribute("scm_repo_archived", pipeline_repo.archived, log)

        # Read branches and set branch to compare for code-drift calculations
        pipeline_repo_branch_list = [ branch.name for branch in pipeline_repo.get_branches() ]
        pipeline_app.set_log_attribute("scm_repo_branch_list", pipeline_repo_branch_list, log)
        pipeline_app.set_log_attribute("scm_repo_default_branch_name", pipeline_repo.default_branch, log)
        pipeline_app.set_log_attribute("scm_repo_primary_branch_name", pipeline_repo.default_branch, log)
        # Override primary branch with "master" or "main" if they exist (prefer "main")
        for branch_list in ["master", "main"]:
            if branch_list in pipeline_app.scm_repo_branch_list:
                log.info("{} - Override scm_repo_primary_branch_name with '{}'.".format(pipeline_app.config_filename, branch_list))
                pipeline_app.set_log_attribute("scm_repo_primary_branch_name", branch_list, log)
            else:
                log.info("{} - No '{}' branch exists".format(pipeline_app.config_filename, branch_list))                

        # Read pipeline app SCM repo primary branch
        pipeline_repo_primary_branch=pipeline_repo.get_branch(pipeline_app.scm_repo_primary_branch_name)
        pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_sha", pipeline_repo_primary_branch.commit.sha, log)
        
        # Read pipeline app SCM repo primary branch commits
        pipeline_repo_primary_branch_commits=pipeline_repo.get_commits(pipeline_app.scm_repo_primary_branch_name)
        pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_count", pipeline_repo_primary_branch_commits.totalCount, log)

        # Read pipeline app SCM repo primary branch head commit
        pipeline_repo_primary_branch_head_commit=pipeline_repo.get_commit(pipeline_app.scm_repo_primary_branch_head_commit_sha)
        pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_date", datetime.strptime(pipeline_repo_primary_branch_head_commit.last_modified, settings.GIT_DATE_FORMAT), log)
        try:
            pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_author", pipeline_repo_primary_branch_head_commit.author.login, log)
        except AttributeError:
            pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_author", "N/A", log, settings.LOG_LEVEL["WARNING"])
            log.warn("Author cannot be read")
        except Exception as ex:
            pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_author", "N/A", log, settings.LOG_LEVEL["ERROR"])
            log.error("Exception: {0} {1!r}".format(type(ex).__name__, ex.args))
        try:
            pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_committer", pipeline_repo_primary_branch_head_commit.committer.login, log)
        except AttributeError:
            pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_committer", "N/A", log, settings.LOG_LEVEL["WARNING"])
            log.warn("Committer cannot be read")
        except Exception as ex:
            pipeline_app.set_log_attribute("scm_repo_primary_branch_head_commit_committer", "N/A", log, settings.LOG_LEVEL["ERROR"])
            log.error("Exception: {0} {1!r}".format(type(ex).__name__, ex.args))

        pipeline_app.save()
        log.info("{} - Saved app record. ID is {}.".format(pipeline_app.config_filename, pipeline_app.id))

        # Process each environment
        for environment_yaml in pipeline_app.config["environments"]:
            pipeline_env = PipelineEnv()
            pipeline_env.set_log_attribute("config_id_fk", pipeline_app, pipeline_app.config_filename, log)
            pipeline_env.set_log_attribute("config_env", environment_yaml["environment"], pipeline_app.config_filename, log)
            pipeline_env.set_log_attribute("cf_app_type", environment_yaml["type"], pipeline_app.config_filename, log)
            if pipeline_env.cf_app_type != "gds":
                pipeline_env.log_message="App type is '{}'. Only processing 'gds' type apps here.".format(pipeline_env.cf_app_type)
                log.warning(pipeline_env.log_message)
                write_record(pipeline_app, pipeline_env, log)
                continue

            # Read the CF path from the pipeline yaml
            pipeline_env.set_log_attribute("cf_full_name", environment_yaml["app"], pipeline_app.config_filename, log)

            # Check CF application path has exactly 2 "/" characters - i.e. "org/spoace/app"
            if pipeline_env.cf_full_name.count("/") != 2:
                pipeline_env.log_message="Invalid app path: {}!".format(pipeline_env.cf_full_name)
                log.error(pipeline_env.log_message)
                write_record(pipeline_app, pipeline_env, log)
                continue

            # Read the org, space and app for this environment
            pipeline_env.set_log_attribute("cf_org_name", pipeline_env.cf_full_name.split("/")[0], pipeline_app.config_filename, log)
            for cf_orgs in cf.v3.organizations.list(names=pipeline_env.cf_org_name):
                pipeline_env.set_log_attribute("cf_org_guid", cf_orgs['guid'], pipeline_app.config_filename, log)
            pipeline_env.set_log_attribute("cf_space_name", pipeline_env.cf_full_name.split("/")[1], pipeline_app.config_filename, log)
            for cf_spaces in cf.v3.spaces.list(names=pipeline_env.cf_space_name, organization_guids=pipeline_env.cf_org_guid):
                pipeline_env.set_log_attribute("cf_space_guid", cf_spaces['guid'], pipeline_app.config_filename, log)
            pipeline_env.set_log_attribute("cf_app_name", pipeline_env.cf_full_name.split("/")[2], pipeline_app.config_filename, log)
            for cf_apps in cf.v3.apps.list(names=pipeline_env.cf_app_name, space_guids=pipeline_env.cf_space_guid, organization_guids=pipeline_env.cf_org_guid):
                pipeline_env.set_log_attribute("cf_app_guid", cf_apps['guid'], pipeline_app.config_filename, log)
            
            # App GUID validation
            if not pipeline_env.cf_app_guid:
                pipeline_env.log_message="Cannot read app '{}' with guid '{}'!".format(pipeline_env.cf_app_name, pipeline_env.cf_app_guid)
                log.error(pipeline_env.log_message)
                write_record(pipeline_app, pipeline_env, log)
                continue
            
            # Get app environment configuration
            cf_app_env=cf.v3.apps.get_env(application_guid=pipeline_env.cf_app_guid)
            try:
                pipeline_env.set_log_attribute("cf_app_git_branch", cf_app_env["environment_variables"]["GIT_BRANCH"], pipeline_app.config_filename, log)
                pipeline_env.set_log_attribute("cf_app_git_commit", cf_app_env["environment_variables"]["GIT_COMMIT"], pipeline_app.config_filename, log)
            except:
                pipeline_env.log_message="No SCM Branch or Commit Hash in app environmant"
                log.error(pipeline_env.log_message)
                write_record(pipeline_app, pipeline_env, log)
                continue

            try:
                # Get commit details of CF commit and calculate drift days
                cf_commit=pipeline_repo.get_commit(pipeline_env.cf_app_git_commit)
                pipeline_env.set_log_attribute("cf_commit_date", datetime.strptime(cf_commit.last_modified, settings.GIT_DATE_FORMAT), pipeline_app.config_filename, log)
                pipeline_env.set_log_attribute("cf_commit_author", cf_commit.author.login, pipeline_app.config_filename, log)
                pipeline_env.set_log_attribute("cf_commit_count", pipeline_repo.get_commits(pipeline_env.cf_app_git_commit).totalCount, pipeline_app.config_filename, log)
                pipeline_env.set_log_attribute("cf_commit_author", cf_commit.author.login, pipeline_app.config_filename, log)

                # Calculate "simple" drift days - between head commit date and CF commit date
                drift_time_simple = pipeline_env.cf_commit_date-pipeline_app.scm_repo_primary_branch_head_commit_date
                pipeline_env.set_log_attribute("drift_time_simple", drift_time_simple, pipeline_app.config_filename, log)

                # Calculate merge-base drift days - between primary branch head commit date and date of last common ancestor (head and cf)
                cf_compare=pipeline_repo.compare(pipeline_repo_primary_branch.commit.sha, pipeline_env.cf_app_git_commit)
                pipeline_env.set_log_attribute("git_compare_ahead_by", cf_compare.ahead_by, pipeline_app.config_filename, log)
                pipeline_env.set_log_attribute("git_compare_behind_by", cf_compare.behind_by, pipeline_app.config_filename, log)
                pipeline_env.set_log_attribute("git_compare_merge_base_commit", cf_compare.merge_base_commit.sha, pipeline_app.config_filename, log)
                merge_base_commit=pipeline_repo.get_commit(pipeline_env.git_compare_merge_base_commit)
                pipeline_env.set_log_attribute("git_compare_merge_base_commit_date", datetime.strptime(merge_base_commit.last_modified, settings.GIT_DATE_FORMAT), pipeline_app.config_filename, log)
                pipeline_env.set_log_attribute("git_compare_merge_base_commit", cf_compare.merge_base_commit.sha, pipeline_app.config_filename, log)

                drift_time_merge_base=pipeline_env.git_compare_merge_base_commit_date-pipeline_app.scm_repo_primary_branch_head_commit_date
                pipeline_env.set_log_attribute("drift_time_merge_base", drift_time_merge_base, pipeline_app.config_filename, log)
            except:
                pipeline_env.log_message="Cannot read commit {}!".format(pipeline_env.cf_app_git_commit)
                log.error(pipeline_env.log_message)
                write_record(pipeline_app, pipeline_env, log)
                continue

            log.debug(pipeline_app)
            write_record(pipeline_app, pipeline_env, log)

        log.info("{} - DONE Processing pipeline file".format(pipeline_app.config_filename))

    exit()