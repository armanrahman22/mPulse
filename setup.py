#!/usr/bin/env python
import os
from setuptools import setup, find_packages

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

setup(
    name='mpulse',
    version='1.0',
    description='mpulse App',
    author='Arman Rahman',
    author_email='azrahman@mit.edu',
    url='http://django-mpulse.rhcloud.com/',
    include_package_data=True,
    install_requires=['Django==1.5.4',
                      'ecdsa==0.13',
                      'paramiko==1.15.2',
                      'pbr==0.10.7',
                      'Pillow==2.7.0',
                      'Pmw==2.0.0',
                      'preppy==2.3.3',
                      'psycopg2==2.6',
                      'pycrypto==2.6',
                      'pyRXP==2.1.0',
                      'reportlab==3.1.47',
                      'rlextra==3.1.47',
                      'six==1.9.0',
                      'stevedore==1.2.0',
                      'virtualenv==12.0.7',
                      'virtualenv-clone==0.2.5',
                      'virtualenvwrapper==4.3.2',
                      'virtualenvwrapper-powershell==12.7.8]'
    ])