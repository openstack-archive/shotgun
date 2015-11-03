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

import copy
import logging
import time

from shotgun import settings


logger = logging.getLogger(__name__)


class Config(object):
    def __init__(self, data=None):
        self.data = data
        self.time = time.localtime()
        self.offline_hosts = []
        self.objs = []
        for role, properties in self.data.get("dump", {}).iteritems():
            for host in properties.get("hosts", []):
                for object_ in properties.get("objects", []):
                    object_["host"] = host
                    object_["attempts"] = 2
                    self.objs.append(object_)

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

    def get_address_from_obj(self, obj):
        # XXX: address or hostname?
        return obj["host"].get('address', '127.0.0.1')

    def postpone_obj(self, obj):
        host = self.get_address_from_obj(obj)
        logger.debug("Remote host %s is unreachable. "
                     "Processing of its objects postponed.", host)
        self.offline_hosts.append(host)
        self.objs.append(obj)
        obj["attempts"] -= 1

    @property
    def objects(self):
        while self.objs:
            for obj in copy.deepcopy(self.objs):
                host = self.get_address_from_obj(obj)
                if host not in self.offline_hosts:
                    self.objs.remove(obj)
                    if not obj["attempts"]:
                        obj['type'] = 'offline'
                    yield obj
            self.offline_hosts = []

    @property
    def timeout(self):
        """Timeout for executing commands."""
        return self.data.get("timeout", settings.DEFAULT_TIMEOUT)
