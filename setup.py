#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from distutils.core import setup

setup(
    name='klaus',
    version='1.0.0',
    author='Jonas Haag',
    author_email='jonas@lophus.org',
    packages=['klaus', 'klaus/templates', 'klaus/static'],
    scripts=['bin/klaus'],
    package_data={
        'klaus': ['templates/*.html', 'static/*']
    },
    url='https://github.com/jonashaag/klaus',
    license='BSD style',
    description='The first Git web viewer that Just Works™.',
    long_description=__doc__,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
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
