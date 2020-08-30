
# Copyright 2017 Bloomberg Finance L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import requests
import time
import kubernetes.client

from powerfulseal import makeLogger

from ..metriccollectors.stdout_collector import StdoutCollector
from .action_abstract import ActionAbstract


class ActionClone(ActionAbstract):

  def __init__(self, name, schema, k8s_inventory, logger=None, metric_collector=None):
    self.name = name
    self.schema = schema
    self.k8s_inventory = k8s_inventory
    self.logger = logger or makeLogger(__name__, name)
    self.metric_collector = metric_collector or StdoutCollector()

  def get_source_schema(self, source):
    # currently, only deployments are supported
    source_deployment = source.get("deployment")
    deployment = self.k8s_inventory.k8s_client.get_deployment(
      name=source_deployment.get("name"),
      namespace=source_deployment.get("namespace"),
    )
    return deployment

  def execute(self):
    # get the source deployment
    try:
      source_schema = self.get_source_schema(self.schema.get("source"))
    except:
      return False

    # build the body for the request to create
    body = kubernetes.client.V1Deployment()
    body.metadata = kubernetes.client.V1ObjectMeta(
      name=source_schema.metadata.name + "-chaos",
      namespace=source_schema.metadata.namespace,
      annotations=dict(
        original_deployment=source_schema.metadata.name,
        chaos_scenario=self.name,
      ),
      labels = dict(
        chaos="true",
      ),
    )
    body.spec = kubernetes.client.V1DeploymentSpec(
      replicas=self.schema.get("replicas", 1),
      selector=source_schema.spec.selector,
      template=source_schema.spec.template,
    )

    if body.spec.selector.match_expressions is not None:
      self.logger.error("Deployment is using match_expressions. Not supported")
      return False

    # handle the labels modifiers
    for label_modifier in self.schema.get("labels", []):
      # TODO handle the labels mutations
      pass

    # handle the mutations
    for mutation in self.schema.get("mutations", []):
      # TODO handle the environment mutation
      # TODO handle the tc mutation
      # TODO handle the toxiproxy mutation
      pass

    # insert the extra selector
    body.spec.selector.match_labels["chaos"] = "true"
    body.spec.template.metadata.labels["chaos"] = "true"

    # create the clone
    try:
      response = self.k8s_inventory.k8s_client.create_deployment(
        namespace=body.metadata.namespace,
        body=body,
      )
      print(response)
    except:
      return False

    # TODO add a cleanup action to remove the clone

    return True
