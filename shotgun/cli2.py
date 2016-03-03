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
import yaml

from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.lister import Lister

import shotgun
from shotgun.config import Config
from shotgun.logger import configure_logger
from shotgun.manager import Manager


logger = logging.getLogger(__name__)


class Base(object):
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
        logger.info(u'Snapshot path: {0}'.format(snapshot_path))

    def run(self, parsed_args):
        """Overriden for returning errno from exceptions"""
        try:
            return super(SnapshotCommand, self).run(parsed_args)
        except Exception as err:
            logger.error(err)
            return getattr(err, 'errno', 1)


class ReportCommand(Lister, Base):

    columns = ['Host', 'Reporter', 'Report']

    def get_parser(self, prog_name):
        parser = super(ReportCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--config',
            default='/etc/shotgun/report.yaml',
            help='Path to report config file')
        parser.add_argument(
            'lines',
            action='store',
            nargs='?',
            default=3,
            help='Package info lines to show. If not set, default=3 is used')
        return parser

    def take_action(self, parsed_args):
        self.initialize_cmd(parsed_args)
        data = [line for line in self.manager.report(parsed_args)]
        return (self.columns, data)


def main(argv=None):
    configure_logger()
    return App(
        description="Shotgun CLI",
        version=shotgun.__version__,
        command_manager=CommandManager('shotgun')
    ).run(argv)
