#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import tempfile

import fabric.exceptions
import mock

from shotgun.config import Config
from shotgun.manager import Manager
from shotgun.test import base


class TestManager(base.BaseTestCase):

    @mock.patch('shotgun.manager.Driver.getDriver')
    @mock.patch('shotgun.manager.utils.execute')
    @mock.patch('shotgun.manager.utils.compress')
    def test_snapshot(self, mcompress, mexecute, mget):
        data = {
            "type": "file",
            "path": "/remote_dir/remote_file",
            "host": {
                "address": "remote_host",
            },
        }
        conf = mock.MagicMock()
        conf.target = "/target/data"
        conf.objects = [data]
        conf.lastdump = tempfile.mkstemp()[1]
        manager = Manager(conf)
        manager.snapshot()
        mget.assert_called_once_with(data, conf)
        mexecute.assert_called_once_with('rm -rf /target')

    @mock.patch('shotgun.manager.Driver.getDriver')
    @mock.patch('shotgun.manager.utils.execute')
    @mock.patch('shotgun.manager.utils.compress')
    def test_snapshot_network_error(self, mcompress, mexecute, mget):
        data = {
            "dump": {
                "role": {
                    "objects": [
                        {
                            "type": "file",
                            "path": "/remote_dir/remote_file",
                        },
                        {
                            "type": "dir",
                            "path": "/remote_dir/remote_dir",
                        },
                    ],
                    "hosts": [
                        {
                            "address": "remote_host",
                        },
                    ],
                },
            },
        }
        drv = mock.MagicMock()
        # two objects: type='file' and type='dir'
        # First one throws NetworkError, the second is processed without it
        drv.snapshot.side_effect = 2 * [fabric.exceptions.NetworkError, None]
        mget.return_value = drv
        conf = Config(data)
        failed_obj_1st_attempt = {
            'path': '/remote_dir/remote_file',
            'host': {'address': 'remote_host'},
            'type': 'file', 'attempts': 1,
        }
        processed_obj = {
            'path': '/remote_dir/remote_dir',
            'host': {'address': 'remote_host'},
            'type': 'dir', 'attempts': 2,
        }
        failed_obj_2nd_attempt = {
            'path': '/remote_dir/remote_file',
            'host': {'address': 'remote_host'},
            'type': 'file', 'attempts': 0,
        }
        offline_obj = {
            'path': '/remote_dir/remote_file',
            'host': {'address': 'remote_host'},
            'type': 'offline', 'attempts': 0,
        }
        manager = Manager(conf)
        manager.snapshot()
        self.assertEquals([mock.call(failed_obj_1st_attempt, conf),
                           mock.call(processed_obj, conf),
                           mock.call(failed_obj_2nd_attempt, conf),
                           mock.call(offline_obj, conf)],
                          mget.call_args_list)
        mexecute.assert_called_once_with('rm -rf /tmp')
