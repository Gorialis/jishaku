
from setuptools import setup

import re


with open('requirements.txt') as f:
    requirements = f.read().splitlines()


with open('jishaku/__init__.py') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)


if not version:
    raise RuntimeError('version is not set')


with open('README.rst') as f:
    readme = f.read()


setup(name='jishaku',
      author='Gorialis',
      url='https://github.com/Gorialis/jishaku',
      download_url='https://github.com/Gorialis/jishaku/archive/0.0.4.tar.gz',
      version=version,
      packages=['jishaku'],
      license='MIT',
      description='A debugging and testing cog for discord.py rewrite',
      long_description=readme,
      include_package_data=True,
      install_requires=requirements,
      python_requires='>=3.6.0',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet',
        'Topic :: Utilities',
      ]
)
