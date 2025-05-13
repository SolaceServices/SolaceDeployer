from requests import request
from requests import exceptions
from deployer.errors import *
from functools import reduce

import os
import logging
from jsonpath_ng.ext import parse

def get_path_expr(data, path_expr):
    jsonpath_expr = parse(path_expr)
    return [match.value for match in jsonpath_expr.find(data)]

class EventPortal:

    def __init__(self, base_url, solace_cloud_token):
        if solace_cloud_token is None and os.environ.get('SOLACE_CLOUD_TOKEN') is None or base_url is None:
            raise EventPortalException(10,'You must define the base_url and Solace Cloud token')
        token = solace_cloud_token if solace_cloud_token else os.environ.get('SOLACE_CLOUD_TOKEN')
        self.base_url = base_url
        self.headers = {"authorization": f"Bearer {token}"}

    ## Design API calls
    def get_application_domain_object(self,application_domain_name):
        try:
            response = self.design_api("GET", "applicationDomains", params={"name": application_domain_name})
            application_domains = response.get("data")
            for domain in application_domains:
                if domain.get('name') == application_domain_name:
                    return domain
        except Exception as ex:
            raise ex

    def get_application_domain_id(self, application_domain_name):
        application_domain = self.get_application_domain_object(application_domain_name)
        return application_domain.get("id")

    def get_application_objects(self,application_domain_id):
        try:
            response = self.design_api("GET", "applications", params={"applicationDomainId": application_domain_id})
            applications = response.get("data")
            return applications
        except Exception as ex:
            raise ex

    def get_application_object_by_name(self, application_domain_id, application_name ):
        applications = self.get_application_objects(application_domain_id)
        for application in applications:
            if application.get("name") == application_name:
                return application

    def get_application_ids(self,application_domain_id):
        applications = self.get_application_objects(application_domain_id)
        jsonpath_expr = parse("$..id")
        return [match.value for match in jsonpath_expr.find(applications)]

    def get_application_id_by_name(self,application_domain_id, application_name):
        application = self.get_application_object_by_name(application_domain_id, application_name)
        return application["id"] if application["id"] else None

    def get_application_version_objects(self,application_id):
        try:
            response = self.design_api("GET", "applicationVersions", params={"applicationIds": application_id})
            versions = response.get("data")
            return versions
        except Exception as ex:
            raise ex

    def get_application_version_ids(self,application_id):
        versions = self.get_application_objects(application_id)
        jsonpath_expr = parse("$..id")
        return [match.value for match in jsonpath_expr.find(versions)]

    def get_application_version_object_by_name(self,application_id, version_name):
        versions = self.get_application_version_objects(application_id)
        for version in versions:
            if version.get("version") == version_name:
                return version

    def get_application_version_object_by_name_json(self,application_id, version_name):
        versions = self.get_application_version_objects(application_id)
        jsonpath_expr = parse(f'$..[?(@.name == "{ version_name }"]')
        return [match.value for match in jsonpath_expr.find(versions)]

    def get_application_version_id_by_name(self,application_id, version_name):
        version = self.get_application_version_object_by_name(application_id, version_name)
        return version["id"] if version["id"] else None

    ## Runtime API calls
    def get_environment_object(self, environment_name):
        try:
            response = self.runtime_api("GET", "environments")
            data = response.get("data")
            for env in data:
                if env.get('name') == environment_name:
                    return env
        except Exception as ex:
            raise ex

    def get_environment_id(self, environment_name):
        env = self.get_environment_object(environment_name)
        return env.get("id")

    def get_modeled_event_mesh_object(self, environment_id, mesh_name):
        try:
            response = self.runtime_api("GET", "eventMeshes", params={"environmentId": environment_id})
            data = response.get("data")
            for mesh in data:
                if mesh.get('name') == mesh_name:
                    return mesh
        except Exception as ex:
            raise ex

    def get_modeled_event_mesh_id(self, environment_id, mesh_name):
        mesh = self.get_modeled_event_mesh_object(environment_id, mesh_name)
        return mesh.get("id")

    def get_messaging_services_objects(self, mesh_id):
        try:
            response = self.runtime_api("GET", "messagingServices", params={"eventMeshId": mesh_id})
            services = response.get("data")
            return services
        except Exception as ex:
            raise ex

    def get_messaging_services_ids(self, mesh_id):
        services = self.get_messaging_services_objects(mesh_id)
        jsonpath_expr = parse("$..messagingServiceId")
        return [match.value for match in jsonpath_expr.find(services)]

    def preview_application_deployment(self, version_id, action, messaging_service_id):
        try:
            payload = {
                "applicationVersionId": version_id,
                "action": action,
                "eventBrokerId": messaging_service_id
            }
            response = self.runtime_api("POST", "runtimeManagement/applicationDeploymentPreviews", json=payload)
            return response
        except Exception as ex:
            logging.error(f"preview_application-deployment:: Exception {ex}")
            raise ex

    def create_application_deployment(self, version_id, action, messaging_service_id):
        try:
            payload = {
                "applicationVersionId": version_id,
                "action": action,
                "eventBrokerId": messaging_service_id
            }
            response = self.runtime_api("POST", "runtimeManagement/applicationDeployments", json=payload)
            return response
        except Exception as ex:
            raise ex

    ## MissionControl API calls
    def get_event_broker_objects(self, environment_id):
        try:
            response = self.missioncontrol_api("GET", "eventBrokerServices", params={"customAttributes": f"environmentId=={environment_id}"})
            brokers = response.get("data")
            return brokers
        except Exception as ex:
            raise ex

    def get_broker_ids(self, environment_id):
        brokers = self.get_event_broker_objects(environment_id)
        jsonpath_expr = parse("$..id")
        return [match.value for match in jsonpath_expr.find(brokers)]

    def get_broker_id_by_name(self, environment_id, broker_name):
        brokers = self.get_event_broker_objects(environment_id)
        for broker in brokers:
            if broker.get("name") == broker_name:
                return broker.get("id")

    def get_broker_by_name(self, environment_id, broker_name):
        brokers = self.get_event_broker_objects(environment_id)
        for broker in brokers:
            if broker.get("name") == broker_name:
                return broker

    def get_client_profile_objects(self, service_id):
        try:
            response = self.missioncontrol_api("GET", f"eventBrokerServices/{service_id}/clientProfiles")
            profiles = response.get("data")
            return profiles
        except Exception as ex:
            raise ex

    def get_client_profile_names(self, service_id):
        profiles = self.get_client_profile_objects(service_id)
        jsonpath_expr = parse("$..name")
        return [match.value for match in jsonpath_expr.find(profiles)]

    def profile_exists(self, service_id, preview_profile_names):
        profile_names = self.get_client_profile_names(service_id)
        return reduce(lambda acc, name: acc and any(map(lambda target: name == target, preview_profile_names)), profile_names, True)

    ## Internal api calls
    def design_api(self, method, endpoint, **kwargs):
        return self.api(method, f"architecture/{endpoint}", **kwargs)

    def runtime_api(self, method, endpoint, **kwargs):
        return self.api(method, f"architecture/{endpoint}", **kwargs)

    def missioncontrol_api(self, method, endpoint, **kwargs):
        return self.api(method, f"missionControl/{endpoint}", **kwargs)

    def api(self, method, endpoint, **kwargs):
        try:
            if method is None or endpoint is None:
                raise Exception('You must pass a method and endpoint')
            url = f"{self.base_url}/{endpoint}"
            response = request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except exceptions.HTTPError as exc:
            code = exc.response.status_code
            message = exc.response.json()
            logging.error(f"PORTAL::HTTP { method } Request to endpoint { endpoint } failed with status_code { code }: message: { message }")
            if code == 400 and "not currently deployed" not in message:
                return message
            if code == 422:
                raise UnprocessableEntity(exc.request, exc.response)
            raise EventPortalException(11, "PORTAL:HTTPError", f"code:{code}, message:{ message }")

        except Exception as exc:
            logging.error(f"PORTAL:HTTP { method } Request to endpoint { endpoint } failed with exception { exc}")
            raise EventPortalException( 12, "PORTAL:Exception", f"HTTP { method } Request to endpoint { endpoint } failed")