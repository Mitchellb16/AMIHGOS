#! /usr/bin/env python

"""
Function to convert a SimpleITK image to a VTK image.

Adapted from script written by David T. Chen from the National Institute of Allergy
and Infectious Diseases, dchen@mail.nih.gov.
It is covered by the Apache License, Version 2.0:
http://www.apache.org/licenses/LICENSE-2.0

Changes made by Mitchell Bishop with help from Claude AI
"""
import SimpleITK as sitk
import vtk
from vtk.util import numpy_support


def sitk2vtk(img, debug_on=False):
    """
    Convert a SimpleITK image to a VTK image using numpy as an intermediate format.
    
    Parameters
    ----------
    img : sitk.Image
        The SimpleITK image to convert
    debug_on : bool, optional
        Whether to print debug information, by default False
        
    Returns
    -------
    vtk.vtkImageData
        The converted VTK image
    """
    # Get image properties
    size = list(img.GetSize())
    origin = list(img.GetOrigin())
    spacing = list(img.GetSpacing())
    n_components = img.GetNumberOfComponentsPerPixel()
    direction = img.GetDirection()
    
    # Convert the SimpleITK image to a numpy array
    array_data = sitk.GetArrayFromImage(img)
    
    if debug_on:
        array_string = array_data.tostring()
        print("Data string address inside sitk2vtk:", hex(id(array_string)))
    
    # Create a new VTK image
    vtk_image = vtk.vtkImageData()
    
    # VTK expects 3-dimensional parameters - pad if needed
    if len(size) == 2:
        size.append(1)
    if len(origin) == 2:
        origin.append(0.0)
    if len(spacing) == 2:
        spacing.append(spacing[0])
    if len(direction) == 4:  # 2D direction matrix (2x2)
        direction = [
            direction[0], direction[1], 0.0,
            direction[2], direction[3], 0.0,
            0.0, 0.0, 1.0
        ]
    
    # Set image properties
    vtk_image.SetDimensions(size)
    vtk_image.SetSpacing(spacing)
    vtk_image.SetOrigin(origin)
    vtk_image.SetExtent(0, size[0] - 1, 0, size[1] - 1, 0, size[2] - 1)
    
    # Set direction matrix if VTK version supports it
    if vtk.vtkVersion.GetVTKMajorVersion() >= 9:
        vtk_image.SetDirectionMatrix(direction)
    else:
        print("Warning: VTK version <9. No direction matrix support.")
    
    # Convert numpy array to VTK array
    depth_array = numpy_support.numpy_to_vtk(array_data.ravel())
    depth_array.SetNumberOfComponents(n_components)
    vtk_image.GetPointData().SetScalars(depth_array)
    vtk_image.Modified()
    
    # Print debug information if requested
    if debug_on:
        print("Volume object inside sitk2vtk:")
        print(vtk_image)
        print("Number of components =", n_components)
        print("Dimensions:", size)
        print("Origin:", origin)
        print("Spacing:", spacing)
        print("Sample value at (0,0,0):", vtk_image.GetScalarComponentAsFloat(0, 0, 0, 0))
    
    return vtk_image


def vtk2sitk(vtk_image, debug_on=False):
    """
    Convert a VTK image to a SimpleITK image.
    
    Parameters
    ----------
    vtk_image : vtk.vtkImageData
        The VTK image to convert
    debug_on : bool, optional
        Whether to print debug information, by default False
        
    Returns
    -------
    sitk.Image
        The converted SimpleITK image
    """
    # This is a placeholder for the reverse conversion
    # Can be implemented as needed for your application
    raise NotImplementedError("vtk2sitk conversion not yet implemented")
