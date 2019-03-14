#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2019 Devon (Gorialis) R

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import pathlib
import re
import subprocess

from setuptools import setup

ROOT = pathlib.Path(__file__).parent

with open(ROOT / 'requirements' / 'pypi.txt', 'r', encoding='utf-8') as f:
    REQUIREMENTS = f.read().splitlines()

with open(ROOT / 'jishaku' / 'meta.py', 'r', encoding='utf-8') as f:
    VERSION = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

if not VERSION:
    raise RuntimeError('version is not set')


try:
    PROCESS = subprocess.Popen(
        ['git', 'rev-list', '--count', 'HEAD'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    COMMIT_COUNT, ERR = PROCESS.communicate()

    if COMMIT_COUNT:
        PROCESS = subprocess.Popen(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        COMMIT_HASH, ERR = PROCESS.communicate()

        if COMMIT_HASH:
            if VERSION.endswith(('a', 'b', 'rc')):
                VERSION += COMMIT_COUNT.decode('utf-8').strip() + '+' + COMMIT_HASH.decode('utf-8').strip()
            else:
                VERSION += '.' + COMMIT_COUNT.decode('utf-8').strip()

except FileNotFoundError:
    pass


with open(ROOT / 'README.rst', 'r', encoding='utf-8') as f:
    README = f.read()


setup(
    name='jishaku',
    author='Devon (Gorialis) R',
    url='https://github.com/Gorialis/jishaku',

    license='MIT',
    description='A discord.py extension including useful tools for bot development and debugging.',
    long_description=README,
    long_description_content_type='text/x-rst',
    project_urls={
        'Documentation': 'https://jishaku.readthedocs.io/en/latest/',
        'Code': 'https://github.com/Gorialis/jishaku',
        'Issue tracker': 'https://github.com/Gorialis/jishaku/issues'
    },

    version=VERSION,
    packages=['jishaku', 'jishaku.repl'],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    python_requires='>=3.6.0',

    extras_require={
        'docs': [
            'sphinx>=1.7.0',
            'sphinxcontrib-asyncio'
        ],

        'test': [
            'coverage',
            'flake8',
            'isort',
            'pylint',
            'pytest',
            'pytest-cov'
        ],

        'voice': [
            'PyNaCl',
            'youtube-dl'
        ],

        'procinfo': [
            'psutil'
        ]
    },

    download_url='https://github.com/Gorialis/jishaku/archive/{}.tar.gz'.format(VERSION),

    keywords='jishaku discord.py discord cog repl extension',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Communications :: Chat',
        'Topic :: Internet',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities'
    ]
)
