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

from collections import deque
import tempfile

import fabric.exceptions
import mock

from shotgun.config import Config
from shotgun.manager import Manager
from shotgun.test import base


class TestManager(base.BaseTestCase):

    @mock.patch('shotgun.manager.Driver.getDriver')
    @mock.patch('shotgun.manager.utils.compress')
    @mock.patch('shutil.rmtree')
    def test_snapshot(self, mrmtree, mcompress, mget):
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
        conf.self_log_object = {"type": "file", "path": "/path"}
        manager = Manager(conf)
        manager.snapshot()
        calls = [mock.call(data, conf), mock.call(conf.self_log_object, conf)]
        mget.assert_has_calls(calls, any_order=True)
        mrmtree.assert_called_once_with('/target', onerror=mock.ANY)

    @mock.patch('shotgun.manager.Driver.getDriver')
    @mock.patch('shutil.rmtree')
    @mock.patch('shotgun.manager.utils.compress')
    def test_snapshot_network_error(self, mcompress, mrmtree, mget):
        objs = [
            {"type": "file",
             "path": "/remote_file1",
             "host": {"address": "remote_host1"},
             },
            {"type": "dir",
             "path": "/remote_dir1",
             "host": {"address": "remote_host1"},
             },
            {"type": "file",
             "path": "/remote_file1",
             "host": {"address": "remote_host2"},
             },
        ]
        drv = mock.MagicMock()
        drv.snapshot.side_effect = [
            fabric.exceptions.NetworkError,
            None,
            fabric.exceptions.NetworkError,
            None,
            None,
        ]
        mget.return_value = drv
        conf = Config()
        conf.objs = deque(objs)
        offline_obj = {
            'path': '/remote_file1',
            'host': {'address': 'remote_host1'},
            'type': 'offline',
        }
        processed_obj = {
            'path': '/remote_file1',
            'host': {'address': 'remote_host2'},
            'type': 'file',
        }
        manager = Manager(conf)
        manager.snapshot()
        mget.assert_has_calls([mock.call(offline_obj, conf),
                               mock.call(processed_obj, conf),
                               mock.call(offline_obj, conf),
                               mock.call(offline_obj, conf)], any_order=True)
        mrmtree.assert_called_once_with('/tmp', onerror=mock.ANY)

    @mock.patch('shotgun.manager.Manager.action_single')
    def test_report(self, mock_action):
        objs = ["o1", "o2"]
        mock_action.side_effect = [["r1", "r2"], ["r3"]]
        conf = mock.Mock()
        conf.objects = objs
        manager = Manager(conf)
        manager.action_single = mock_action
        reports = []
        for rep in manager.report():
            reports.append(rep)
        self.assertEqual(["r1", "r2", "r3"], reports)

        expected_calls = [
            mock.call('o1', action='report'),
            mock.call('o2', action='report')]
        self.assertEqual(expected_calls, mock_action.call_args_list)

    @mock.patch('shotgun.manager.Driver')
    def test_action_single(self, mock_driver):
        mock_driver_instance = mock.Mock()
        mock_driver_instance.report = mock.Mock()
        mock_driver_instance.snapshot = mock.Mock()
        mock_driver.getDriver = mock.Mock(return_value=mock_driver_instance)
        manager = Manager('conf')

        manager.action_single('object', action='report')
        mock_driver.getDriver.assert_called_once_with('object', 'conf')
        mock_driver_instance.report.assert_called_once_with()
        self.assertFalse(mock_driver_instance.snapshot.called)
        mock_driver.getDriver.reset_mock()

        # default action should be 'snapshot'
        manager.action_single('object')
        mock_driver.getDriver.assert_called_once_with('object', 'conf')
        mock_driver_instance.report.mock_reset()
        mock_driver_instance.snapshot.assert_called_once_with()
        self.assertFalse(mock_driver_instance.report.called)

    @mock.patch('shotgun.manager.Manager.action_single')
    @mock.patch('shutil.rmtree')
    def test_snapshot_rm_without_disk_space(self, mrmtree, mock_action):
        mock_action.side_effect = IOError(28, "Not enough space")

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
        conf.self_log_object = {"type": "file", "path": "/path"}
        manager = Manager(conf)

        self.assertRaises(IOError, manager.snapshot)
        calls = [mock.call('/target', onerror=mock.ANY) for _ in range(2)]
        mrmtree.assert_has_calls(calls)

    @mock.patch('shotgun.manager.Manager.action_single')
    @mock.patch('shutil.rmtree')
    def test_snapshot_doesnt_clean_on_generic_ioerror(self, mrmtree,
                                                      mock_action):
        mock_action.side_effect = IOError(1, "Generic error")

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
        conf.self_log_object = {"type": "file", "path": "/path"}
        manager = Manager(conf)

        self.assertRaises(IOError, manager.snapshot)
        mrmtree.assert_called_once_with('/target', onerror=mock.ANY)
