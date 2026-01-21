import logging

from deployer.errors import EventPortalException
from deployer.event_portal import EventPortal
from deployer.event_portal import get_path_expr
from deployer.broker import Broker
from deployer.utils import store_preview
from deployer.enums import Action

def semp(parameters):
    logging.debug(f"Running semp with parameters { parameters }")
    ep = parameters["eventPortal"]
    if not isinstance(ep, EventPortal):
        raise TypeError("Expect an EventPortal instance")
    # get the preview from src
    broker_id = parameters.get("broker_ids")[0]
    action = parameters["action"]
    target = parameters["target"]
    environment_name = target.get("environment")
    broker_configs = target["brokers"]
    for domain in parameters.get("target").get("domains"):
        domain_name = domain["domainName"]
        applications = domain["applications"]
        for application in [app for app in applications if app["versionId"]]:
            application_name = application["name"]
            version_name = application["version"]
            version_id = application["versionId"]
            state = application["state"]
            logging.info(f"{action.capitalize()} application: [{ application_name }] with version [{ version_name }], id [{ version_id }] and state [{ state }] in domain [{domain_name}]")
            try:
                preview = ep.preview_application_deployment(version_id, Action.DEPLOY.value, broker_id)
                if action in [Action.SAVE.value]:
                    store_preview(preview, environment_name, domain_name, application_name, version_name, state)
                if action in [Action.DEPLOY.value, Action.UNDEPLOY.value]:
                    execute(application, action, broker_configs, preview, application_name)
            except EventPortalException as ex:
                logging.error(f"semp_deploy::EventPortalException::{ex}")
            except Exception as ex:
                logging.error(f"semp_deploy::Exception::{ex}")

def execute(config, action, broker_cfgs, preview, app_name):
    logging.debug(f"Deploying { config } to brokers { broker_cfgs }")
    selector = 'requested'# if action == 'deploy' else 'existing'
    solace_client_usernames = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceClientUsername')].value")
    solace_client_certificate_usernames = get_path_expr(preview, f"$..{selector}[?( @.type=='solaceClientCertificateUsername')].value")
    solace_authorization_groups =  get_path_expr(preview, f"$..{selector}[?(@.type=='solaceAuthorizationGroup')].value")
    solace_acl_profiles = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceAcl')].value")
    solace_queues = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceQueue')].value")
    solace_rdps = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceRestDeliveryPoint')].value")
    solace_rdp_queue_bindings = get_path_expr(preview, f"$..{selector}[?(@.type=='solaceRestDeliveryPointQueueBinding')].value")
    for cfg in broker_cfgs:
        broker_name = cfg["name"]
        base_url = cfg["url"]
        msg_vpn_name = cfg["msgVpnName"]
        user = cfg["user"]
        pwd = cfg["password"]
        broker = Broker(broker_name, base_url, user, pwd, msg_vpn_name)
        if action == Action.DEPLOY.value:
            if solace_acl_profiles:
                broker.create_acl_profile( solace_acl_profiles[0], app_name) # always just 1 profile
            if solace_client_usernames:
                broker.create_client_username(solace_client_usernames[0], solace_acl_profiles[0].get("aclProfile"), app_name, config.get("user"))# possible multi?
            if solace_client_certificate_usernames:
                broker.create_client_username(solace_client_certificate_usernames[0], solace_acl_profiles[0].get("aclProfile"), app_name, config.get("user"))# possible multi?
            if solace_authorization_groups:
                broker.create_authorization_group(solace_authorization_groups[0], solace_acl_profiles[0].get("aclProfile"), app_name, config.get("user"))
            if solace_queues:
                broker.create_queues(solace_queues, config.get("user"))
            if solace_rdps:
                broker.create_rdps(solace_rdps)
            if solace_rdp_queue_bindings:
                broker.create_rdp_queue_bindings(solace_rdp_queue_bindings)
        else:
            if solace_rdp_queue_bindings:
                broker.delete_rdp_queue_bindings(solace_rdp_queue_bindings)
            if solace_rdps:
                broker.delete_rdps(solace_rdps)
            if solace_queues:
                broker.delete_queues(solace_queues)
            if solace_client_usernames:
                broker.delete_client_username(solace_client_usernames[0], app_name, config.get("user"))
            if solace_client_certificate_usernames:
                broker.delete_client_username(solace_client_certificate_usernames[0], app_name, config.get("user"))
            if solace_authorization_groups:
                broker.delete_authorization_group(solace_authorization_groups[0], app_name)
            if solace_acl_profiles:
                broker.delete_acl_profile(solace_acl_profiles[0], app_name)

