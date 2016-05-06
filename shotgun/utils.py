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
import errno
import logging
import os
import re
import socket
from StringIO import StringIO
import subprocess


logger = logging.getLogger(__name__)


def hostname():
    return socket.gethostname()


def is_ip(name):
    return (re.search(ur"([0-9]{1,3}\.){3}[0-9]{1,3}", name) and True)


def fqdn(name=None):
    if name:
        return socket.getfqdn(name)
    return socket.getfqdn(socket.gethostname())


def iterfiles(path):
    for root, dirnames, filenames in os.walk(path, topdown=True):
        for filename in filenames:
            yield os.path.join(root, filename)


def remove(full_dst_path, excludes):
    """Removes subdirs/files using unixs syntax

    full_dst_path is treated as root directory for remove

    :param full_dst_path: str
    :param excludes: list with excludes paths/files
    """
    for exclude in excludes:
        path = os.path.join(full_dst_path, exclude.lstrip('/'))
        logger.debug('Deleting %s', path)
        execute("shopt -s globstar; rm -rf {0}".format(path))


def is_out_of_space(code, errdata):
    if code:
        # Since compression command is actually a pipeline
        # we cannot use return code to detect out of space condition
        # so, the only way is to parse stderr
        return errdata.lower().find('no space left'.encode()) >= 0

def compress(target, level, keep_target=False, exclude=None):
    """Runs compression of provided directory

    :param target: directory to compress
    :param level: level of compression
    :param keep_target: bool, if True target directory wont be removed
    """
    if exclude is None:
        exclude = []

    env = copy.deepcopy(os.environ)
    env['XZ_OPT'] = level
    env['LANG'] = 'C' # We need non localized output
    code, _, errdata = execute(
        "tar chJf {0}.tar.xz -C {1} {2}{3}"
        "".format(target,
                  os.path.dirname(target),
                  os.path.basename(target),
                  "".join(' --exclude={}'.format(e) for e in exclude)),
        env=env)
    if not keep_target:
        execute("rm -r {0}".format(target))
    if is_out_of_space(code, errdata):
        raise IOError(errno.ENOSPC)


def execute(command, env=None):
    logger.debug("Trying to execute command: %s", command)

    env = env or os.environ
    env["PATH"] = "/bin:/usr/bin:/sbin:/usr/sbin"

    process = subprocess.Popen(
        command, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    return (process.poll(), stdout, stderr)


class CCStringIO(StringIO):
    """A "carbon copy" StringIO.

    It's capable of multiplexing its writes to other buffer objects.

    Taken from fabric.tests.mock_streams.CarbonCopy
    """

    def __init__(self, buffer='', writers=None):
        """CCStringIO initializator

        If ``writers`` is given and is a file-like object or an
        iterable of same, it/they will be written to whenever this
        StringIO instance is written to.
        """
        StringIO.__init__(self, buffer)
        if writers is None:
            writers = []
        elif hasattr(writers, 'write'):
            writers = [writers]
        self.writers = writers

    def write(self, s):
        # unfortunately, fabric writes into StringIO both so-called
        # bytestrings and unicode strings. obviously, bytestrings may
        # contain non-ascii symbols. that leads to type-conversion
        # issue when we use string's join (inside getvalue()) with
        # a list of both unicodes and bytestrings. in order to avoid
        # this issue we should convert all input unicode strings into
        # utf-8 bytestrings (let's assume that slaves encoding is utf-8
        # too so we won't have encoding mess in the output file).
        if isinstance(s, unicode):
            s = s.encode('utf-8')

        StringIO.write(self, s)
        for writer in self.writers:
            writer.write(s)
