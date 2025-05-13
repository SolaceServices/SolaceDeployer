from requests.auth import HTTPBasicAuth
from requests import request
from requests import exceptions
from deployer.errors import *
from deployer.event_portal import get_path_expr
from urllib.parse import quote

import logging

class BrokerResponse:
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

class Broker:
    def __init__(self, name, url, user, password, msg_vpn_name, headers=None):
        if user is None and password is None or url is None:
            raise BrokerException(20, 'You must define the url, username and password')
        self.name = name
        self.url = url
        self.auth = HTTPBasicAuth(user, password) if user and password else None
        self.msg_vpn_name = msg_vpn_name
        self.headers = headers

    def get_client_profile_names(self):
        logging.info("Get Client Profiles")
        url = f"msgVpns/{ self.msg_vpn_name }/clientProfiles"
        response = self.api("GET", url)
        self.check_response(response, "ClientProfiles", "all")

    def acl_profile_exists(self, profile_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}"
        response = self.api("GET", url)
        return response.status_code == 200

    def create_acl_profile(self, acl_profile, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles"
        profile = acl_profile["aclProfile"]
        profile["msgVpnName"] = self.msg_vpn_name
        profile_name = profile["aclProfileName"]
        #profile["aclProfileName"] = f"app-{ app_name.lower() }_{index}" if profile["aclProfileName"].startswith("app-") else profile["aclProfileName"]
        logging.info(f"Create ACL-Profile '{profile_name}' for Application {app_name} on messageVPN '{self.msg_vpn_name}'")
        if self.acl_profile_exists(profile_name):
            logging.debug(f"Patch {url}/{profile_name} payload { profile }")
            resp = self.api("PATCH", f"{url}/{profile_name}", json=profile)
            self.check_response(resp, "ACL-profile", acl_profile)
        else:
            logging.debug(f"POST { url } payload { profile}")
            resp = self.api("POST", url, json=profile)
            self.check_response(resp, "ACL-profile", acl_profile)
        self.process_acl_client_connect_exceptions(profile_name, acl_profile["clientConnectExceptions"]) if acl_profile.get("clientConnectExceptions") else None
        self.process_acl_publish_topic_exceptions(profile_name, acl_profile["publishTopicExceptions"])
        self.process_acl_subscribe_topic_exceptions(profile_name, acl_profile["subscribeTopicExceptions"])

    def process_acl_client_connect_exceptions(self, profile_name, connect_exceptions):
        current_exceptions = self.get_acl_client_connect_exceptions(profile_name)
        for exception in connect_exceptions:
            if exception not in current_exceptions:
                self.create_acl_client_connect_exception(profile_name, exception)
            else:
                logging.info(f"ConnectException {exception} already exists in ACL-profile {profile_name}...")
            current_exceptions.remove(exception)
        for exception in current_exceptions:
            self.delete_acl_client_connect_exception(profile_name, exception)

    def get_acl_client_connect_exceptions(self, profile_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/clientConnectExceptions"
        resp = self.api("GET", url)
        return get_path_expr(resp.message, "$..clientConnectExceptionAddress") if resp.status_code == 200 else None

    def create_acl_client_connect_exception(self, profile_name, exception):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/clientConnectExceptions"
        payload = {
            "aclProfileName": profile_name,
            "msgVpnName": self.msg_vpn_name,
            "clientConnectExceptionAddress": exception
        }
        logging.info(f"Create clientConnectException '{ exception }' on ACL-Profile '{profile_name}' on messageVPN '{self.msg_vpn_name}'")
        logging.debug(f"POST { url } payload { payload }")
        resp = self.api("POST", url, json=payload)
        self.check_response(resp, "clientConnectException", exception)

    def delete_acl_client_connect_exception(self, profile_name, exception):
        delete_url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/clientConnectExceptions/{quote(exception, '')}"
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "clientConnectException", profile_name)

    def process_acl_publish_topic_exceptions(self, profile_name, topic_exceptions):
        current_exceptions = self.get_acl_publish_topic_exceptions(profile_name)
        for exception in topic_exceptions:
            if exception not in current_exceptions:
                self.create_acl_publish_topic_exception(profile_name, exception)
            else:
                logging.info(f"PublishTopicException {exception} already exists in ACL-profile {profile_name}...")
            current_exceptions.remove(exception)
        for exception in current_exceptions:
            self.delete_acl_publish_topic_exception(profile_name, exception)

    def get_acl_publish_topic_exceptions(self, profile_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/publishTopicExceptions"
        resp = self.api("GET", url)
        return get_path_expr(resp.message, "$..publishTopicException") if resp.status_code == 200 else None

    def create_acl_publish_topic_exception(self, profile_name, exception):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/publishTopicExceptions"
        payload = {
            "aclProfileName": profile_name,
            "msgVpnName": self.msg_vpn_name,
            "publishTopicException": exception,
            "publishTopicExceptionSyntax": "smf"
        }
        logging.info(f"Create publishTopicException '{ exception }' on ACL-Profile '{profile_name}' on messageVPN '{self.msg_vpn_name}'")
        logging.debug(f"POST { url } payload { payload }")
        resp = self.api("POST", url, json=payload)
        self.check_response(resp, "publishTopicExceptions", exception)

    def delete_acl_publish_topic_exception(self, profile_name, exception):
        delete_url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/publishTopicExceptions/smf,{quote(exception,'')}"
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "publishTopicException", exception)

    def process_acl_subscribe_topic_exceptions(self, profile_name, topic_exceptions):
        current_exceptions = self.get_acl_subscribe_topic_exceptions(profile_name)
        for exception in topic_exceptions:
            if exception not in current_exceptions:
                self.create_acl_subscribe_topic_exception(profile_name, exception)
            else:
                logging.info(f"SubscribeTopicException {exception} already exists in ACL-profile {profile_name}...")
            current_exceptions.remove(exception)
        for exception in current_exceptions:
            self.delete_acl_subscribe_topic_exception(profile_name, exception)

    def get_acl_subscribe_topic_exceptions(self, profile_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/subscribeTopicExceptions"
        resp = self.api("GET", url)
        return get_path_expr(resp.message, "$..subscribeTopicException") if resp.status_code == 200 else []

    def create_acl_subscribe_topic_exception(self, profile_name, exception):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/subscribeTopicExceptions"
        payload = {
            "aclProfileName": profile_name,
            "msgVpnName": self.msg_vpn_name,
            "subscribeTopicException": exception,
            "subscribeTopicExceptionSyntax": "smf"
        }
        logging.info(f"Create subscribeTopicException '{ exception }' on ACL-Profile '{profile_name}' on messageVPN '{self.msg_vpn_name}'")
        logging.debug(f"POST { url } payload { payload }")
        resp = self.api("POST", url, json=payload)
        self.check_response(resp, "subscribeTopicExceptions", exception)

    def delete_acl_subscribe_topic_exception(self, profile_name, exception):
        delete_url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}/subscribeTopicExceptions/smf,{quote(exception,'')}"
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "subscribeTopicException", profile_name)

    def delete_acl_profile(self, acl_profile, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles"
        profile = acl_profile["aclProfile"]
        #acl_profile_name = f"app-{ app_name.lower() }_{index}" if profile["aclProfileName"].startswith("app-") else profile["aclProfileName"]
        acl_profile_name = profile["aclProfileName"]
        logging.info(f"Delete ACL Profile {acl_profile_name} for {app_name}")
        delete_url = f"{url}/{acl_profile_name}"
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "aclProfile", acl_profile)

    def client_username_exists(self, user_name):
        url = f"msgVpns/{ self.msg_vpn_name }/clientUsernames/{user_name}"
        response = self.api("GET", url)
        return response.status_code == 200

    def create_client_username(self, client_username, acl_profile, app_name, user):
        logging.info(f"Create Client Username {user.get("name")} for Application {app_name}")
        url = f"msgVpns/{ self.msg_vpn_name }/clientUsernames"
        user_name =  user.get("name")
        client_username["msgVpnName"] = self.msg_vpn_name
        client_username["aclProfileName"] = acl_profile["aclProfileName"]
        client_username["clientUsername"] =  user_name
        if user.get("type") == "solaceClientUsername":
            client_username["password"] = user.get("password")
        logging.info(f"Create clientUsername {user_name} on messageVPN {self.msg_vpn_name}")
        if self.client_username_exists(user_name):
            logging.debug(f"PATCH { url } payload { client_username }")
            resp = self.api("PATCH", f"{url}/{user_name}", json=client_username)
            self.check_response(resp, "clientUsername", user_name)
        else:
            logging.debug(f"POST { url } payload { client_username }")
            resp = self.api("POST", url, json=client_username)
            self.check_response(resp, "clientUsername", user_name)

    def delete_client_username(self, client_username, user, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/clientUsernames"
        client_name = user["name"]
        delete_url = f"{url}/{client_name}"
        logging.info(f"Delete client name { client_name } for Application {app_name}")
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "clientUsername", client_username)

    def authorization_group_exists(self, group_name):
        url = f"msgVpns/{ self.msg_vpn_name }/authorizationGroups/{group_name}"
        response = self.api("GET", url)
        return response.status_code == 200

    def create_authorization_group(self, authorization_group, acl_profile, app_name, group):
        logging.info(f"Create Authentication Group {group.get("name")} for Application {app_name}")
        url = f"msgVpns/{ self.msg_vpn_name }/authorizationGroups"
        group_name = group.get("name")
        authorization_group["msgVpnName"] = self.msg_vpn_name
        authorization_group["aclProfileName"] = acl_profile["aclProfileName"]
        authorization_group["authorizationGroupName"] = group_name
        logging.info(f"Create authorizationGroup  {group_name} on messageVPN {self.msg_vpn_name}")
        if self.authorization_group_exists(group_name):
            logging.debug(f"PATCH { url } payload { authorization_group }")
            resp = self.api("PATCH", f"{url}/{group_name}", json=authorization_group)
            self.check_response(resp, "authorizationGroup", group_name)
        else:
            logging.debug(f"POST { url } payload { authorization_group }")
            resp = self.api("POST", url, json=authorization_group)
            self.check_response(resp, "authorizationGroup", group_name)

    def delete_authorization_group(self, authorization_group, group, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/authorizationGroups"
        authorization_group_name = group.get("name")
        delete_url = f"{url}/{authorization_group_name}"
        logging.info(f"Delete Authorization Group {authorization_group_name} for Application {app_name}")
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "authorizationGroup", authorization_group_name)

    def queue_exists(self, queue_name):
        url = f"msgVpns/{ self.msg_vpn_name }/queues/{queue_name}"
        response = self.api("GET", url)
        return response.status_code == 200

    def create_queues(self, solace_queues, owner):
        logging.info(f"Create Queues")
        for queue in solace_queues:
            self.create_queue(queue, owner)

    def create_queue(self, queue, owner):
        url = f"msgVpns/{ self.msg_vpn_name }/queues"
        configuration = queue["queueConfiguration"]
        configuration["msgVpnName"] = self.msg_vpn_name
        queue_name = configuration["queueName"]
        configuration["owner"] = owner["name"]
        logging.info(f"Create queue '{queue_name}' on messageVPN '{self.msg_vpn_name}'")
        if self.queue_exists(queue_name):
            logging.debug(f"Patch {url}/{queue_name} payload { configuration }")
            resp = self.api("PATCH", f"{url}/{queue_name}", json=configuration)
            self.check_response(resp, "queue", queue_name)
        else:
            logging.debug(f"POST { url } payload { configuration }")
            resp = self.api("POST", url, json=configuration)
            self.check_response(resp, "queue", queue_name)
        self.process_queue_subscription_topics(queue_name, queue["subscriptions"])

    def delete_queues(self, solace_queues):
        logging.info(f"Delete Queues")
        for queue in solace_queues:
            self.delete_queue(queue)

    def delete_queue(self, queue):
        url = f"msgVpns/{ self.msg_vpn_name }/queues"
        configuration = queue["queueConfiguration"]
        queue_name = configuration["queueName"]
        logging.info(f"Delete Queue {queue_name}")
        delete_url = f"{url}/{queue_name}"
        logging.info(f"Delete queue { queue_name }")
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "queue", queue_name)

    def process_queue_subscription_topics(self, queue_name, subscriptions):
        current_subscriptions = self.get_queue_subscription_topics(queue_name)
        for subscription in subscriptions:
            if subscription not in current_subscriptions:
                self.create_queue_subscription_topic(queue_name, subscription)
            else:
                logging.info(f"Subscription {subscription} already exists...")
            current_subscriptions.remove(subscription)
        for subscription in current_subscriptions:
            self.delete_queue_subscription_topic(queue_name, subscription)

    def get_queue_subscription_topics(self, queue_name):
        url = f"msgVpns/{ self.msg_vpn_name }/queues/{queue_name}/subscriptions"
        resp = self.api("GET", url)
        return get_path_expr(resp.message, "$..subscriptionTopic") if resp.status_code == 200 else None

    def create_queue_subscription_topic(self, queue_name, topic):
        url = f"msgVpns/{ self.msg_vpn_name }/queues/{queue_name}/subscriptions"
        payload = {
            "queueName": queue_name,
            "msgVpnName": self.msg_vpn_name,
            "subscriptionTopic": topic
        }
        logging.info(f"Create subscriptionTopic '{ topic }' on Queue '{queue_name}' on messageVPN '{self.msg_vpn_name}'")
        logging.debug(f"POST { url } payload { payload }")
        resp = self.api("POST", url, json=payload)
        self.check_response(resp, "subscriptionTopic", topic)

    def delete_queue_subscription_topic(self, queue_name, topic):
        delete_url = f"msgVpns/{ self.msg_vpn_name }/queues/{queue_name}/subscriptions/{quote(topic, '')}"
        resp = self.api("DELETE", delete_url)
        self.check_response(resp, "subscription", topic)

    def api(self, method, endpoint, **kwargs):
        try:
            if method is None or endpoint is None:
                raise Exception('You must pass a method and endpoint')
            url = f"{ self.url }/{endpoint}"
            response = request(method, url, auth=self.auth, headers=self.headers, **kwargs)
            response.raise_for_status()
            return BrokerResponse(response.status_code, response.json())
        except exceptions.HTTPError as exc:
            code = exc.response.status_code
            message = exc.response.json()
            if code == 400:
                return BrokerResponse(code, message)
            if code == 422:
                logging.error(f"BROKER::HTTP { method } Request to endpoint { endpoint } failed with status_code { code }: message: { message }")
                raise UnprocessableEntity(exc.request, exc.response)
            raise BrokerException(21, "BROKER::HTTPError", f"code:{code}, message:{ message }")
        except Exception as exc:
            logging.error(f"BROKER::HTTP { method } Request to endpoint { endpoint } failed with exception { exc}")
            raise BrokerException( 22, "BROKER::Exception", f"HTTP { method } Request to endpoint { endpoint } failed")

    def check_response(self, response: BrokerResponse, object_type, name=None):
        method_mapping = {
            "GET": "Request",
            "POST": "Creation",
            "PATCH": "Modification",
            "DELETE": "Deletion"
        }
        if response.status_code in [200, 201]:
            method = response.message.get("meta").get("request").get("method")
            operation = method_mapping.get(method, "Unknown")
            logging.info(f"{operation} of {object_type} {name} succeeded")
        else:
            if response.message.get("meta").get("error").get("code") == 10:
                logging.info(f"{object_type} {name} already exists")
            else:
                logging.info(f"Creation of {object_type} {name} failed! {response.message}")