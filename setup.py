#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2021 Devon (Gorialis) R

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

import os
import pathlib
import re
import subprocess
import typing

from setuptools import setup

ROOT = pathlib.Path(__file__).parent

with open(ROOT / 'jishaku' / 'meta.py', 'r', encoding='utf-8') as f:
    VERSION_MATCH = re.search(r'VersionInfo\(major=(\d+), minor=(\d+), micro=(\d+), .+\)', f.read(), re.MULTILINE)

    if not VERSION_MATCH:
        raise RuntimeError('version is not set or could not be located')

    version = '.'.join([VERSION_MATCH.group(1), VERSION_MATCH.group(2), VERSION_MATCH.group(3)])

EXTRA_REQUIRES: typing.Dict[str, typing.List[str]] = {}

for feature in (ROOT / 'requirements').glob('*.txt'):
    with open(feature, 'r', encoding='utf-8') as f:
        EXTRA_REQUIRES[feature.with_suffix('').name] = f.read().splitlines()

REQUIREMENTS = EXTRA_REQUIRES.pop('_')

if not version:
    raise RuntimeError('version is not set')


try:
    process = subprocess.Popen(
        ['git', 'rev-list', '--count', 'HEAD'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    COMMIT_COUNT, err = process.communicate()

    if COMMIT_COUNT:
        process = subprocess.Popen(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        COMMIT_HASH, err = process.communicate()

        if COMMIT_HASH:
            match = re.match(r'(\d).(\d).(\d)(a|b|rc)?', os.getenv('tag_name') or "")

            if (match and match[4]) or not match:
                version += ('' if match else 'a') + COMMIT_COUNT.decode('utf-8').strip() + '+g' + COMMIT_HASH.decode('utf-8').strip()

                # Also attempt to retrieve a branch, when applicable
                process = subprocess.Popen(
                    ['git', 'symbolic-ref', '-q', '--short', 'HEAD'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                COMMIT_BRANCH, err = process.communicate()

                if COMMIT_BRANCH:
                    version += "." + re.sub('[^a-zA-Z0-9.]', '.', COMMIT_BRANCH.decode('utf-8').strip())

except FileNotFoundError:
    pass


with open(ROOT / 'README.md', 'r', encoding='utf-8') as f:
    README = f.read()


setup(
    name='jishaku',
    author='Devon (Gorialis) R',
    url='https://github.com/Gorialis/jishaku',

    license='MIT',
    description='A discord.py extension including useful tools for bot development and debugging.',
    long_description=README,
    long_description_content_type='text/markdown',
    project_urls={
        'Documentation': 'https://jishaku.readthedocs.io/en/latest/',
        'Code': 'https://github.com/Gorialis/jishaku',
        'Issue tracker': 'https://github.com/Gorialis/jishaku/issues'
    },

    version=version,
    packages=['jishaku', 'jishaku.features', 'jishaku.repl'],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    python_requires='>=3.10.0',

    extras_require=EXTRA_REQUIRES,
    entry_points={
        'console_scripts': [
            'jishaku = jishaku.__main__:entrypoint',
        ],
    },

    download_url=f'https://github.com/Gorialis/jishaku/archive/{version}.tar.gz',

    keywords='jishaku discord.py discord cog repl extension',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Communications :: Chat',
        'Topic :: Internet',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities'
    ]
)
