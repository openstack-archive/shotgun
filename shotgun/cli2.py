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


class ReportCommand(Lister, Base):

    columns = ['Host', 'Reporter', 'Report']

    def get_parser(self, prog_name):
        parser = super(ReportCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--config',
            default='/etc/shotgun/report.yaml',
            help='Path to report config file')
        return parser

    def take_action(self, parsed_args):
        self.initialize_cmd(parsed_args)
        data = [line for line in self.manager.report()]
        return (self.columns, data)


class ShotgunApp(App):
    def run(self, argv):
        """Equivalent to the main program for the application.

        This method is copied from cliff app.py with added handling of
        EnvironmentError to make Shotgun return error codes other than 1.

        :param argv: input arguments and options
        :paramtype argv: list of str
        """
        try:
            self.options, remainder = self.parser.parse_known_args(argv)
            self.configure_logging()
            self.interactive_mode = not remainder
            if self.deferred_help and self.options.deferred_help and remainder:
                self.options.deferred_help = False
                remainder.insert(0, "help")
                self.initialize_app(remainder)
                self.print_help_if_requested()
        except Exception as err:
            if hasattr(self, 'options'):
                debug = self.options.debug
            else:
                debug = True
                if debug:
                    self.LOG.exception(err)
                    raise
                else:
                    self.LOG.error(err)
                    # Note: This line differs from original run implementation
                    return getattr(err, 'errno', 1)
        result = 1
        if self.interactive_mode:
            result = self.interact()
        else:
            result = self.run_subcommand(remainder)
            return result


def main(argv=None):
    configure_logger()
    return ShotgunApp(
        description="Shotgun CLI",
        version=shotgun.__version__,
        command_manager=CommandManager('shotgun')
    ).run(argv)
