#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from wotpy.__version__ import __version__
from wotpy.protocols.support import is_coap_supported, is_mqtt_supported
from wotpy.wot.discovery.support import is_dnssd_supported

install_requires = [
    'tornado>=5.1,<6.0',
    'jsonschema>=2.0,<3.0',
    'six>=1.10.0,<2.0',
    'rx>=1.6.0,<2.0',
    'python-slugify>=1.2.4,<2.0'
]

test_requires = [
    'pytest>=3.6.1,<4.0.0',
    'pytest-cov>=2.5.1,<3.0.0',
    'pytest-rerunfailures>=4.1,<5.0',
    'mock>=2.0,<3.0',
    'tox>=2.0,<3.0',
    'faker>=0.8.15,<0.9',
    'Sphinx>=1.7.5,<2.0.0',
    'sphinx-rtd-theme>=0.4.0,<0.5.0',
    'futures>=3.1.1,<4.0.0',
    'pyOpenSSL>=18.0.0,<19.0.0'
]

if is_coap_supported():
    install_requires.append('aiocoap>=0.3.0,<1.0')
    install_requires.append('LinkHeader>=0.4.3,<1.0')

if is_mqtt_supported():
    install_requires.append('hbmqtt>=0.9.4,<1.0')

if is_dnssd_supported():
    install_requires.append('zeroconf>=0.21.3,<0.22.0')
    test_requires.append('aiozeroconf==0.1.8')

setup(
    name='wotpy',
    version=__version__,
    description='Python implementation of the W3C WoT Scripting API',
    keywords='wot w3c ctic iot',
    author='Andres Garcia Mangas',
    author_email='andres.garcia@fundacionctic.org',
    url='https://bitbucket.org/fundacionctic/wot-py',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        'tests': test_requires
    }
)
