# -*- coding: utf-8 -*-

# Copyright Noronha Development Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Noronha is a framework that helps you adopt
DataOps practices in Machine Learning projects
"""

import os
from setuptools import find_packages, setup
from distutils.dir_util import copy_tree


if os.environ.get('include_tests'):
    copy_tree('tests', 'noronha/resources/tests')
    copy_tree('examples', 'noronha/resources/examples')

setup(
    name='noronha-dataops',
    version='1.6.6',
    url='https://github.com/noronha-dataops/noronha',
    author='Noronha Development Team',
    author_email='noronha.mlops@everis.com',
    description='DataOps for Machine Learning',
    long_description=__doc__,
    zip_safe=False,
    platforms=['Unix'],
    license='Apache-2.0',
    install_requires=open('./requirements/{}_reqs.txt'.format(
        'on_board' if os.environ.get('AM_I_ON_BOARD') else 'off_board'
    )).read().split('\n'),
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    package_data={
        'noronha.resources': [
            'nha.yaml',
            'entrypoint.sh',
            'isle/*/*',
            'tests/*/*',
            'examples/*/*',
            'examples/*/*/*'
        ]
    },
    entry_points={
        'console_scripts': [
            '{alias}={entry_pont}'.format(alias=alias, entry_pont='noronha.cli.main:nha')
            for alias in ['noronha', 'nha']
        ],
        'papermill.engine': [
            'noronha_engine=noronha.tools.main:NoronhaEngine'
        ]
    },
    classifiers=[
        # As from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
    ]
)
