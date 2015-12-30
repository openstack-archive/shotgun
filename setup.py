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

import setuptools


setuptools.setup(
    name='shotgun',
    version='9.0.0',
    description='Shotgun package',
    long_description='Shotgun is diagnostic snapshot generator',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python'],
    author='Mirantis Inc.',
    author_email='product@mirantis.com',
    url='http://mirantis.com',
    keywords='shotgun mirantis',
    packages=setuptools.find_packages(),
    zip_safe=False,
    install_requires=[
        'Fabric >= 1.10.0'],
    entry_points={
        'console_scripts': [
            'shotgun = shotgun.cli:main',
            'shotgun2 = shotgun.cli2:main'],
        'shotgun': [
            'snapshot = shotgun.cli2:SnapshotCommand',
            'report = shotgun.cli2:ReportCommand']
    })
