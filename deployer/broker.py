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

    # There is usually only 1 aclProfile when executing a deployment
    def create_acl_profiles(self, solace_acl_profiles, app_name):
        logging.info(f"Create ACL Profiles for {app_name}")
        profile_name = []
        for index, acl_profile in enumerate(solace_acl_profiles):
            profile_name.append(self.create_acl_profile(index, acl_profile, app_name))
        return profile_name[0]

    def create_acl_profile(self, index, acl_profile, app_name):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles"
        profile = acl_profile["aclProfile"]
        profile["msgVpnName"] = self.msg_vpn_name
        #profile["aclProfileName"] = f"app-{ app_name.lower() }_{index}" if profile["aclProfileName"].startswith("app-") else profile["aclProfileName"]
        logging.debug(f"POST { url } payload { profile}")
        logging.info(f"Create ACL-Profile '{profile["aclProfileName"]}' on messageVPN '{self.msg_vpn_name}'")
        self.api("POST", url, json=profile)
        publish_topic_exceptions = acl_profile["publishTopicExceptions"]
        for exception in publish_topic_exceptions:
            self.create_acl_publish_exception(profile["aclProfileName"], exception)
        subscribe_topic_exceptions = acl_profile["subscribeTopicExceptions"]
        for exception in subscribe_topic_exceptions:
            self.create_acl_subscribe_exception(profile["aclProfileName"], exception)
        return profile["aclProfileName"]

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

    def create_client_usernames(self, solace_client_usernames, acl_profile_name, config):
        logging.info(f"Create Client Usernames")
        for user in config.get("users"):
            self.create_client_username(user, acl_profile_name)

    def create_client_username(self, user, acl_profile_name):
        logging.info(f"Create Client Username")
        url = f"msgVpns/{ self.msg_vpn_name }/clientUsernames"
        payload = {
            "msgVpnName": self.msg_vpn_name,
            "aclProfileName": acl_profile_name,
            "clientUsername": user.get("name"),
            "password": user.get("password"),
            "enabled": True,
            "guaranteedEndpointPermissionOverrideEnabled": False,
            "subscriptionManagerEnabled": False
        }
        logging.info(f"Create clientUsername {payload["clientUsername"]} on messageVPN {self.msg_vpn_name}")
        logging.debug(f"POST { url } payload { payload }")
        self.api("POST", url, json=payload)

    def create_queues(self, solace_queues):
        logging.info(f"Create Queues")
        for queue in solace_queues:
            self.create_queue(queue)

    def create_queue(self, queue):
        url = f"msgVpns/{ self.msg_vpn_name }/queues"
        configuration = queue["queueConfiguration"]
        configuration["msgVpnName"] = self.msg_vpn_name
        queue_name = configuration["queueName"]
        logging.debug(f"POST { url } payload { configuration }")
        logging.info(f"Create queue '{queue_name}' on messageVPN '{self.msg_vpn_name}'")
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
        delete_url = f"{url}/{queue_name}"
        logging.info(f"Delete queue { queue_name }")
        self.api("DELETE", delete_url)

    def delete_client_usernames(self, solace_client_usernames, config):
        logging.info(f"Delete Client Usernames")
        for user in config.get("users"):
            self.delete_client_username(user)

    def delete_client_username(self, user):
        url = f"msgVpns/{ self.msg_vpn_name }/clientUsernames"
        client_name = user["name"]
        delete_url = f"{url}/{client_name}"
        logging.info(f"Delete client name { client_name }")
        self.api("DELETE", delete_url)

    def delete_acl_profiles(self, solace_acl_profiles, app_name):
        logging.info(f"Delete ACL Profiles for {app_name}")
        for index, acl_profile in enumerate(solace_acl_profiles):
            self.delete_acl_profile(index, acl_profile)

    def delete_acl_profile(self, index, acl_profile):
        url = f"msgVpns/{ self.msg_vpn_name }/aclProfiles"
        profile = acl_profile["aclProfile"]
        #acl_profile_name = f"app-{ app_name.lower() }_{index}" if profile["aclProfileName"].startswith("app-") else profile["aclProfileName"]
        acl_profile_name = profile["aclProfileName"]
        delete_url = f"{url}/{acl_profile_name}"
        logging.info(f"Delete ACL profile { acl_profile_name }")
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