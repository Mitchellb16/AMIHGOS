#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for sitk2vtk conversion utility
Created by Mitchell Bishop using Claude AI
"""
import os
import sys
import SimpleITK as sitk
import vtk
import numpy as np

# Ensure we can find both old and new module paths
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import both versions of the function to test
from utils.sitk2vtk import sitk2vtk as old_sitk2vtk
from amihgosapp.utils.sitk_utils import sitk2vtk as new_sitk2vtk

def create_test_image():
    """Create a simple test image using SimpleITK"""
    # Create a simple 3D image (50x50x20) with a sphere in the middle
    size = [50, 50, 20]
    image = sitk.Image(size[0], size[1], size[2], sitk.sitkFloat32)
    
    # Set some metadata
    image.SetOrigin([10.0, 20.0, 30.0])
    image.SetSpacing([0.5, 0.5, 1.0])
    
    # Fill with test pattern - a sphere
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                # Distance from center
                dx = x - size[0]//2
                dy = y - size[1]//2
                dz = z - size[2]//2
                distance = np.sqrt(dx*dx + dy*dy + dz*dz)
                
                # Set value based on distance (sphere pattern)
                if distance < 10:
                    image[x, y, z] = 100.0
                else:
                    image[x, y, z] = 0.0
    
    return image

def verify_conversion(sitk_image, vtk_image):
    """Verify that the VTK image matches the SimpleITK image"""
    # Check dimensions
    sitk_size = sitk_image.GetSize()
    vtk_dims = vtk_image.GetDimensions()
    print(f"SimpleITK size: {sitk_size}")
    print(f"VTK dimensions: {vtk_dims}")
    
    # Check origin
    sitk_origin = sitk_image.GetOrigin()
    vtk_origin = vtk_image.GetOrigin()
    print(f"SimpleITK origin: {sitk_origin}")
    print(f"VTK origin: {vtk_origin}")
    
    # Check spacing
    sitk_spacing = sitk_image.GetSpacing()
    vtk_spacing = vtk_image.GetSpacing()
    print(f"SimpleITK spacing: {sitk_spacing}")
    print(f"VTK spacing: {vtk_spacing}")
    
    # Check some sample values
    center_x, center_y, center_z = [d//2 for d in sitk_size]
    sitk_value = sitk_image[center_x, center_y, center_z]
    vtk_value = vtk_image.GetScalarComponentAsFloat(center_x, center_y, center_z, 0)
    print(f"Center value in SimpleITK: {sitk_value}")
    print(f"Center value in VTK: {vtk_value}")
    
    # Check if values match approximately
    if abs(sitk_value - vtk_value) < 0.001:
        print("✓ Center values match!")
    else:
        print("✗ Center values do not match!")
    
    # Check a few more random points
    matches = 0
    total_checks = 5
    
    np.random.seed(42)  # For reproducibility
    for i in range(total_checks):
        x = np.random.randint(0, sitk_size[0]-1)
        y = np.random.randint(0, sitk_size[1]-1)
        z = np.random.randint(0, sitk_size[2]-1)
        
        sitk_val = sitk_image[x, y, z]
        vtk_val = vtk_image.GetScalarComponentAsFloat(x, y, z, 0)
        
        if abs(sitk_val - vtk_val) < 0.001:
            matches += 1
    
    print(f"Random point checks: {matches}/{total_checks} match")
    
    return matches == total_checks

def test_conversion():
    """Test both versions of the conversion function"""
    print("Creating test image...")
    test_image = create_test_image()
    
    print("\nTesting original sitk2vtk...")
    old_vtk_image = old_sitk2vtk(test_image)
    old_result = verify_conversion(test_image, old_vtk_image)
    
    print("\nTesting new sitk2vtk...")
    new_vtk_image = new_sitk2vtk(test_image)
    new_result = verify_conversion(test_image, new_vtk_image)
    
    if old_result and new_result:
        print("\n✓ Both versions passed all tests!")
        return True
    else:
        print("\n✗ Test failures detected")
        return False

if __name__ == "__main__":
    success = test_conversion()
    sys.exit(0 if success else 1)