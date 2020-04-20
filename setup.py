#!/usr/bin/env python
from setuptools import setup

with open("README.md") as fh:
    LONG_DESCRIPTION = fh.read()

setup(
    name='blm_header',
    url='https://github.com/loiccoyle/blm_header',
    description='Bruteforce the LHC\'s BLM header.',
    long_description=LONG_DESCRIPTION,
    author='Loic Coyle',
    author_email='loic.thomas.coyle@cern.ch',
    packages=['blm_header'],
    install_requires=['numpy', 'pandas', 'pytimber'],
    python_requires='>=3.6',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
    ],
)

__author__ = 'Loic Coyle'
