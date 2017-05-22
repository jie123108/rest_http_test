#!/usr/bin/env python
from __future__ import with_statement

import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


IS_PYPY = hasattr(sys, 'pypy_translation_info')
VERSION = '0.1.0'
DESCRIPTION = "rest_http_test is a data-driven test framework for testing restful services. is implementation by python."

with open('README.rst', 'r') as f:
   LONG_DESCRIPTION = f.read()



setup(
    name="rest_http_test",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    # classifiers=CLASSIFIERS,
    author="jie123108",
    author_email="jie123108@163.com",
    url="https://github.com/jie123108/rest_http_test",
    license="LGPL",
    packages=['rest_http_test'],
    platforms=['any'],
    # scripts = ['say_hello.py'],
    install_requires = ['dotmap', 'jsonschema'],
)


