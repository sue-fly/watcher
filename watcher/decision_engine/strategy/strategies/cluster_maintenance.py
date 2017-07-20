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

from oslo_log import log
import six

from watcher._i18n import _
from watcher.common import exception as wexc
from watcher.decision_engine.model import element
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)


class ClusterMaintenance(base.ClusterMaintenanceBaseStrategy):
    """Cluster Maintenance"""
    INSTANCE_MIGRATION = "migrate"
    CHANGE_NOVA_SERVICE_STATE = "change_nova_service_state"

    def __init__(self, config, osc=None):
        super(ClusterMaintenance, self).__init__(config, osc)

    @classmethod
    def get_name(cls):
        return "cluster_maintenance"

    @classmethod
    def get_display_name(cls):
        return _("Cluster Maintenance Strategy")

    @classmethod
    def get_translatable_display_name(cls):
        return "Cluster Maintenance Strategy"

    @classmethod
    def get_schema(cls):
        return {
            "properties": {
                "node": {
                    "description": "The host name which need maintenance",
                    "type": "string",
                    "default": ""
                },
            },
        }

    def get_available_compute_nodes(self):
        available_node_status = {element.ServiceState.ENABLED.value,
                                 element.ServiceState.DISABLED.value}
        return {uuid: cn for uuid, cn in
                self.compute_model.get_all_compute_nodes().items()
                if cn.state == element.ServiceState.ONLINE.value and
                cn.status in available_node_status}

    def get_disabled_compute_nodes(self):
        disabled_node_status = element.ServiceState.DISABLED.value
        return {uuid: cn for uuid, cn in
                self.compute_model.get_all_compute_nodes().items()
                if cn.state == element.ServiceState.ONLINE.value and
                cn.status == disabled_node_status}

    def get_instance_state_str(self, instance):
        """Get instance state in string format"""
        if isinstance(instance.state, six.string_types):
            return instance.state
        elif isinstance(instance.state, element.InstanceState):
            return instance.state.value
        else:
            LOG.error('Unexpected instance state type, '
                      'state=%(state)s, state_type=%(st)s.',
                      dict(state=instance.state,
                           st=type(instance.state)))
            raise wexc.WatcherException

    def get_node_status_str(self, node):
        """Get node status in string format"""
        if isinstance(node.status, six.string_types):
            return node.status
        elif isinstance(node.status, element.ServiceState):
            return node.status.value
        else:
            LOG.error('Unexpected node status type, '
                      'status=%(status)s, status_type=%(st)s.',
                      dict(status=node.status,
                           st=type(node.status)))
            raise wexc.WatcherException

    def get_instance_capacity(self, instance):
        """Collect cpu, ram and disk capacity of a instance.

        :param instance: instance object
        :return: dict(cpu(cores), ram(MB), disk(B))
        """
        return dict(cpu=instance.vcpus,
                    ram=instance.memory,
                    disk=instance.disk)

    def get_node_capacity(self, node):
        """Collect cpu, ram and disk capacity of a node.

        :param node: node object
        :return: dict(cpu(cores), ram(MB), disk(B))
        """
        return dict(cpu=node.vcpus,
                    ram=node.memory,
                    disk=node.disk_capacity)

    def get_node_used(self, node):
        """Collect cpu, ram and disk used of a node.

        :param node: node object
        :return: dict(cpu(cores), ram(MB), disk(B))
        """
        vcpus_used = 0
        memory_used = 0
        disk_used = 0
        for instance in self.compute_model.get_node_instances(node):
            vcpus_used += instance.vcpus
            memory_used += instance.memory
            disk_used += instance.disk

        return dict(cpu=vcpus_used,
                    ram=memory_used,
                    disk=disk_used)

    def get_node_free(self, node):
        """Collect cpu, ram and disk free of a node.

        :param node: node object
        :return: dict(cpu(cores), ram(MB), disk(B))
        """
        node_capacity = self.get_node_capacity(node)
        node_used = self.get_node_used(node)
        return dict(cpu=node_capacity['cpu']-node_used['cpu'],
                    ram=node_capacity['ram']-node_used['ram'],
                    disk=node_capacity['disk']-node_used['disk'],
                    )

    def host_fits(self, source_node, destination_node):
        """check host fits

        return True if VMs could intensively migrate
        from source_node to destination_node.
        """

        source_node_used = self.get_node_used(source_node)
        destination_node_free = self.get_node_free(destination_node)
        metrics = ['cpu', 'ram']
        for m in metrics:
            if source_node_used[m] > destination_node_free[m]:
                return False
        return True

    def instance_fits(self, instance, node):
        """return True if one instance could migrate to the node."""
        instance_capacity = self.get_instance_capacity(instance)
        node_free = self.get_node_free(node)
        metrics = ['cpu', 'ram']
        for m in metrics:
            if instance_capacity[m] > node_free[m]:
                return False
        return True

    def change_node_service_state(self, node, current_state, target_state):
        params = {'current': current_state,
                  'target': target_state}
        self.solution.add_action(
            action_type=self.CHANGE_NOVA_SERVICE_STATE,
            resource_id=node.uuid,
            input_parameters=params)

    def add_action_enable_compute_node(self, node):
        """Add an action for node enabler into the solution."""
        current_state = node.status
        target_state = element.ServiceState.ENABLED.value
        return self.change_node_service_state(node,
                                              current_state,
                                              target_state)

    def enable_compute_node_if_disabled(self, node):
        node_status_str = self.get_node_status_str(node)
        if node_status_str != element.ServiceState.ENABLED.value:
            self.add_action_enable_compute_node(node)

    def add_action_disable_compute_node(self, node):
        """Add an action for node disability into the solution."""
        current_state = node.status
        target_state = element.ServiceState.DISABLED.value
        return self.change_node_service_state(node,
                                              current_state,
                                              target_state)

    def disable_compute_node_if_enabled(self, node):
        node_status_str = self.get_node_status_str(node)
        if node_status_str == element.ServiceState.ENABLED.value:
            self.add_action_disable_compute_node(node)

    def add_action_maintain_compute_node(self, node):
        """Add an action for node maintenance into the solution."""
        current_state = node.status
        target_state = element.ServiceState.MAINTAINING.value
        return self.change_node_service_state(node,
                                              current_state,
                                              target_state)

    def instance_migration(self, instance, source_node, destination_node):
        """Add an action for VM migration into the solution.

        :param instance: instance object
        :param source_node: node object
        :param destination_node: node object
        :return: None
        """
        instance_state_str = self.get_instance_state_str(instance)
        if instance_state_str == element.InstanceState.ACTIVE.value:
            migration_type = 'live'
        else:
            migration_type = 'cold'

        self.enable_compute_node_if_disabled(destination_node)

        if self.compute_model.migrate_instance(
                instance, source_node, destination_node):
            params = {'migration_type': migration_type,
                      'source_node': source_node.uuid,
                      'destination_node': destination_node.uuid}
            self.solution.add_action(action_type=self.INSTANCE_MIGRATION,
                                     resource_id=instance.uuid,
                                     input_parameters=params)

    def host_migration(self, source_node, destination_node):
        """host migration

        Migrate all instances from source_node to destination_node.
        Active instances use "live-migrate",
        and other instances use "cold-migrate"
        """
        instances = self.compute_model.get_node_instances(source_node)
        for instance in instances:
            self.instance_migration(instance, source_node, destination_node)

    def safe_maintain(self, maintenance_node):
        """safe maintain one compute node

        migrate all instances of the maintenance_node intensively
        to one unused host.
        It Calculate free resource of the unused node to determine
        a instance can yes or not migrated in.
        First, it will be able to enable the unused node.
        After all instances of the maintaining node has evacuated,
        it will set the maintenance_node in 'maintaining' status.
        This method won't result in more VMs migration among other hosts,
        and has least risk.
        """
        nodes = sorted(
            self.get_disabled_compute_nodes().values(),
            key=lambda x: self.get_node_capacity(x)['cpu'])
        if maintenance_node in nodes:
            nodes.remove(maintenance_node)

        for node in nodes:
            if self.host_fits(maintenance_node, node):
                self.host_migration(maintenance_node, node)
                self.add_action_maintain_compute_node(maintenance_node)
                return True

        return False

    def try_maintain(self, maintenance_node):
        """try best to maintain one compute node

        Try best to migrate all instances of the maintenance_node
        to the other nodes.
        This first-fit based method just consider how to evacuate
        all instances from maintenance_node. It Calculate free resource
        of a node to determine a instance can yes or not migrated in.
        After all instances of the maintaining node has evacuated,
        it set the maintenance_node in 'maintaining' status.
        """
        nodes = sorted(
            self.get_available_compute_nodes().values(),
            key=lambda x: self.get_node_free(x)['cpu'])
        if maintenance_node in nodes:
            nodes.remove(maintenance_node)

        instances = sorted(
            self.compute_model.get_node_instances(maintenance_node),
            key=lambda x: self.get_instance_capacity(x)['cpu'])

        for instance in instances:
            for destination_node in nodes:
                if self.instance_fits(instance, destination_node):
                    self.instance_migration(instance, maintenance_node,
                                            destination_node)

        if len(self.compute_model.get_node_instances(maintenance_node)) == 0:
            self.add_action_maintain_compute_node(maintenance_node)
        else:
            reason = ("Can't evacuate all instances from %s."
                      % maintenance_node.hostname)
            raise wexc.AuditSolutionNotFound(strategy=self.get_name(),
                                             reason=reason)

    def pre_execute(self):
        if not self.compute_model:
            raise wexc.ClusterStateNotDefined()

        if self.compute_model.stale:
            raise wexc.ClusterStateStale()

        LOG.debug(self.compute_model.to_string())

    def do_execute(self):
        LOG.info(_('Executing Cluster Maintenance Migration Strategy'))

        node = self.input_parameters.node
        if not node:
            LOG.debug("Please input the hostname which one needs maintenance")
            return

        maintenance_node = self.compute_model.get_node_by_uuid(node)

        # if no VMs in the maintenance_node, just maintain the compute node
        if len(self.compute_model.get_node_instances(maintenance_node)) == 0:
            self.add_action_maintain_compute_node(maintenance_node)
            return

        if not self.safe_maintain(maintenance_node):
            self.try_maintain(maintenance_node)

    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        LOG.debug(self.solution.actions)
        LOG.debug(self.compute_model.to_string())