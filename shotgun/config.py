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

from collections import deque
import copy
import logging
import time

import six

from shotgun import settings


class Config(object):
    log = logging.getLogger(__name__)

    def __init__(self, data=None):
        self.data = data or {}
        self.time = time.localtime()
        self.offline_hosts = set()
        self.objs = deque()
        self.try_again = deque()
        for properties in six.itervalues(self.data.get('dump', {})):
            hosts = properties.get('hosts') or [{}]
            for obj in properties.get('objects', []):
                for h in hosts:
                    obj_new = copy.deepcopy(obj)
                    obj_new['host'] = h
                    self.objs.append(obj_new)

    def _timestamp(self, name):
        return "{0}-{1}".format(
            name,
            time.strftime('%Y-%m-%d_%H-%M-%S', self.time)
        )

    @property
    def target(self):
        target = self.data.get("target", settings.TARGET)
        if self.data.get("timestamp", settings.TIMESTAMP):
            target = self._timestamp(target)
        return target

    @property
    def compression_level(self):
        level = self.data.get("compression_level")
        if level is None:
            self.log.info(
                'Compression level is not specified,'
                ' Default %s will be used', settings.COMPRESSION_LEVEL)

        level = settings.COMPRESSION_LEVEL

        return '-{level}'.format(level=level)

    @property
    def lastdump(self):
        return self.data.get("lastdump", settings.LASTDUMP)

    @staticmethod
    def get_network_address(obj):
        """Returns network address of object."""
        return obj['host'].get('address') or obj['host'].get('hostname')

    def on_network_error(self, obj):
        """Lets the object to have another attempt for being proccessed."""
        host = self.get_network_address(obj)
        self.log.debug("Remote host %s is unreachable. "
                       "Processing of its objects postponed.", host)
        self.try_again.append(obj)
        self.offline_hosts.add(host)

    @property
    def objects(self):
        """Stateful generator for processing objects.

        It should be used in conjunction with on_network_error() to give
        another try for objects which threw NetworkError.
        """
        for _ in range(settings.ATTEMPTS):
            while self.objs:
                obj = self.objs.popleft()
                if self.get_network_address(obj) not in self.offline_hosts:
                    yield obj
                else:
                    self.try_again.append(obj)
            self.offline_hosts.clear()
            self.objs, self.try_again = self.try_again, deque()

        for obj in self.objs:
            obj["type"] = 'offline'
            host = self.get_network_address(obj)
            if host not in self.offline_hosts:
                self.offline_hosts.add(host)
                yield obj
            else:
                self.log.debug("Skipping offline object processing: %s", obj)

    @property
    def timeout(self):
        """Timeout for executing commands."""
        return self.data.get("timeout", settings.DEFAULT_TIMEOUT)

    @property
    def self_log_object(self):
        return {
            "type": "file",
            "path": settings.LOG_FILE
        }
