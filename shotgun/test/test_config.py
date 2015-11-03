#    Copyright 2013 Mirantis, Inc.
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

import time

import mock

from shotgun.config import Config
from shotgun.test import base


class TestConfig(base.BaseTestCase):

    def test_timestamp(self):
        t = time.localtime()
        with mock.patch('shotgun.config.time') as MockedTime:
            MockedTime.localtime.return_value = t
            MockedTime.strftime.side_effect = time.strftime
            conf = Config({})
            stamped = conf._timestamp("sample")
        self.assertEqual(
            stamped,
            "sample-{0}".format(time.strftime('%Y-%m-%d_%H-%M-%S', t))
        )

    def test_target_timestamp(self):
        conf = Config({
            "target": "/tmp/sample",
            "timestamp": True
        })
        self.assertRegex(
            conf.target,
            ur"\/tmp\/sample\-[\d]{4}\-[\d]{2}\-[\d]{2}_"
            "([\d]{2}\-){2}[\d]{2}",
        )

    @mock.patch('shotgun.config.settings')
    def test_timeout(self, m_settings):
        conf = Config({})
        self.assertIs(conf.timeout, m_settings.DEFAULT_TIMEOUT)

    def test_pass_default_timeout(self):
        timeout = 1345
        conf = Config({
            'timeout': timeout,
        })
        self.assertEqual(conf.timeout, timeout)

    def test_objects_per_host(self):
        data = {
            "dump": {
                "master": {
                    "objects":
                        [{"path": "/etc/nailgun",
                          "type": "dir"},
                         {"command": "uname -a",
                          "to_file": "uname_a.txt",
                          "type": "command"},
                         {"command": "lsmod",
                          "to_file": "lsmod.txt",
                          "type": "command"},
                         {"path": "/etc/*-release",
                          "type": "file"}],
                    "hosts": [{"ssh-key": "/root/.ssh/id_rsa",
                               "address": "10.109.2.2"}]},
                "controller": {
                    "objects":
                        [{"command": "pcs status",
                          "to_file": "pcs_status.txt",
                          "type": "command"}],
                    "hosts":
                        [{"ssh-key": "/root/.ssh/id_rsa",
                          "hostname": "node-2",
                          "address": "10.109.2.5"},
                         {"ssh-key": "/root/.ssh/id_rsa",
                          "hostname": "node-1",
                          "address": "10.109.2.3"},
                         {"ssh-key": "/root/.ssh/id_rsa",
                          "hostname": "node-5",
                          "address": "10.109.2.4"}]},
            }
        }
        conf = Config(data)

        self.assertEqual({
            '10.109.2.5': [
                {'type': 'command',
                 'host': {'ssh-key': '/root/.ssh/id_rsa',
                          'hostname': 'node-5', 'address': '10.109.2.4'},
                 'to_file': 'pcs_status.txt', 'command': 'pcs status'}],
            '10.109.2.4': [
                {'type': 'command',
                 'host': {'ssh-key': '/root/.ssh/id_rsa',
                          'hostname': 'node-5', 'address': '10.109.2.4'},
                 'to_file': 'pcs_status.txt', 'command': 'pcs status'}],
            '10.109.2.3': [
                {'type': 'command',
                 'host': {'ssh-key': '/root/.ssh/id_rsa',
                          'hostname': 'node-5', 'address': '10.109.2.4'},
                 'to_file': 'pcs_status.txt', 'command': 'pcs status'}],
            '10.109.2.2': [
                {'path': '/etc/nailgun',
                 'host': {'ssh-key': '/root/.ssh/id_rsa',
                          'address': '10.109.2.2'},
                 'type': 'dir'},
                {'type': 'command',
                 'host': {'ssh-key': '/root/.ssh/id_rsa',
                          'address': '10.109.2.2'},
                 'to_file': 'uname_a.txt', 'command': 'uname -a'},
                {'type': 'command',
                 'host': {'ssh-key': '/root/.ssh/id_rsa',
                          'address': '10.109.2.2'},
                 'to_file': 'lsmod.txt', 'command': 'lsmod'},
                {'path': '/etc/*-release',
                 'host': {'ssh-key': '/root/.ssh/id_rsa',
                          'address': '10.109.2.2'},
                 'type': 'file'}]},
            conf.objects_per_host)
