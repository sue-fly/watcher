# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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

from oslo_config import cfg

from watcher.common import exception
from watcher.notifications import base as notificationbase
from watcher.notifications import goal as goal_notifications
from watcher.notifications import strategy as strategy_notifications
from watcher.objects import base
from watcher.objects import fields as wfields

CONF = cfg.CONF


@base.WatcherObjectRegistry.register_notification
class AuditPayload(notificationbase.NotificationPayloadBase):
    SCHEMA = {
        'uuid': ('audit', 'uuid'),

        'audit_type': ('audit', 'audit_type'),
        'state': ('audit', 'state'),
        'parameters': ('audit', 'parameters'),
        'interval': ('audit', 'interval'),
        'scope': ('audit', 'scope'),
        # 'goal_uuid': ('audit', 'goal_uuid'),
        # 'strategy_uuid': ('audit', 'strategy_uuid'),

        'created_at': ('audit', 'created_at'),
        'updated_at': ('audit', 'updated_at'),
        'deleted_at': ('audit', 'deleted_at'),
    }

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'uuid': wfields.UUIDField(),
        'audit_type': wfields.StringField(),
        'state': wfields.StringField(),
        'parameters': wfields.FlexibleDictField(nullable=True),
        'interval': wfields.IntegerField(nullable=True),
        'scope': wfields.FlexibleListOfDictField(nullable=True),
        'goal_uuid': wfields.UUIDField(),
        'strategy_uuid': wfields.UUIDField(nullable=True),
        'goal': wfields.ObjectField('GoalPayload'),
        'strategy': wfields.ObjectField('StrategyPayload', nullable=True),

        'created_at': wfields.DateTimeField(nullable=True),
        'updated_at': wfields.DateTimeField(nullable=True),
        'deleted_at': wfields.DateTimeField(nullable=True),
    }

    def __init__(self, audit, **kwargs):
        super(AuditPayload, self).__init__(**kwargs)
        self.populate_schema(audit=audit)


@base.WatcherObjectRegistry.register_notification
class AuditStateUpdatePayload(notificationbase.NotificationPayloadBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'old_state': wfields.StringField(nullable=True),
        'state': wfields.StringField(nullable=True),
    }


@base.WatcherObjectRegistry.register_notification
class AuditUpdatePayload(AuditPayload):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'state_update': wfields.ObjectField('AuditStateUpdatePayload'),
    }

    def __init__(self, audit, state_update, goal, strategy):
        super(AuditUpdatePayload, self).__init__(
            audit=audit,
            state_update=state_update,
            goal=goal,
            strategy=strategy)


@notificationbase.notification_sample('audit-update.json')
@base.WatcherObjectRegistry.register_notification
class AuditUpdateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('AuditUpdatePayload')
    }


def send_update(context, audit, service='infra-optim',
                host=None, old_state=None):
    """Emit an audit.update notification."""
    goal = None
    strategy = None
    try:
        goal = audit.goal
        if audit.strategy_id:
            strategy = audit.strategy
    except NotImplementedError:
        raise exception.EagerlyLoadedAuditRequired(audit=audit.uuid)

    goal_payload = goal_notifications.GoalPayload(goal=goal)

    strategy_payload = None
    if strategy:
        strategy_payload = strategy_notifications.StrategyPayload(
            strategy=strategy)

    state_update = AuditStateUpdatePayload(
        old_state=old_state,
        state=audit.state if old_state else None)

    versioned_payload = AuditUpdatePayload(
        audit=audit,
        state_update=state_update,
        goal=goal_payload,
        strategy=strategy_payload,
    )

    notification = AuditUpdateNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='audit',
            action=wfields.NotificationAction.UPDATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)
