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

import mock

from watcher.common import cinder_helper
from watcher.common import clients
from watcher.common import exception
from watcher.tests import base


@mock.patch.object(clients.OpenStackClients, 'cinder')
class TestCinderHelper(base.TestCase):

    def setUp(self):
        super(TestCinderHelper, self).setUp()

    @staticmethod
    def fake_storage_node(**kwargs):
        node = mock.MagicMock()
        node.binary = kwargs.get('binary', 'cinder-volume')
        node.host = kwargs.get('name', 'host@backend')

        return node

    def test_get_storage_node_list(self, mock_cinder):
        node1 = self.fake_storage_node()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        cinder_util.get_storage_node_list()
        cinder_util.cinder.services.list.assert_called_once_with(
            binary='cinder-volume')

    def test_get_storage_node_by_name_success(self, mock_cinder):
        node1 = self.fake_storage_node()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        node = cinder_util.get_storage_node_by_name('host@backend')

        self.assertEqual(node, node1)

    def test_get_storage_node_by_name_failure(self, mock_cinder):
        node1 = self.fake_storage_node()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        self.assertRaisesRegex(
            exception.StorageNodeNotFound,
            "The storage node failure could not be found",
            cinder_util.get_storage_node_by_name, 'failure')

    @staticmethod
    def fake_pool(**kwargs):
        pool = mock.MagicMock()
        pool.name = kwargs.get('name', 'host@backend#pool')

        return pool

    def test_get_storage_pool_list(self, mock_cinder):
        pool = self.fake_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.pools.list.return_value = [pool]
        cinder_util.get_storage_pool_list()
        cinder_util.cinder.pools.list.assert_called_once_with(detailed=True)

    def test_get_storage_pool_by_name_success(self, mock_cinder):
        pool1 = self.fake_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.pools.list.return_value = [pool1]
        pool = cinder_util.get_storage_pool_by_name('host@backend#pool')

        self.assertEqual(pool, pool1)

    def test_get_storage_pool_by_name_failure(self, mock_cinder):
        pool1 = self.fake_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [pool1]
        self.assertRaisesRegex(
            exception.PoolNotFound,
            "The pool failure could not be found",
            cinder_util.get_storage_pool_by_name, 'failure')

    @staticmethod
    def fake_volume_type(**kwargs):
        volume_type = mock.MagicMock()
        volume_type.name = kwargs.get('name', 'fake_type')
        extra_specs = {'volume_backend_name': 'backend'}
        volume_type.extra_specs = kwargs.get('extra_specs', extra_specs)
        return volume_type

    def test_get_volume_type_list(self, mock_cinder):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        cinder_util.get_volume_type_list()
        cinder_util.cinder.volume_types.list.assert_called_once_with()

    def test_get_volume_type_by_backendname_with_backend_exist(
            self, mock_cinder):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'backend')

        self.assertEqual(volume_type_name, volume_type1.name)

    def test_get_volume_type_by_backendname_with_no_backend_exist(
            self, mock_cinder):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'nobackend')

        self.assertEqual("", volume_type_name)
