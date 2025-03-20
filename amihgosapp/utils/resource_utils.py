#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 19 10:50:30 2025

@author: mitchell with help of ClaudeAI
"""

# amighosapp/utils/resource_utils.py
import os

# Base paths
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_image_path(image_name):
    """Get absolute path to an image resource"""
    return os.path.join(_PROJECT_ROOT, 'images', image_name)

def get_template_path(template_name):
    """Get absolute path to a template resource"""
    return os.path.join(_PROJECT_ROOT, 'templates', template_name)

def get_output_path(filename, subdir='head_stls'):
    """Get absolute path for an output file"""
    output_dir = os.path.join(_PROJECT_ROOT, subdir)
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)