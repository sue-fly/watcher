# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from oslo_log import log

from watcher.decision_engine.strategy.context.base import BaseStrategyContext
from watcher.decision_engine.strategy.selection.default import \
    DefaultStrategySelector

LOG = log.getLogger(__name__)


class DefaultStrategyContext(BaseStrategyContext):
    def __init__(self):
        super(DefaultStrategyContext, self).__init__()
        LOG.debug("Initializing Strategy Context")
        self._strategy_selector = DefaultStrategySelector()

    @property
    def strategy_selector(self):
        return self._strategy_selector

    def execute_strategy(self, goal, cluster_data_model):
        selected_strategy = self.strategy_selector.define_from_goal(goal)
        return selected_strategy.execute(cluster_data_model)
