import logging

from deployer.errors import EventPortalException
from deployer.event_portal import EventPortal

def config_push(parameters):
    target = parameters["target"]
    preview = parameters["preview"]
    if target.get("broker_ids") is None:
        logging.error(f"No brokers found for target-environment {target.get("environmentName")}")
        return None
    action = parameters.get("action") if parameters.get("action") else 'deploy'
    apps = [item.strip() for item in target.get("appl").split(",")] if target.get("appl") else None
    config = parameters.get("target")
    logging.debug(f"Action={action}, apps = {apps}, config={target}")
    ep = parameters["eventPortal"]
    if not isinstance(ep, EventPortal):
        raise TypeError("Expect an EventPortal instance")
    # Gets the application to perform the action on, defaults to all applications of all domains in the json config file
    for domain in target.get("domains"):
        domain_name = domain.get("domainName")
        applications = domain.get("applications")
        for application in [app for app in applications if app["versionId"]]:
            app_name = application.get("name")
            if application.get("versionId"):
                version_id = application["versionId"]
                for broker_id in target["broker_ids"]:
                    logging.info(f"{ action.capitalize() } for application { app_name } with version { application["version"] } and id { version_id } on broker {broker_id} for application domain {domain.get("domainName")}")
                    try:
                        preview_broker_id = preview.get('broker_id') if action == "undeploy" else broker_id
                        application_preview = ep.preview_application_deployment(version_id, "deploy", preview_broker_id)
                        ep.create_application_deployment(version_id, action, broker_id )
                    except EventPortalException as ex:
                        logging.error(f"config_push::Exception::{ex}")
            else:
                logging.info(f"Application { app_name } with version { application["version"] } in domain {domain.get("domainName")} is not eligible for action { action }")
