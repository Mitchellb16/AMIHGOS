#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for vtk_utils functionality.
Written by Mitchell Bishop using Claude AI
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the new vtk_utils implementation.
This script verifies that the new module works correctly.
"""
import os
import sys
import vtk

# Ensure we can find the module path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the new module
from amihgosapp.utils import vtk_utils

def create_test_mesh():
    """Create a simple test mesh - a sphere."""
    source = vtk.vtkSphereSource()
    source.SetCenter(0, 0, 0)
    source.SetRadius(1.0)
    source.SetThetaResolution(32)
    source.SetPhiResolution(32)
    source.Update()
    return source.GetOutput()

def create_test_volume():
    """Create a simple test volume - a 3D Gaussian."""
    source = vtk.vtkImageGaussianSource()
    source.SetCenter(0, 0, 0)
    source.SetMaximum(1.0)
    source.SetStandardDeviation(5.0)
    source.SetWholeExtent(0, 50, 0, 50, 0,50)
    source.Update()
    return source.GetOutput()

def test_mesh_functions():
    """Test various mesh manipulation functions."""
    print("Creating test mesh...")
    test_mesh = create_test_mesh()
    original_poly_count = test_mesh.GetNumberOfPolys()
    print(f"Original mesh: {original_poly_count} polygons")
    
    # Test mesh reduction
    print("\nTesting mesh reduction...")
    reduced_mesh = vtk_utils.reduce_mesh(test_mesh, 0.5)
    reduced_count = reduced_mesh.GetNumberOfPolys()
    print(f"Reduced mesh: {reduced_count} polygons")
    
    if reduced_count < original_poly_count:
        print("✓ Mesh reduction working correctly")
    else:
        print("✗ Mesh reduction failed")
    
    # Test mesh smoothing
    print("\nTesting mesh smoothing...")
    smoothed_mesh = vtk_utils.smooth_mesh(test_mesh, n_iterations=5)
    
    if smoothed_mesh and smoothed_mesh.GetNumberOfPoints() > 0:
        print("✓ Mesh smoothing working correctly")
    else:
        print("✗ Mesh smoothing failed")
    
    # Test mesh cleaning
    print("\nTesting mesh cleaning...")
    cleaned_mesh = vtk_utils.clean_mesh(test_mesh)
    
    if cleaned_mesh and cleaned_mesh.GetNumberOfPoints() > 0:
        print("✓ Mesh cleaning working correctly")
    else:
        print("✗ Mesh cleaning failed")
    
    # Test mesh rotation
    print("\nTesting mesh rotation...")
    rotated_mesh = vtk_utils.rotate_mesh(test_mesh, axis=2, angle=45)
    
    if rotated_mesh and rotated_mesh.GetNumberOfPoints() > 0:
        print("✓ Mesh rotation working correctly")
    else:
        print("✗ Mesh rotation failed")
    
    return True

def test_file_io(temp_dir=None):
    """Test file I/O operations."""
    if temp_dir is None:
        temp_dir = os.getcwd()
    
    test_mesh = create_test_mesh()
    
    # Test STL writing and reading
    print("\nTesting STL file I/O...")
    stl_path = os.path.join(temp_dir, "test.stl")
    
    # Test writing
    vtk_utils.write_stl(test_mesh, stl_path)
    
    if os.path.exists(stl_path):
        print("✓ STL writing working correctly")
        
        # Test reading
        read_mesh = vtk_utils.read_stl(stl_path)
        
        if read_mesh and read_mesh.GetNumberOfPoints() > 0:
            print("✓ STL reading working correctly")
        else:
            print("✗ STL reading failed")
    else:
        print("✗ STL writing failed")
    
    # Clean up temporary file
    if os.path.exists(stl_path):
        try:
            os.remove(stl_path)
        except:
            print(f"Warning: Could not remove temporary file {stl_path}")
    
    return True

def test_volume_io(temp_dir=None):
    """Test volume I/O operations."""
    if temp_dir is None:
        temp_dir = os.getcwd()
    
    test_volume = create_test_volume()
    
    # Test VTK volume writing
    print("\nTesting VTK volume writing...")
    vtk_path = os.path.join(temp_dir, "test_volume.vtk")
    
    vtk_utils.write_vtk_volume(test_volume, vtk_path)
    
    if os.path.exists(vtk_path):
        print("✓ VTK volume writing working correctly")
    else:
        print("✗ VTK volume writing failed")
    
    # Test VTI volume writing
    print("\nTesting VTI volume writing...")
    vti_path = os.path.join(temp_dir, "test_volume.vti")
    
    vtk_utils.write_vti_volume(test_volume, vti_path)
    
    if os.path.exists(vti_path):
        print("✓ VTI volume writing working correctly")
    else:
        print("✗ VTI volume writing failed")
    
    # Clean up temporary files
    for path in [vtk_path, vti_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                print(f"Warning: Could not remove temporary file {path}")
    
    return True

def test_extract_surface():
    """Test surface extraction from volume."""
    print("\nTesting surface extraction...")
    test_volume = create_test_volume()
    
    surface = vtk_utils.extract_surface(test_volume, isovalue=0.5)
    
    if surface and surface.GetNumberOfCells() > 0:
        print("✓ Surface extraction working correctly")
        print(f"  Extracted surface has {surface.GetNumberOfCells()} cells")
        return True
    else:
        print("✗ Surface extraction failed")
        return False

def run_all_tests():
    """Run all tests and return True if all passed."""
    print("=== Testing New VTK Utils Implementation ===")
    
    print("\n--- Testing mesh functions ---")
    mesh_result = test_mesh_functions()
    
    print("\n--- Testing file I/O ---")
    file_result = test_file_io()
    
    print("\n--- Testing volume I/O ---")
    volume_result = test_volume_io()
    
    print("\n--- Testing surface extraction ---")
    surface_result = test_extract_surface()
    
    print("\n=== Test Summary ===")
    if mesh_result and file_result and volume_result and surface_result:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)