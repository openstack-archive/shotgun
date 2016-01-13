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
        excludes = []
        for obj_data in self.conf.objects:
            logger.debug("Dumping: %s", obj_data)
            self.action_single(obj_data, action='snapshot')
            if 'exclude' in obj_data:
                excludes.extend(os.path.join(obj_data['path'], ex)
                                for ex in obj_data['exclude'])

        logger.debug("Dumping shotgun log and archiving dump directory: %s",
                     self.conf.target)
        self.action_single(self.conf.self_log_object, action='snapshot')

        utils.compress(self.conf.target, self.conf.compression_level, excludes)

        with open(self.conf.lastdump, "w") as fo:
            fo.write("{0}.tar.xz".format(self.conf.target))
        return "{0}.tar.xz".format(self.conf.target)

    def action_single(self, object, action='snapshot'):
        driver = Driver.getDriver(object, self.conf)
        try:
            return getattr(driver, action)()
        except fabric.exceptions.NetworkError:
            self.conf.on_network_error(object)

    def report(self):
        logger.debug("Making report")
        for obj_data in self.conf.objects:
            logger.debug("Gathering report for: %s", obj_data)
            for report in self.action_single(obj_data, action='report'):
                yield report
