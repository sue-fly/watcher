# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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

import jsonschema

from watcher._i18n import _
from watcher.applier.actions import base
from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.model import element


class ChangeNovaServiceState(base.BaseAction):
    """Change the state of nova-compute service, deployed on a host

    By using this action, you will be able to update the state of a
    nova-compute service. A disabled nova-compute service can not be selected
    by the nova scheduler for furture deployment of server. A maintaining
    nova-compute service can not be selected by Watcher for future migration
    of instances.

    The action schema is::

        schema = Schema({
         'resource_id': str,
         'current': str,
         'target': str,
        })

    The `resource_id` references a nova-compute service name (list of available
    nova-compute services is returned by this command: ``nova service-list
    --binary nova-compute``).
    The `current` and 'target' value should be one of `ENABLED`, `DISABLED`,
    'MAINTAINING'.
    """

    CURRENT_STATE = 'current'
    TARGET_STATE = 'target'

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'resource_id': {
                    'type': 'string',
                    "minlength": 1
                },
                'current': {
                    'type': 'string',
                    'enum': [element.ServiceState.ONLINE.value,
                             element.ServiceState.OFFLINE.value,
                             element.ServiceState.ENABLED.value,
                             element.ServiceState.DISABLED.value,
                             element.ServiceState.MAINTAINING.value]
                },
                'target': {
                    'type': 'string',
                    'enum': [element.ServiceState.ONLINE.value,
                             element.ServiceState.OFFLINE.value,
                             element.ServiceState.ENABLED.value,
                             element.ServiceState.DISABLED.value,
                             element.ServiceState.MAINTAINING.value]
                }
            },
            'required': ['resource_id', 'current', 'target'],
            'additionalProperties': False,
        }

    def validate_parameters(self):
        try:
            jsonschema.validate(self.input_parameters, self.schema)
            return True
        except jsonschema.ValidationError as e:
            raise e

    @property
    def host(self):
        return self.resource_id

    @property
    def current_state(self):
        return self.input_parameters.get(self.CURRENT_STATE)

    @property
    def target_state(self):
        return self.input_parameters.get(self.TARGET_STATE)

    def execute(self):
        return self._nova_manage_service(self.target_state)

    def revert(self):
        return self._nova_manage_service(self.current_state)

    def _nova_manage_service(self, state):
        if state is None:
            raise exception.IllegalArgumentException(
                message=_("The target state is not defined"))

        nova = nova_helper.NovaHelper(osc=self.osc)
        if state == element.ServiceState.ENABLED.value:
            return nova.enable_service_nova_compute(self.host)
        elif state == element.ServiceState.DISABLED.value:
            return nova.disable_service_nova_compute(self.host,
                                                     'watcher_disabled')
        elif state == element.ServiceState.MAINTAINING.value:
            return nova.disable_service_nova_compute(self.host,
                                                     'watcher_maintaining')

    def pre_condition(self):
        pass

    def post_condition(self):
        pass

    def get_description(self):
        """Description of the action"""
        return ("Change the state of nova-compute service."
                "A disabled nova-compute service can not be selected "
                "by the nova for furture deployment of new instances. "
                "A maintaining nova-compute service can not be selected "
                "by Watcher for furture migration of instances.")
