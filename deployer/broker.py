from requests.auth import HTTPBasicAuth
from requests import request
from requests import exceptions
from deployer.errors import *

import logging

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
        logging.info(f"RESPONSE={response}")

    def acl_profile_exists(self, profile_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profile_name}"
        response = self.api("GET", url)
        meta = response["meta"]
        return meta["responseCode"] == 200

    def create_acl_profile(self, acl_profile, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles"
        profile = acl_profile["aclProfile"]
        profile["msgVpnName"] = self.msg_vpn_name
        profile_name = profile["aclProfileName"]
        #profile["aclProfileName"] = f"app-{ app_name.lower() }_{index}" if profile["aclProfileName"].startswith("app-") else profile["aclProfileName"]
        logging.info(f"Create ACL-Profile '{profile_name}' for Application {app_name} on messageVPN '{self.msg_vpn_name}'")
        if self.acl_profile_exists(profile_name):
            logging.debug(f"Patch {url}/{profile_name} payload { profile }")
            self.api("PATCH", f"{url}/{profile_name}", json=profile)
        else:
            logging.debug(f"POST { url } payload { profile}")
            self.api("POST", url, json=profile)
        publish_topic_exceptions = acl_profile["publishTopicExceptions"]
        for exception in publish_topic_exceptions:
            self.create_acl_publish_exception(profile["aclProfileName"], exception)
        subscribe_topic_exceptions = acl_profile["subscribeTopicExceptions"]
        for exception in subscribe_topic_exceptions:
            self.create_acl_subscribe_exception(profile["aclProfileName"], exception)

    def create_acl_publish_exception(self, profileName, exception):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profileName}/publishTopicExceptions"
        payload = {
            "aclProfileName": profileName,
            "msgVpnName": self.msg_vpn_name,
            "publishTopicException": exception,
            "publishTopicExceptionSyntax": "smf"
        }
        logging.info(f"Create publishTopicException '{ exception }' on ACL-Profile '{profileName}' on messageVPN '{self.msg_vpn_name}'")
        logging.debug(f"POST { url } payload { payload }")
        self.api("POST", url, json=payload)

    def create_acl_subscribe_exception(self, profileName, exception):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles/{profileName}/subscribeTopicExceptions"
        payload = {
            "aclProfileName": profileName,
            "msgVpnName": self.msg_vpn_name,
            "subscribeTopicException": exception,
            "subscribeTopicExceptionSyntax": "smf"
        }
        logging.info(f"Create subscribeTopicException '{ exception }' on ACL-Profile '{profileName}' on messageVPN '{self.msg_vpn_name}'")
        logging.debug(f"POST { url } payload { payload }")
        self.api("POST", url, json=payload)

    def delete_acl_profile(self, acl_profile, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles"
        profile = acl_profile["aclProfile"]
        #acl_profile_name = f"app-{ app_name.lower() }_{index}" if profile["aclProfileName"].startswith("app-") else profile["aclProfileName"]
        acl_profile_name = profile["aclProfileName"]
        logging.info(f"Delete ACL Profile {acl_profile_name} for {app_name}")
        delete_url = f"{url}/{acl_profile_name}"
        self.api("DELETE", delete_url)

    def client_username_exists(self, user_name):
        url = f"msgVpns/{ self.msg_vpn_name }/clientUsernames/{user_name}"
        response = self.api("GET", url)
        meta = response["meta"]
        return meta["responseCode"] == 200

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
            self.api("PATCH", f"{url}/{user_name}", json=client_username)
        else:
            logging.debug(f"POST { url } payload { client_username }")
            self.api("POST", url, json=client_username)

    def delete_client_username(self, client_username, user, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/clientUsernames"
        client_name = user["name"]
        delete_url = f"{url}/{client_name}"
        logging.info(f"Delete client name { client_name } for Application {app_name}")
        self.api("DELETE", delete_url)

    def authorization_group_exists(self, group_name):
        url = f"msgVpns/{ self.msg_vpn_name }/authorizationGroups/{group_name}"
        response = self.api("GET", url)
        meta = response["meta"]
        return meta["responseCode"] == 200

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
            self.api("PATCH", f"{url}/{group_name}", json=authorization_group)
        else:
            logging.debug(f"POST { url } payload { authorization_group }")
            self.api("POST", url, json=authorization_group)

    def delete_authorization_group(self, authorization_group, group, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/authorizationGroups"
        authorization_group_name = group.get("name")
        delete_url = f"{url}/{authorization_group_name}"
        logging.info(f"Delete Authorization Group {authorization_group_name} for Application {app_name}")
        self.api("DELETE", delete_url)

    def queue_exists(self, queue_name):
        url = f"msgVpns/{ self.msg_vpn_name }/queues/{queue_name}"
        response = self.api("GET", url)
        meta = response["meta"]
        return meta["responseCode"] == 200

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
            self.api("PATCH", f"{url}/{queue_name}", json=configuration)
        else:
            logging.debug(f"POST { url } payload { configuration }")
            self.api("POST", url, json=configuration)
        for subscription in queue["subscriptions"]:
            subs_url = f"{url}/{queue_name}/subscriptions"
            payload = {
                "msgVpnName": self.msg_vpn_name,
                "queueName": queue_name,
                "subscriptionTopic": subscription
            }
            logging.info(f"Create subscriptionTopic '{subscription}' queue '{queue_name}' on messageVPN '{self.msg_vpn_name}'")
            logging.debug(f"POST { subs_url } payload { payload }")
            self.api("POST", subs_url, json=payload)

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
        self.api("DELETE", delete_url)

    def api(self, method, endpoint, **kwargs):
        try:
            if method is None or endpoint is None:
                raise Exception('You must pass a method and endpoint')
            url = f"{ self.url }/{endpoint}"
            response = request(method, url, auth=self.auth, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except exceptions.HTTPError as exc:
            code = exc.response.status_code
            message = exc.response.json()
            error = message.get("meta").get("error")
            if code == 400 and error.get("status") in ['ALREADY_EXISTS','NOT_FOUND']:
                return message
            if code == 422:
                logging.error(f"BROKER::HTTP { method } Request to endpoint { endpoint } failed with status_code { code }: message: { message }")
                raise UnprocessableEntity(exc.request, exc.response)
            raise BrokerException(21, "BROKER::HTTPError", f"code:{code}, message:{ message }")

        except Exception as exc:
            logging.error(f"BROKER::HTTP { method } Request to endpoint { endpoint } failed with exception { exc}")
            raise BrokerException( 22, "BROKER::Exception", f"HTTP { method } Request to endpoint { endpoint } failed")