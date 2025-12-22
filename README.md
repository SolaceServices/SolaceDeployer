# SolaceDeployer
Demonstrates different deployment strategies.  
This project can be used inside a CICD pipeline to execute deployments and undeployments of applications in a broker mesh.

## Prerequisites

- python3 [>= 3.12]
- virtual environment activated
-
```console
 python -m venv .venv
 source .venv/bin/activate
```

By running the following command, all dependencies will be installed/updated according to the content of the pyproject.toml file.
```console
python -m pip install -e . 
```

## Strategies for Deployment

There are 2 CICD strategies possible.
1. Use config-push in Event Portal for all environments, have it triggered by CICD pipeline for TST, ACC and PRD
2. Use config push in Event Portal for DEV and optional TST, extract the proper configuration from a given application from Event Portal, store it in GitLab, create merge request that triggers deployment to a given environment.

### Config-Push triggered by CICD pipeline

**Advantages:**

- all configuration is stored inside Event Portal
- all deployments to all environments are reflected in Event Portal.
- Uses Cloud API
-

**Disadvantages:**

- uses Event Management Agent, not yet ready for secure connections.
- You need predefined applicationIds to get the list of applicationVersionIds, you need predefined environmentIds for each environment and MEM's,  you can use the MEMId to get the specific broker service(s) for an environment and you can use the broker service id(s) to deploy the specific applicationIds onto the broker service

#### Steps to execute for a deployment:

