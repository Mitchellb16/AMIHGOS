#!/usr/bin/env python
"""
A collection of VTK functions for processing surfaces and volume.

This is a compatibility layer for the original vtkutils.py module.
All functions are imported from the new amihgosapp.utils.vtk_utils module.

Original by David T. Chen from the National Institute of Allergy and
Infectious Diseases, dchen@mail.nih.gov.
It is covered by the Apache License, Version 2.0:
http://www.apache.org/licenses/LICENSE-2.0
"""

import warnings

# Import everything from the new module location
from amihgosapp.utils.vtk_utils import (
    # Core functions
    extractSurface,
    cleanMesh,
    smoothMesh,
    rotateMesh,
    reduceMesh,
    removeSmallObjects,
    
    # Mesh I/O
    readMesh,
    readVTKMesh,
    readSTL,
    readPLY,
    writeMesh,
    writeVTKMesh,
    writeSTL,
    writePLY,
    
    # Volume I/O
    readVTKVolume,
    writeVTKVolume,
    readVTIVolume,
    writeVTIVolume,
    
    # Utilities
    roundThousand,
    elapsedTime,
    
    # Also expose the new snake_case names
    extract_surface,
    clean_mesh,
    smooth_mesh,
    rotate_mesh,
    reduce_mesh,
    remove_small_objects,
    read_mesh,
    read_vtk_mesh,
    read_stl,
    read_ply,
    write_mesh,
    write_vtk_mesh,
    write_stl,
    write_ply,
    read_vtk_volume,
    write_vtk_volume,
    read_vti_volume,
    write_vti_volume,
    round_thousand,
    elapsed_time,
)

# Add a deprecation warning
warnings.warn(
    "The 'utils.vtkutils' module is deprecated. Please use 'amihgosapp.utils.vtk_utils' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Special handling for direct script execution
if __name__ == "__main__":
    import sys
    import vtk
    
    print("vtkutils.py (compatibility layer)")
    print("VTK version:", vtk.vtkVersion.GetVTKVersion())

    try:
        if len(sys.argv) >= 3:
            mesh = readMesh(sys.argv[1])
            mesh2 = reduceMesh(mesh, .50)
            writeMesh(mesh2, sys.argv[2])
        else:
            print("Usage: vtkutils.py input_mesh output_mesh")
    except Exception:
        print("Error processing mesh")
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)