import logging

from deployer.errors import EventPortalException
from deployer.event_portal import EventPortal
from deployer.event_portal import get_path_expr
from deployer.broker import Broker

def semp(parameters):
    logging.debug(f"Running semp with parameters { parameters }")
    ep = parameters["eventPortal"]
    if not isinstance(ep, EventPortal):
        raise TypeError("Expect an EventPortal instance")
    # get the preview from src
    broker_id = parameters.get("broker_ids")[0]
    applications = parameters.get("target").get("applications")
    action = parameters["action"]
    target = parameters["target"]
    broker_configs = target["brokers"]
    for application in [app for app in applications if app["versionId"]]:
        version_id = application["versionId"]
        logging.info(f"{action.capitalize()} application: { application["name"] } with version { application["version"] } and id { application["versionId"] }")
        try:
            preview = ep.preview_application_deployment(version_id, "deploy", broker_id)
            execute(application, action, broker_configs, preview, application["name"])
        except EventPortalException as ex:
            logging.error(f"semp_deploy::Exception::{ex}")

def execute(config, action, broker_cfgs, preview, app_name):
    logging.debug(f"Deploying { config } to brokers { broker_cfgs }")
    selector = 'requested'# if action == 'deploy' else 'existing'
    solace_client_usernames = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceClientUsername')].value")
    solace_client_certificate_usernames = get_path_expr(preview, f"$..{selector}[?( @.type=='solaceClientCertificateUsername')].value")
    client_usernames = solace_client_usernames + solace_client_certificate_usernames
    solace_authorization_groups =  get_path_expr(preview, f"$..{selector}[?(@.type=='solaceAuthorizationGroup')].value")
    solace_acl_profiles = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceAcl')].value")
    solace_queues = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceQueue')].value")
    for cfg in broker_cfgs:
        broker_name = cfg["name"]
        base_url = cfg["url"]
        msg_vpn_name = cfg["msgVpnName"]
        user = cfg["user"]
        pwd = cfg["password"]
        broker = Broker(broker_name, base_url, user, pwd, msg_vpn_name)
        if action == 'deploy':
            broker.create_acl_profile( solace_acl_profiles[0], app_name) # always just 1 profile
            if client_usernames:
                broker.create_client_username(client_usernames[0], solace_acl_profiles[0].get("aclProfile"), app_name, config.get("user"))# possible multi?
            if solace_authorization_groups:
                broker.create_authorization_group(solace_authorization_groups[0], solace_acl_profiles[0].get("aclProfile"), app_name, config.get("user"))
            broker.create_queues(solace_queues)
        else:
            broker.delete_queues(solace_queues)
            if client_usernames:
                broker.delete_client_username(client_usernames[0], config.get("user"), app_name)
            if solace_authorization_groups:
                broker.delete_authorization_group(solace_authorization_groups[0], config.get("user"), app_name)
            broker.delete_acl_profile(solace_acl_profiles[0], app_name)

