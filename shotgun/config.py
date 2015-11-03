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
import logging
import time

from shotgun import settings


logger = logging.getLogger(__name__)


class Config(object):
    def __init__(self, data=None):
        self.data = data
        self.time = time.localtime()
        self.offline_hosts = set()
        self.objs = deque()
        for properties in self.data.get("dump", {}).itervalues():
            for host in properties.get("hosts", []):
                for object_ in properties.get("objects", []):
                    object_["host"] = host
                    object_["attempts"] = settings.ATTEMPTS
                    self.objs.append(object_)
        # sentinel used to indicate the end of iteration over the
        # objects
        self.sentinel = 'END'
        self.objs.append(self.sentinel)

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
            logger.info(
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
        # XXX: address or hostname?
        return obj["host"].get('address', '127.0.0.1')

    def on_network_error(self, obj):
        """Lets the object to have another attempt for being proccessed."""
        host = self.get_network_address(obj)
        logger.debug("Remote host %s is unreachable. "
                     "Processing of its objects postponed.", host)
        # Convert to 'offline' object once all attempts exhausted
        obj["attempts"] -= 1
        if not obj["attempts"]:
            obj['type'] = 'offline'
        self.objs.append(obj)
        self.offline_hosts.add(host)

    @property
    def objects(self):
        """Stateful generator for processing objects.

        It should be used in conjunction with on_network_error() to give
        another try for objects which threw NetworkError.
        """
        while self.objs:
            obj = self.objs.popleft()
            if obj is self.sentinel:
                if not self.objs:
                    return
                # Emptying offline hosts in order to perform more attempts to
                # yield objects. That will allow to postpone processing of
                # objects to the next iteration rather than having to spend
                # multiple retries in a serie for a particular object.
                self.offline_hosts.clear()
                self.objs.append(self.sentinel)
            else:
                if self.get_network_address(obj) not in self.offline_hosts or \
                        obj['type'] == 'offline':
                    yield obj
                else:
                    self.on_network_error(obj)

    @property
    def timeout(self):
        """Timeout for executing commands."""
        return self.data.get("timeout", settings.DEFAULT_TIMEOUT)
