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
resources_path = os.path.join('amihgosapp','resources')

def get_image_path(image_name):
    """Get absolute path to an image resource"""
    return os.path.join(_PROJECT_ROOT, resources_path,'images', image_name)

def get_template_path(template_name):
    """Get absolute path to a template resource"""
    if template_name is not None:
        return os.path.join(_PROJECT_ROOT, resources_path, 'templates', template_name)
    
    else:
        return os.path.join(_PROJECT_ROOT, resources_path, 'templates')

def get_ct_path(ct_name):
    """Get absolute path to a CT resource"""
    return os.path.join(_PROJECT_ROOT, resources_path, 'ct_files', ct_name)

def get_output_path(filename):
    """Get absolute path for an output file"""
    output_dir = os.path.join(_PROJECT_ROOT, resources_path, 'head_stls')
    return os.path.join(output_dir, filename)