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
import pprint
import pwd
import re
import stat
import sys
import xmlrpclib

import fabric.api

from shotgun import utils


logger = logging.getLogger(__name__)


class CommandOut(object):
    stdout = None
    return_code = None
    stderr = None

    def __eq__(self, other):
        return (
            str(self.stdout) == str(other.stdout) and
            str(self.stderr) == str(other.stderr) and
            str(self.return_code) == str(other.return_code)
        )


class Driver(object):

    @classmethod
    def getDriver(cls, data, conf):
        driver_type = data["type"]
        return {
            "file": File,
            "dir": Dir,
            "postgres": Postgres,
            "xmlrpc": XmlRpc,
            "command": Command,
        }.get(driver_type, cls)(data, conf)

    def __init__(self, data, conf):
        logger.debug("Initializing driver %s: host=%s",
                     self.__class__.__name__, data.get("host"))
        self.data = data
        self.host = self.data.get("host", {}).get("hostname")
        self.addr = self.data.get("host", {}).get("address")
        self.ssh_key = self.data.get("host", {}).get("ssh-key")

        # Indicates whether a command should be executed on remote
        # machine. By default it will be executed on local host
        self.remote = bool(self.addr)

        self.conf = conf
        self.timeout = self.data.get("timeout", self.conf.timeout)

    def snapshot(self):
        raise NotImplementedError

    def command(self, command):
        out = CommandOut()

        raw_stdout = utils.CCStringIO(writers=sys.stdout)
        try:
            if self.remote:
                with fabric.api.settings(
                    host_string=self.addr,      # destination host
                    key_filename=self.ssh_key,  # a path to ssh key
                    timeout=2,                  # a network connection timeout
                    command_timeout=self.timeout,  # command execution timeout
                    warn_only=True,             # don't exit on error
                    abort_on_prompts=True,      # non-interactive mode
                ):
                    logger.debug("Running remote command: "
                                 "host: %s command: %s", self.host, command)
                    try:
                        output = fabric.api.run(command, stdout=raw_stdout)
                    except SystemExit:
                        logger.error("Fabric aborted this iteration")
                    # NOTE(prmtl): because of pty=True (default) and
                    # combine_stderr=True (default) stderr is combined
                    # with stdout
                    out.stdout = raw_stdout.getvalue()
                    out.return_code = output.return_code
            else:
                logger.debug("Running local command: %s", command)
                out.return_code, out.stdout, out.stderr = utils.execute(
                    command)
        except Exception as e:
            logger.error("Error occured: %s", str(e))
            out.stdout = raw_stdout.getvalue()
        return out

    def get(self, path, target_path):
        """Get remote or local file

        target_path must be the directory where to put
        copied files or directories
        """
        try:
            if self.remote:
                with fabric.api.settings(
                    host_string=self.addr,      # destination host
                    key_filename=self.ssh_key,  # a path to ssh key
                    timeout=2,                  # a network connection timeout
                    warn_only=True,             # don't exit on error
                    abort_on_prompts=True,      # non-interactive mode
                ):
                    logger.debug("Getting remote file: %s %s",
                                 path, target_path)
                    utils.execute('mkdir -p "{0}"'.format(target_path))
                    try:
                        return fabric.api.get(path, target_path)
                    except SystemExit:
                        logger.error("Fabric aborted this iteration")
            else:
                logger.debug("Getting local file: cp -r %s %s",
                             path, target_path)
                utils.execute('mkdir -p "{0}"'.format(target_path))
                return utils.execute('cp -r "{0}" "{1}"'.format(path,
                                                                target_path))
        except Exception as e:
            logger.error("Error occured: %s", str(e))


