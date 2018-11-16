#!/usr/bin/env python

"""Setup configuration."""

from setuptools import setup, find_packages

setup(
    name='pynoc',
    version='1.6.3',

    description='Network Operation Center gear',
    long_description='Python package to handle interact with various '
                     'network operation center gear. This includes: network '
                     'switches, power distribution units, and such.',
    url='http://github.com/SimplicityGuy/pynoc',

    author='Robert Wlodarczyk',
    author_email='robert@simplicityguy.com',

    license='Apache License 2.0',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Hardware',
        'Topic :: System :: Networking',
    ],

    keywords=[
        'instrument',
        'switch',
        'pdu',
        'Cisco',
        'APC',
        'network gear',
    ],

    packages=find_packages(exclude=['contrib', 'docs', 'test*']),

    install_requires=[
        'pysnmp',
        'netaddr',
        'netmiko',
        'retrying',
    ],

    test_suite='nose.collector',

    tests_require=[
        'nose',
        'nosexcover',
    ],
)
