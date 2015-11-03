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

import logging
import os

import fabric.exceptions

from shotgun.driver import Driver
from shotgun import utils


logger = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, conf):
        logger.debug("Initializing snapshot manager")
        self.conf = conf

    def snapshot(self):
        logger.debug("Making snapshot")
        utils.execute("rm -rf {0}".format(os.path.dirname(self.conf.target)))
        postponed_objects = []
        offline_hosts = []

        def _snapshot_objects(objects, host, offline_hosts):
            postponed_objects = []
            for obj in objects:
                if host in offline_hosts:
                    postponed_objects.append(obj)
                    logger.debug("Host %s looks offline. Postponing "
                                 "object %s", host, obj)
                    continue
                logger.debug("Dumping: %s", obj)
                driver = Driver.getDriver(obj, self.conf)
                try:
                    driver.snapshot()
                except fabric.exceptions.NetworkError:
                    logger.debug("Remote host %s is unreachable. "
                                 "Processing of its objects postponed.", host)
                    if host not in offline_hosts:
                        offline_hosts.append(host)
            return postponed_objects

        for host, objects in self.conf.objects_per_host.iteritems():
            postponed_objects.extend(_snapshot_objects(objects, host,
                                                       offline_hosts))
        logger.debug("Trying to dump postponed objects")
        offline_hosts = []
        unproccessed_objects = []
        for obj in postponed_objects:
            unproccessed_objects.extend(_snapshot_objects([obj], obj["host"],
                                                          offline_hosts))
        for obj in unproccessed_objects:
            obj['type'] = 'offline'
            _snapshot_objects([obj], obj["host"], [])
        logger.debug("Archiving dump directory: %s", self.conf.target)

        utils.compress(self.conf.target, self.conf.compression_level)

        with open(self.conf.lastdump, "w") as fo:
            fo.write("{0}.tar.xz".format(self.conf.target))
        return "{0}.tar.xz".format(self.conf.target)
