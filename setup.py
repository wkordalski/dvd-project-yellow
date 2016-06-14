# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from codecs import open
from os import path

try:
    import py2exe
except ImportError:
    # py2exe command would not work...
    pass

here = path.abspath(path.dirname(__file__))

# Get the long description from the README.md file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='DvdYellow',
    version='0.0.1',
    description='A simple logic game made by Eryk Kopczyński',
    long_description=long_description,
    url='https://github.com/wojtex/dvd-project-yellow',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Programming Language :: Python :: 3',
    ],

    packages=['dvdyellow'],
    entry_points = {
        'console_scripts': [
            'dvdyellow-client = dvdyellow.client',
            'dvdyellow-server = dvdyellow.server'
        ]
    },
    test_suite='tests.load_tests',

    install_requires=['appdirs', 'sqlalchemy', 'pyyaml']
)
