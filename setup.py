#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 15:14:39 2025

@author: mitchell
"""

from setuptools import setup, find_packages

setup(
    name="amihgosapp",
    version="0.1.0",
    description="AMIHGOS Helmet Segmentation and Processing Tool",
    author="Mitchell", 
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "SimpleITK",
        "pyvista",
        "PyQt5",
        # Add other dependencies as needed
    ],
    entry_points={
        'console_scripts': [
            'amihgos=scripts.run_amihgos:main',
        ],
    },
)