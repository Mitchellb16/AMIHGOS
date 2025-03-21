#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compatibility layer for the sitk2vtk module.
This allows existing code to continue using the old import path.
"""
import warnings

# Import the function from its new location
from amihgosapp.utils.sitk_utils import sitk2vtk

# Add a deprecation warning
warnings.warn(
    "The 'utils.sitk2vtk' module is deprecated. Please use 'amihgosapp.utils.sitk_utils' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Other functions can be added here as needed
