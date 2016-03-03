# -*- coding: utf-8 -*-

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
import logging
import re
import yaml

from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.lister import Lister

import shotgun
from shotgun.config import Config
from shotgun.manager import Manager


class Base(object):
    log = logging.getLogger(__name__)

    def initialize_cmd(self, parsed_args):
        with open(parsed_args.config, "r") as f:
            self.config = Config(yaml.safe_load(f))
        self.manager = Manager(self.config)


class SnapshotCommand(Command, Base):

    def get_parser(self, prog_name):
        parser = super(SnapshotCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--config',
            required=True,
            help='Path to snapshot config file')
        return parser

    def take_action(self, parsed_args):
        """Generates snapshot

        :param parsed_args: argparse object
        """
        self.initialize_cmd(parsed_args)
        snapshot_path = self.manager.snapshot()
        self.log.info(u'Snapshot path: {0}'.format(snapshot_path))

    def run(self, parsed_args):
        """Overriden for returning errno from exceptions"""
        try:
            return super(SnapshotCommand, self).run(parsed_args)
        except Exception as err:
            self.log.error(err)
            return getattr(err, 'errno', 1)


class ReportCommand(Lister, Base):
    columns = ['Info']
    formatter_default = 'value'

    def get_parser(self, prog_name):
        parser = super(ReportCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--config',
            default='/etc/shotgun/report.yaml',
            help='Path to report config file')
        parser.add_argument(
            '--short', '-s',
            action='store_true',
            default=False,
            help='Shows only package name, without git log')
        return parser

    def take_action(self, parsed_args):
        def _filter_data(x):
            regexp = re.compile(
                r'^(?!\-|\*)fuel|astute|network-checker|shotgun')---
            return regexp.search(x[0])
        self.initialize_cmd(parsed_args)
        raw = self.manager.report()
        data = [line[2:3] for line in raw]
        if parsed_args.short:
            data = filter(_filter_data, data)
            data.insert(4, ('',))
        return self.columns, data


def main(argv=None):
    return App(
        description="Shotgun CLI",
        version=shotgun.__version__,
        command_manager=CommandManager('shotgun')
    ).run(argv)
