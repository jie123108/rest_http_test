#!/usr/bin/env python
from __future__ import with_statement

import os
import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


IS_PYPY = hasattr(sys, 'pypy_translation_info')
VERSION = '0.1.1'
DESCRIPTION = "rest_http_test is a data-driven test framework for testing restful services. is implementation by python."

with open('README.md', 'r') as f:
   LONG_DESCRIPTION = f.read()
 
if sys.argv[-1] == 'publish':
    os.system("python setup.py sdist upload")
    os.system("python setup.py bdist_wheel upload")
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (VERSION, VERSION))
    print("  git push --tags")
    sys.exit()


if sys.argv[-1] == 'test':
    test_requirements = [
        'flask',
        'dotmap',
    ]
    try:
        modules = map(__import__, test_requirements)
    except ImportError as e:
        err_msg = e.message.replace("No module named ", "")
        msg = "%s is not installed. Install your test requirments." % err_msg
        raise ImportError(msg)
    os.system('python PyTestMain.py')
    sys.exit()

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


