# -*- coding: utf-8 -*-
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
    version='1.1.0',
    url='https://github.com/athosgvag/noronha-dataops',
    author='Gustavo Vargas Castilhos',
    author_email='gvargasc@everis.com',
    description='DataOps for Machine Learning',
    long_description=__doc__,
    zip_safe=False,
    platforms='any',
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
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
    ]
)