class File(Driver):
    def __init__(self, data, conf):
        super(File, self).__init__(data, conf)
        self.path = self.data["path"]
        self.exclude = self.data.get('exclude', [])
        logger.debug("File to get: %s", self.path)
        self.target_path = str(os.path.join(
            self.conf.target, self.host,
            os.path.dirname(self.path).lstrip("/")))
        self.full_dst_path = os.path.join(
            self.conf.target, self.host,
            self.path.lstrip("/"))
        logger.debug("File to save: %s", self.target_path)

    def snapshot(self):
        """Make a snapshot

        Example:
        self.conf.target IS /target
        self.host IS host.domain.tld
        self.path IS /var/log/somedir
        self.target_path IS /target/host.domain.tld/var/log
        """
        self.get(self.path, self.target_path)

        if self.exclude:
            utils.remove(self.full_dst_path, self.exclude)

Dir = File


class Postgres(Driver):
    def __init__(self, data, conf):
        super(Postgres, self).__init__(data, conf)
        self.dbhost = self.data.get("dbhost", "localhost")
        self.dbname = self.data["dbname"]
        self.username = self.data.get("username", "postgres")
        self.password = self.data.get("password")
        self.target_path = str(os.path.join(self.conf.target,
                               self.host, "pg_dump"))

    def snapshot(self):
        if self.password:
            authline = "{host}:{port}:{dbname}:{username}:{password}".format(
                host=self.dbhost, port="5432", dbname=self.dbname,
                username=self.username, password=self.password)
            home_dir = pwd.getpwuid(os.getuid()).pw_dir
            pgpass = os.path.join(home_dir, ".pgpass")
            with open(pgpass, "a+") as fo:
                fo.seek(0)
                auth = False
                for line in fo:
                    if re.search(ur"^{0}$".format(authline), line):
                        auth = True
                        break
                if not auth:
                    fo.seek(0, 2)
                    fo.write("{0}\n".format(authline))
            os.chmod(pgpass, stat.S_IRUSR + stat.S_IWUSR)
        temp = self.command("mktemp").stdout.strip()
        self.command("pg_dump -h {dbhost} -U {username} -w "
                     "-f {file} {dbname}".format(
                         dbhost=self.dbhost, username=self.username,
                         file=temp, dbname=self.dbname))
        utils.execute('mkdir -p "{0}"'.format(self.target_path))
        dump_basename = "{0}_{1}.sql".format(self.dbhost, self.dbname)

        utils.execute('mv -f "{0}" "{1}"'.format(
            temp,
            os.path.join(self.target_path, dump_basename)))


class XmlRpc(Driver):
    def __init__(self, data, conf):
        super(XmlRpc, self).__init__(data, conf)

        self.server = self.data.get("server", "localhost")
        self.methods = self.data.get("methods", [])
        self.to_file = self.data.get("to_file")

        self.target_path = os.path.join(
            self.conf.target, self.host, "xmlrpc", self.to_file)

    def snapshot(self):
        utils.execute('mkdir -p "{0}"'.format(os.path.dirname(
            self.target_path)))

        server = xmlrpclib.Server(self.server)
        with open(self.target_path, "w") as f:
            for method in self.methods:
                if hasattr(server, method):
                    response = getattr(server, method)()
                    response = pprint.pformat(response, indent=2)
                else:
                    response = "no such method on remote server"

                f.write("===== {0} =====\n{1}\n\n".format(method, response))


class Command(Driver):

    def __init__(self, data, conf):
        super(Command, self).__init__(data, conf)
        self.cmdname = self.data["command"]
        self.to_file = self.data["to_file"]
        self.target_path = os.path.join(
            self.conf.target, self.host, "commands", self.to_file)

    def snapshot(self):
        out = self.command(self.cmdname)
        utils.execute('mkdir -p "{0}"'.format(os.path.dirname(
            self.target_path)))
        with open(self.target_path, "w") as f:
            f.write("===== COMMAND =====: {0}\n".format(self.cmdname))
            f.write("===== RETURN CODE =====: {0}\n".format(out.return_code))
            f.write("===== STDOUT =====:\n")
            if out.stdout:
                f.write(out.stdout)
            f.write("\n===== STDERR =====:\n")
            if out.stderr:
                f.write(out.stderr)