1. Get the predefined values for an environment: environmentName, modeledEventMeshName, applicationDomainName(s), applicationName(s) and its applicationVersion(s) to deploy
2. Get the environmentId of the target environment: GET /api/v2/architecture/environments, extract the environmentId (id) from the response where name === {{environmentName}}
3. Get the meshId in the target environment: GET /api/v2/architecture/eventMeshes?environmentId={{environmentId}}, extract the meshId (id) from the response where name == {{modeledEventMeshName}}
4. Get the connected brokerIds: GET /api/v2/architecture/messagingServices?eventMeshId={{MeshId}}, extract the broker ids (data?.id)
5. For each application domain:
   1. Get the applicationDomainId: GET /api/v2/architecture/applicationDomains?name={{applicationDomainName}}, extract the applicationDomainId (id) from the response
   2. For each applicationName:
       1. Get the applicationId: GET /api/v2/architecture/applications?applicationDomainId={{applicationDomainId}}, extract the applicationId (id) where name === {{applicationName}}
       2. get the applicationVersionId: GET /api/v2/architecture/applicationVersions?applicationIds={{applicationId}}, extract the applicationVersionId (id) where version === {{applicationVersion}}
       3. For each brokerId from step 4:
           1. Deploy applicationVersionId: POST /api/v2/architecture/runtimeManagement/applicationDeployments with body:
              { "applicationVersionId":  "{{applicationVersionId}}", "action": "deploy", "eventBrokerId": "{{brokerId}}


### Pull Config from portal and push to environment with SEMP via CICD pipeline
**Advantages:**

- complete control on provenance
-

**Disadvantages:**

- Mix of Cloud API, SEMP/V2 API and/or terraform API
- convoluted, because it needs a lot of coding in the CICD pipelines. (extract the proper configuration sections for the different queues, get the ACL and client profiles from the DEV/TEST brokers, store the information into GitLab, create a PR to get it approved, once approved, the pipeline can deploy on a given environment.
- keep track of terraform state inside the pipeline
-

#### Steps to execute for a deployment:

1. Get the predefined values for an environment: environmentName, modeledEventMeshName, applicationDomainName, applicationName(s) and its applicationVersion(s) to deploy
2. Get the list of brokers with url, user, password, ands msgVpnName to use for deployment
3. Get the dev environmentId: GET /api/v2/architecture/environments, extract the environmentId (id) from the response where name === {{environmentName}}
4. Get the meshId for the environment: GET /api/v2/architecture/eventMeshes?environmentId={{environmentId}}, extract the meshId (id) from the response where name == {{modeledEventMeshName}}
5. Get one of the connected brokers: GET /api/v2/architecture/messagingServices?eventMeshId={{meshId}}, extract the brokerId and the msgVpnName ($..msgVpn)
6. For each application domain:
    1. Get the applicationDomainId: GET /api/v2/architecture/applicationDomains?name={{applicationDomainName}}, extract the applicationDomainId (id) from the response
    2. For each applicationName:
       1. Get the applicationId: GET /api/v2/architecture/applications?applicationDomainId={{applicationDomainId}}, extract the applicationId (id) where name == {{applicationName}}
       2. get the applicationVersionId: GET /api/v2/architecture/applicationVersions?applicationIds={{applicationId}}, extract the applicationVersionId (id) where version == {{applicationVersion}}
       3. Create a preview applicationVersionId: POST /api/v2/architecture/runtimeManagement/applicationDeployments with body:
         { "applicationVersionId":  "{{applicationVersionId}}", "action": "deploy or undeploy", "eventBrokerId": "{{brokerId}}

This will return a json file containing the new (requested) configuration and the original (existing) configuration for the application version.
The new (requested) configuration will  be used for deployment and the original (existing) configuration willnbe used for undeployment)

Create the semp config sections:

The configuration can be divided into 3 parts:
1. solaceAcl section (only 1)
2. solaceClientUsername or solaceAuthorizationGroup or solaceClientCertificateUsername section (only 1)
3. one or more solaceQueue sections (1 or more)

These have to be transformed to appropriate patch commands for the SEMP/v2 API or a set of terraform modules.

##### 1. SolaceACL section

The Solace ACL section is translated into 3 separate SEMP/V2 calls for create and one for delete:
1. Create aclProfile: POST /msgVpns/{msgVpnName}/aclProfiles
2. Create clientConnectExceptions: POST /msgVpns/{msgVpnName}/aclProfiles/{aclProfileName}/clientConnectExceptions (Not yet supported in the Portal)
3. Create subscribeTopicExceptions: POST /msgVpns/{msgVpnName}/aclProfiles/{aclProfileName}/subscribeTopicExceptions
4. Create publishTopicExceptions: POST /msgVpns/{msgVpnName}/aclProfiles/{aclProfileName}/publishTopicExceptions
5. Delete aclProfile: DELETE /msgVpns/{msgVpnName}/aclProfiles/{aclProfileName}

**Create aclProfile:**

Get body from response: _\$..requested[?(@.type=='solaceAcl')].value.aclProfile_
and add msgVpnName

POST /msgVpns/{msgVpnName}/aclProfiles

Body:
```
{
    "clientConnectDefaultAction": "allow",
    "publishTopicDefaultAction": "disallow",
    "subscribeTopicDefaultAction": "disallow",
    "aclProfileName": "app-[applicationId]",
    "subscribeShareNameDefaultAction": "allow",
    "msgVpnName": "[msgVpnName]"
}
```
**Create subscribeTopicExceptions:**

Determine the aclProfileName with _$..requested[?(@.type=='solaceAcl')].value.aclProfile.aclProfileName_ and use that in the url

For each entry in : _$..requested[?(@.type=='solaceAcl')].value.subscribeTopicExceptions_

POST /msgVpns/{msgVpnName}/aclProfiles/{aclProfileName}/subscribeTopicExceptions
For now only support for SMF syntax
Body:
```
{
    "aclProfileName": [aclProfileName],
    "subscribeTopicException": "[entry]",
    "subscribeTopicExceptionSyntax": "[smf or mqtt]",
    "msgVpnName": "[msgVpnName]"
}
```
**Create publishTopicExceptions:**

Determine the aclProfileName with _$..requested[?(@.type=='solaceAcl')].value.aclProfile.aclProfileName_ and use that in the url

For each entry in : _$..requested[?(@.type=='solaceAcl')].value.publishTopicExceptions_  

POST /msgVpns/{msgVpnName}/aclProfiles/{aclProfileName}/publishTopicExceptions
For now only support for SMF syntax
Body:
```
{
    "aclProfileName": "[aclProfileName]",
    "publishTopicException": "[entry]",
    "publishTopicExceptionSyntax": "[smf or mqtt]",
    "msgVpnName": "[msgVpnName]"
}
```
**Delete aclProfile**

Get aclProfileName from response: _$..existing[?(@.type=='solaceAcl')].value.aclProfile.aclProfileName_ and use that in the url.

DELETE  /msgVpns/{msgVpnName}/aclProfiles/{aclProfileName}

##### 2.a.  SolaceClientUsername

The Solace ClientUsername section is translated into a single SEMP/v2  call:
1. Create clientUsername: POST /msgVpns/{msgVpnName}/clientUsernames
2. Delete clientUsername: DELETE /msgVpns/{msgVpnName}/clientUsernames/{clientUsername}

**Create clientUsername:**

Get body from response: _$..requested[?(@.type=='solaceClientUsername')]_ and add msgVpnName  

POST /msgVpns/{msgVpnName}/clientUsernames

Body:
```
{
    "password": "[app-user-pwd]",
    "subscriptionManagerEnabled": false,
    "clientUsername": "[app-user]",
    "clientProfileName": "[clientProfileName]",
    "guaranteedEndpointPermissionOverrideEnabled": false,
    "aclProfileName": "app-[applicationId]",
    "enabled": true,
    "msgVpnName": "[msgVpnName]"
  }
```

**Delete clientUsername**

Get clientUsername from response: _$..existing[?(@.type=='solaceClientUsername')].value.clientUsername_ and use that in the url.

DELETE /msgVpns/{msgVpnName}/clientUsernames/{clientUsername}

##### 2.b.  SolaceAuthorizationGroup

The Solace AuthorizationGroup section is translated into a single SEMP/v2  call:
1. Create authorizationGroup: POST /msgVpns/{msgVpnName}/authorizationGroups
2. Delete authorizationGroup: DELETE /msgVpns/{msgVpnName}/authorizationGroups/{authorizationGroup}

**Create authorizationGroup:**

Get body from response: _$..requested[?(@.type=='solaceAuthorizationGroup')]_ and add msgVpnName

POST /msgVpns/{msgVpnName}/authorizationGroups

Body:
```
{
    "aclProfileName": "[aclProfileName]",
    "authorizationGroupName": "[authorizationGroup]",
    "clientProfileName": "default",
    "enabled": true,
    "msgVpnName": "[msgVpnName]"
  }
```

**Delete authorizationGroup**

Get authorizationGroup from response: _$..existing[?(@.type=='solaceAuthorizationGroup')].value.authorizationGroupName_ and use that in the url.

DELETE /msgVpns/{msgVpnName}/authorizationGroups/{authorizationGroup}

##### 2.c.  SolaceClientCertificateUsername

The Solace ClientCertificateUsername section is translated into a single SEMP/v2  call:
1. Create clientCertificateUsername: POST /msgVpns/{msgVpnName}/clientUsernames
2. Delete clientCertificateUsername: DELETE /msgVpns/{msgVpnName}/clientUsernames/{clientCertificateUsername}

**Create clientCertificateUsername:**

Get body from response: _$..requested[?(@.type=='solaceClientCertificateUsername')]_ and add msgVpnName

POST /msgVpns/{msgVpnName}/clientUsernames

Body:
```
{
    "subscriptionManagerEnabled": false,
    "clientUsername": "[clientCertificateUsername]",
    "clientProfileName": "[clientProfileName]",
    "guaranteedEndpointPermissionOverrideEnabled": false,
    "aclProfileName": "app-[applicationId]",
    "enabled": true,
    "msgVpnName": "[msgVpnName]"
  }
```

**Delete clientCertificateUsername**

Get clientCertificateUsername from response: _$..existing[?(@.type=='solaceClientCertificateUsername')].value.clientUsername_ and use that in the url.

DELETE /msgVpns/{msgVpnName}/clientUsernames/{clientCertificateUsername}

##### 3. SolaceQueue section

The Solace Queue section is translated into 3 separate SEMP/V2 calls per queue:
1. Create Queue: POST /msgVpns/{msgVpnName}/queues
2. Create Subscription: POST /msgVpns/{msgVpnName}/queues/{queueName}/subscriptions
3. Delete Queue: DELETE /msgVpns/{msgVpnName}/queues/{queueName}

Get the queue definitions: _$..requested[?(@.type=='solaceQueue')].value_

For each definition \$def: 

**Create Queue:**  
Create queue with body: $def.queueConfiguration and add the msgVpnName attribute:

POST /msgVpns/{msgVpnName}/queues

Body:
```
{
    "msgVpnName": "[msgVpnName]",
    "accessType": "exclusive",
    "ingressEnabled": true,
    "owner": "[clientUsername or clientCertificatUsername or authorizationGroup]",
    "queueName": "[queueName]",
    "egressEnabled": true,
    "permission": "no-access",
    "maxMsgSpoolUsage": 5000
}
```

Get subscriptions _\$def.subscriptions_  
For each entry in _\$def.subscriptions_  
**Create subscription:**  

POST /msgVpns/{msgVpnName}/queues/{queueName}/subscriptions

Body:
```
{
    "msgVpnName": "[msgVpnName]",
    "queueName": "[queueName]",
    "subscriptionTopic": "[entry]"
}
```
**Delete Queue**
Get existing queueName with _$def.queueConfiguration.queueName_

DELETE /msgVpns/{msgVpnName}/queues/{queueName}

## Testing it out

The file _SolaceSampleDomain.json_ can be loaded into the Event Portal.
Make sure there are at least 2 environments present [Dev, Test]
Make sure ech environment has at least one broker running
Create a Modeled Event mesh for each environment and note their names.
Connect at least one Broker to each Modeled Event Mesh. This will use the Cloud EMA for that Modeled Event Mesh (if enabled)
Make a note of the 'Manage with Semp' configuration from the brokers in the Event Portal CLuster Manager.
- url
- username
- password
- message vpn name

These values are needed in the next section

My test situation:

| Environment | MEM        | Broker
|-------------|------------| --
| Dev         | memName | brokerDEV
| Test        | memName | brokerTST

Create 
config/eventPortal.json
```
{
  "baseUrl": "https://api.solace.cloud/api/v2",
  "token": "[some token with sufficient permissions]"
}
```
config/dev.json
```shell
{
  "environment": "dev",
  "environmentName": "Dev",
  "memName": "SampleMesh",
  "domains": [
    {
      "domainName": "SolaceSampleDomain",
      "applications": [
        {
          "name": "Application_1",
          "version": "0.1.2",
          "user": {
            "name": "app1-dev",
            "type": "solaceClientUsername"
            "password": "app1-dev"
          }
        },
        {
          "name": "Application_2",
          "version": "0.1.0"
          "user": {
            "name": "PubSubRoleA",
            "type": "solaceAuthorizationGroup"
          }
        },
        {
          "name": "Application_3",
          "version": "0.1.0"
          "user": {
            "name": "app3_dev",
            "type": "solaceClientCertificateUsername"
          }
        }
      ]
    }
  ],
  "brokers": [ {
    "name": "[dev broker name]",
    "url": "[Base path  from EP ClusterManager/Manage/SEMP-REST API]",
    "user": "[Username from EP ClusterManager/Manage/SEMP-REST API]",
    "password": "[Password from EP ClusterManager/Manage/SEMP-REST API]",
    "msgVpnName": "[Message VPN Name from EP ClusterManager/Manage/SEMP-REST API]"
  }]
}
```
config/tst.json
```shell
{
  "environment": "tst",
  "environmentName": "Test",
  "memName": "SampleMesh",
  "domains":[
    {
      "domainName": "SolaceSampleDomain",
      "applications": [
        {
          "name": "Application_1",
          "version": "0.1.2",
          "user": {
            "name": "app1-tst",
            "type": "solaceClientUsername"
            "password": "app1-tst"
          }
        },
        {
          "name": "Application_2",
          "version": "0.1.0"
          "user": {
            "name": "app2-tst",
            "type": "solaceClientUsername"
            "password": "app2-tst"
          }
        }
      ]
    }
  ],
  "brokers": [ {
    "name": "[test broker name]",
    "url": "[Base path  from EP ClusterManager/Manage/SEMP-REST API]",
    "user": "[Username from EP ClusterManager/Manage/SEMP-REST API]",
    "password": "[Password from EP ClusterManager/Manage/SEMP-REST API]",
    "msgVpnName": "[Message VPN Name from EP ClusterManager/Manage/SEMP-REST API]"
  }]
}
```
Make sure the Cloud EMA's are running for each environment:

If these don't run you cannot use configPush
Execute a config-push on the EventPortal for both applications on the dev broker 

Now you can test both strategies for deployment on tst:

### ConfigPush

Deploy version to Test
```shell
runAction --mode configPush --action=deploy --target=tst --appl "[{\"Domainname\":[\"app_1\",\"app_2\",\"app_3\",\"app_4\"]}]"
```
Check on the Test broker if acl, clientUsernames and Queues are created

Undeploy version from Test
```
runAction --mode configPush --action=undeploy --target=tst --appl "[{\"Domainname\":[\"app_1\",\"app_2\",\"app_3\",\"app_4\"]}]"
```
Check if acls, clientUsernames and queues are removed

### Semp Deployment
Deploy version to Test
```shell
runAction --mode semp --action=deploy --target=tst --appl "[{\"Domainname\":[\"app_1\",\"app_2\",\"app_3\",\"app_4\"]}]"
```
Check on the Test broker if acl, clientUsernames and Queues are created

Undeploy version from Test
```
runAction --mode semp --action=undeploy --target=tst --appl "[{\"Domainname\":[\"app_1\",\"app_2\",\"app_3\",\"app_4\"]}]"
```
Check if acls, clientUsernames and queues are removed

Save deployment of version for Test
```shell
runAction --mode semp --action=save --target=tst --appl "[{\"Domainname\":[\"app_1\",\"app_2\",\"app_3\",\"app_4\"]}]"
```
Check if there are folders created in store with this format: store/[app_domain]/[application]/[version]/preview-[state].json

### Test connectivity Dev environment

Send message to Application_1 on Dev
```shell
sdkperf_amqp -cip amqps://mr-connection-[dev serviceId].messaging.solace.cloud -cu app2-dev@[dev msgvpn] -cp 'app2-dev' -ptl 'topic://#P2P/QUE/Event_2MessageQueue' -msa 100 -mn 5 -mr 1
```

Receive messages from Application_1  on dev
```shell
sdkperf_java  -cip tcps://mr-connection-[dev serviceId].messaging.solace.cloud -cu app1-dev@[dev msgvpn] -cp app1-dev -sql 'Event_2MessageQueue' -md
```

Send message to Application_2 on Dev
```shell
sdkperf_amqp -cip amqps://mr-connection-[dev serviceId].messaging.solace.cloud -cu app1-dev@s[dev msgvpn] -cp 'app1-dev' -ptl 'topic://#P2P/QUE/Event_1MessageQueue' -msa 100 -mn 5 -mr 1
```

Receive messages from Application_2  on dev
```shell
sdkperf_java  -cip tcps://mr-connection-[dev serviceId].messaging.solace.cloud -cu app2-dev@[dev msgvpn] -cp app2-dev -sql 'Event_1MessageQueue' -md
```

### Test connectivity Test environment

Send message to Application_1 on tst
```shell
sdkperf_amqp -cip amqps://mr-connection-[tst serviceId].messaging.solace.cloud -cu app2-tst@[tst msgvpn] -cp 'app2-tst' -ptl 'topic://#P2P/QUE/Event_2MessageQueue' -msa 100 -mn 5 -mr 1
```

Receive messages from Application_1  on tst
```shell
sdkperf_java  -cip tcps://mr-connection-[tst serviceId].messaging.solace.cloud -cu app1-tst@[tst msgvpn] -cp app1-tst -sql 'Event_2MessageQueue' -md
```

Send message to Application_2 on tst
```shell
sdkperf_amqp -cip amqps://mr-connection-[tst serviceId].messaging.solace.cloud -cu app1-tst@s[tst msgvpn] -cp 'app1-tst' -ptl 'topic://#P2P/QUE/Event_1MessageQueue' -msa 100 -mn 5 -mr 1
```

Receive messages from Application_2  on tst
```shell
sdkperf_java  -cip tcps://mr-connection-[tst serviceId].messaging.solace.cloud -cu app2-tst@[tst msgvpn] -cp app2-tst -sql 'Event_1MessageQueue' -md
```
