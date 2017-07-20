# -*- encoding: utf-8 -*-
# Copyright (c) 2017 chinac.com
#
# Authors: suzhengwei<suzhengwei@chinac.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import random

from oslo_log import log
import six

from watcher._i18n import _
from watcher.decision_engine.model import element
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)


class BasicPowerSave(base.PowerSaveBaseStrategy):
    """Basic Power Save Strategy"""
    CHANGE_NOVA_SERVICE_STATE = "change_nova_service_state"
    CHANGE_NODE_POWER_STATE = "change_nova_power_state"

    def __init__(self, config, osc=None):
        super(BasicPowerSave, self).__init__(config, osc)
        self.standby_hosts = 1

    @classmethod
    def get_name(cls):
        return "basic_power_save"

    @classmethod
    def get_display_name(cls):
        return _("Basic Power Save Strategy")

    @classmethod
    def get_translatable_display_name(cls):
        return "Basic Power Save Strategy"

    @classmethod
    def get_schema(cls):
        return {
            "properties": {
                "standby": {
                    "description": "The host standby number, which is disabled "
                                   "but not poweroff, must more than 0",
                    "type": "number",
                    "default": 1
                },
            },
        }

    def get_unused_compute_nodes(self):
        unused_node_status = {element.ServiceState.DISABLED.value}
        return {uuid: cn for uuid, cn in
                self.compute_model.get_all_compute_nodes().items()
                if cn.state == element.ServiceState.ONLINE.value and
                cn.status == unused_node_status}

    def get_poweroff_compute_nodes(self):
        poweroff_node_status = element.ServiceState.POWEROFF.value
        return {uuid: cn for uuid, cn in
                self.compute_model.get_all_compute_nodes().items()
                if cn.state == element.ServiceState.OFFLINE.value and
                cn.status == poweroff_node_status}

    def get_poweron_compute_nodes(self):
        poweron_node_status = element.ServiceState.POWERON.value
        return {uuid: cn for uuid, cn in
                self.compute_model.get_all_compute_nodes().items()
                if cn.state == element.ServiceState.ONLINE.value and
                cn.status == poweron_node_status}

    def add_node_power_action(self, node, action):
        """Add an action for node disability into the solution.

        :param node: node
        :param state: node power state, power on or power off
        :return: None
        """
        # update disable reason before power on/off
        if action == 'on':
            params = {'current': element.ServiceState.POWEROFF.value,
                      'target': element.ServiceState.POWERON.value}
        if action == 'off':
            params = {'current': element.ServiceState.DISABLED.value,
                      'target': element.ServiceState.POWEROFF.value}
        self.solution.add_action(
            action_type=self.CHANGE_NOVA_SERVICE_STATE,
            resource_id=node.uuid,
            input_parameters=params)

        # power action
        power_action_params = {'state': action}
        self.solution.add_action(
            action_type=self.CHANGE_NODE_POWER_STATE,
            resource_id=node.uuid,
            input_parameters=power_action_params)

    def pre_execute(self):
        """Pre-execution phase

        This can be used to fetch some pre-requisites or data.
        """
        LOG.info(_LI("Initializing Basic Power Save Strategy"))

        if not self.compute_model:
            raise wexc.ClusterStateNotDefined()

        if self.compute_model.stale:
            raise wexc.ClusterStateStale()

        # If there are still some compute nodes poweron but not online
        # before this audit. That means some problem maybe happened to 
        # the power-on nodes. It need administrator to check.
        if len(self.get_poweron_compute_nodes())> 0 :
            LOG.warn("Some compute nodes power on but can not bootup, "
                     "please check it.")

    def do_execute(self):
        """Strategy execution phase

        This phase is where you should put the main logic of your strategy.
        """

        standby_number = self.input_parameters.standby
        disabled_node_number = len(self.get_unused_compute_nodes())
        poweroff_node_number = len(self.get_poweroff_compute_nodes())

        if disabled_node_number > standby_number:
            for node in random.sample(self.get_unused_compute_nodes(),
                                      (disabled_node_number - standby_number)):
                self.add_node_power_action(node, 'off')
        if disabled_node_number < standby_number:
            poweron_node_number = min(standby_number-disabled_node_number,
                                      poweroff_node_number)
            for node in random.sample(self.get_poweroff_compute_nodes(),
                                      poweron_node_number):
                self.add_node_power_action(node, 'on')

    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        self.solution.model = self.compute_model
        LOG.debug(self.compute_model.to_string())
