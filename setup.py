#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2018 Devon (Gorialis) R

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

import re

from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('jishaku/meta.py') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('version is not set')


if version.endswith(('a', 'b', 'rc')):
    try:
        import subprocess

        p = subprocess.Popen(['git', 'rev-list', '--count', 'HEAD'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        commit_count, err = p.communicate()

        if commit_count:
            p = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            commit_hash, err = p.communicate()

            if commit_hash:
                version += commit_count.decode('utf-8').strip() + '+' + commit_hash.decode('utf-8').strip()
    except Exception:
        pass


with open('README.rst') as f:
    readme = f.read()


setup(name='jishaku',
      author='Gorialis',
      url='https://github.com/Gorialis/jishaku',
      download_url='https://github.com/Gorialis/jishaku/archive/{}.tar.gz'.format(version),
      version=version,
      packages=['jishaku', 'jishaku.repl'],
      license='MIT',
      description='A discord.py extension including useful tools for bot development and debugging.',
      long_description=readme,
      include_package_data=True,
      install_requires=requirements,
      python_requires='>=3.6.0',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Framework :: AsyncIO',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Communications :: Chat',
          'Topic :: Internet',
          'Topic :: Software Development :: Debuggers',
          'Topic :: Software Development :: Testing',
          'Topic :: Utilities'
      ])
