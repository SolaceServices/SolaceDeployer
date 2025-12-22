import logging

from deployer.errors import EventPortalException
from deployer.event_portal import EventPortal
from deployer.utils import preview_exists, get_preview, store_preview
from deployer.enums import Action

def config_push(parameters):
    logging.debug(f"Running config_push with parameters { parameters }")
    ep = parameters["eventPortal"]
    if not isinstance(ep, EventPortal):
        raise TypeError("Expect an EventPortal instance")
    action = parameters.get("action") if parameters.get("action") else Action.DEPLOY.value
    target = parameters["target"]
    environment_name = target.get("environment")
    preview = parameters["preview"]
    if target.get("broker_ids") is None:
        logging.error(f"No brokers found for target-environment {target.get("environmentName")}")
        return None
    apps = [item.strip() for item in target.get("appl").split(",")] if target.get("appl") else None
    config = parameters.get("target")
    logging.debug(f"Action={action}, apps = {apps}, config={target}")
    # Gets the application to perform the action on, defaults to all applications of all domains in the json config file
    for domain in target.get("domains"):
        domain_name = domain.get("domainName")
        applications = domain.get("applications")
        for application in [app for app in applications if app["versionId"]]:
            application_name = application["name"]
            version_name = application["version"]
            state = application["state"]
            if application.get("versionId"):
                version_id = application["versionId"]
                for broker_id in target["broker_ids"]:
                    logging.info(f"{ action.capitalize() } for application { application_name } with version { version_name } and id { version_id } on broker {broker_id} for application domain { domain_name }")
                    try:
                        preview_broker_id = preview.get('broker_id') if action == Action.UNDEPLOY.value else broker_id
                        preview = ep.preview_application_deployment(version_id, Action.DEPLOY.value, preview_broker_id)
                        if action in [Action.SAVE.value]:
                            store_preview(preview, environment_name, domain_name, application_name, version_name, state)
                        ep.create_application_deployment(version_id, action, broker_id )
                    except EventPortalException as ex:
                        logging.error(f"config_push::Exception::{ex}")
            else:
                logging.info(f"Application { application_name } with version { application["version"] } in domain {domain.get("domainName")} is not eligible for action { action }")
