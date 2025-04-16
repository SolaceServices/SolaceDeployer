from deployer.utils import parse_arguments, setup_logging, show_help, logging, ConfigLoader
from deployer.config_push import config_push
from deployer.semp import semp
from deployer.event_portal import EventPortal
from enum import Enum

class Environment(Enum):
    DEV = 'dev'
    TST = 'tst'
    ACC = 'acc'
    PRD = 'prd'

class Action(Enum):
    DEPLOY = 'deploy'
    UNDEPLOY = 'undeploy'

class Mode(Enum):
    CONFIG_PUSH = 'configPush'
    SEMP = 'semp'

def run():
    arguments = parse_arguments()
    setup_logging(arguments.log)
    if arguments.mode is None or arguments.mode not in [Mode.CONFIG_PUSH.value, Mode.SEMP.value]:
        show_help()
        exit (1)
    if arguments.target is None:
        show_help()
        exit (1)
    if arguments.mode == Mode.CONFIG_PUSH.value and arguments.target == Environment.DEV.value:
        logging.info("This mode can not be used on the Dev environment. Use config push via the Event Portal!")
        exit(1)
    try:
        parameters = get_parameters(arguments)
        logging.info(f"Running deployer in mode {arguments.mode} with action {parameters["action"]} on environment {parameters.get("target").get("environmentName")}")
        logging.debug(f"Parameters := { parameters }")
        if arguments.mode == Mode.CONFIG_PUSH.value:
            config_push(parameters)
        else:
            semp(parameters)
    except Exception as ex:
        logging.error(f"run:Exception occurred! {ex}")

# In mode 'configPush' src and target conf are the same.
# In mode 'semp' use src config to get the deployment preview and use the target config to execute the deployment preview via semp
def get_parameters(arguments):
    mode = arguments.mode
    action = arguments.action if arguments.action else Action.DEPLOY.value
    apps = [item.strip() for item in arguments.appl.split(",")] if arguments.appl else None
    config_loader = ConfigLoader()

    preview_config = config_loader.load_config(Environment.DEV.value)
    target_config = config_loader.load_config(arguments.target)
    ep_config = config_loader.load_config("eventPortal")
    base_url = ep_config.get("baseUrl")
    token = ep_config.get("token")
    ep = EventPortal(base_url, token)

    preview_env_id = ep.get_environment_id(preview_config["environmentName"])
    preview_mesh_id = ep.get_modeled_event_mesh_id(preview_env_id, preview_config["meshName"])
    preview_broker_id = ep.get_messaging_services_ids(preview_mesh_id)[0]
    preview_config["mesh_id"] = preview_mesh_id
    preview_config["broker_id"] = preview_broker_id

    target_env_id = ep.get_environment_id(target_config["environmentName"])
    target_mem_id = ep.get_modeled_event_mesh_id(target_env_id, target_config["meshName"])
    target_broker_ids = ep.get_messaging_services_ids(target_mem_id) if target_mem_id else None
    target_config["mesh_id"] = target_mem_id
    target_config["broker_ids"] = target_broker_ids

    environment_name = target_config["environmentName"] if mode == Mode.CONFIG_PUSH.value else preview_config["environmentName"]
    environment_id = ep.get_environment_id(environment_name)
    logging.debug(f"Environment { environment_name }  with environmentId: { environment_id }")

    mem_name = target_config["meshName"] if mode == Mode.CONFIG_PUSH.value else preview_config["meshName"]
    mesh_id = ep.get_modeled_event_mesh_id(environment_id, mem_name)
    logging.debug(f"Mesh { mem_name } with meshId: { mesh_id }")

    broker_ids = ep.get_messaging_services_ids(mesh_id)
    logging.debug(f"brokerIds: { broker_ids }")

    domain_id = ep.get_application_domain_id(target_config["domainName"])
    target_config["domainId"] = domain_id
    logging.debug(f"applicationDomain: { domain_id }")
    # Gets the application(s) to perform the action on, defaults to all applications in the json config file
    target_config["applications"] = [app for app in target_config["applications"] if app["name"] in apps] if apps else target_config["applications"]

    target_config = add_eligible_version_ids(ep, domain_id, target_config["environment"], action, mode, target_config)
    return {
        "base_url": base_url,
        "eventPortal": ep,
        "action": action,
        "dev": preview_config,
        "config": target_config,
        "preview": preview_config,
        "target": target_config,
        "environment_id": environment_id,
        "mesh_id": mesh_id,
        "broker_ids": broker_ids
    }

def add_eligible_version_ids(ep, domain_id, env, action, mode, parameters):
    if not isinstance(ep, EventPortal):
        raise TypeError("Expect an EventPortal instance")

    for application in parameters.get("applications",[]):
        app_name = application["name"]
        version_name = application["version"]
        logging.debug(f"Get eligible versions for application { app_name }")
        application_id = ep.get_application_id_by_name(domain_id, app_name)
        application["applicationId"] = application_id
        application_version = ep.get_application_version_object_by_name(application_id, version_name)
        logging.debug(f"applicationVersion= { application_version }")
        if application_version is None:
            raise Exception({"code": "NOT_EXIST", "message": f"App { app_name } version { version_name } does not exist in environment { env }"})
        if is_version_eligible(env, app_name, action, mode, application_version):
            application["versionId"]=application_version["id"]
        else:
            logging.info(f"App { app_name } version {application_version.get('version')} not eligible for env { env }")
    return parameters

def is_version_eligible(env, app_name, action, mode, version):
    logging.debug(f"Check if application { app_name } version { version.get("version") } with state { version.get("stateId") } is eligible for the given mode { mode } and action { action } in environment { env }")
    # if env in [dev, tst] and version.state in [1, 2] and action == 'deploy' => True
    # if env in [dev, tst] and action == 'undeploy' => True
    # if env in [acc, prd] and version.state == 2 and action == 'deploy' => True
    # if env in [acc, prd] and version.state in [2, 3, 4] and action == 'undeploy' => True
    # else False
    if ((env in [Environment.DEV.value, Environment.TST.value] and version.get('stateId') in ['1','2'] and action == Action.DEPLOY.value) or
            (env in [Environment.DEV.value, Environment.TST.value] and action == Action.UNDEPLOY.value)):
        return True
    if ((env in [Environment.ACC.value, Environment.PRD.value] and version.get('stateId') == '2' and action == Action.DEPLOY.value) or
            (env in [Environment.ACC.value, Environment.PRD.value] and version.get('stateId') in ['2','3','4'] and action == Action.UNDEPLOY.value)):
        return True
    return False

