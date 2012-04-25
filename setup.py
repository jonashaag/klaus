#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# this is a clever hack to circumvent distutil's data_files
# policy "install once, find never". Definitely a TODO!
# -- https://groups.google.com/group/comp.lang.python/msg/2105ee4d9e8042cb
from distutils.command.install import INSTALL_SCHEMES
for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

from distutils.core import setup
from os.path import join

templates = ['base.html', 'history.html', 'repo_list.html', 'skeleton.html',
             'tree.inc.html', 'view_blob.html', 'view_commit.html']
static = ['klaus.css', 'line-highlighter.js', 'pygments.css']

setup(
    name='klaus',
    version='1.0.1',
    author='Jonas Haag',
    author_email='jonas@lophus.org',
    packages=['klaus'],
    scripts=['bin/klaus'],
    data_files=[
        ('klaus/templates', [join('klaus/templates', path) for path in templates]),
        ('klaus/static', [join('klaus/static', path) for path in static])
    ],
    url='https://github.com/jonashaag/klaus',
    license='BSD style',
    description='The first Git web viewer that Just Works™.',
    long_description=__doc__,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
    ],
    install_requires=[
        'werkzeug',
        'Jinja2',
        'Pygments',
        'dulwich>=0.7.1'
    ],
)
