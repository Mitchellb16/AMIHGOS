#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A collection of VTK functions for processing surfaces and volumes.

Originally written by David T. Chen from the National Institute of Allergy and
Infectious Diseases, dchen@mail.nih.gov.
It is covered by the Apache License, Version 2.0:
http://www.apache.org/licenses/LICENSE-2.0

Reorganized and optimized as part of the AMIHGOS project migration by Mitchell Bishop and Claude AI.
"""

import sys
import os
import time
import traceback
import vtk
import pyvista as pv
import trimesh


def round_thousand(x):
    """Round a number to the nearest thousandth for display."""
    y = int(1000.0 * x + 0.5)
    return str(float(y) * .001)


def elapsed_time(start_time):
    """Print the elapsed time since start_time in seconds."""
    dt = round_thousand(time.perf_counter() - start_time)
    print("    ", dt, "seconds")
    
# Helper function for watertightness check
def _is_mesh_watertight(mesh: pv.PolyData) -> bool:
    """Checks if a PyVista mesh is watertight (i.e., has no boundary edges)."""
    boundary_edges = mesh.extract_feature_edges(feature_edges=False, non_manifold_edges=False, boundary_edges=True)
    return boundary_edges.n_points == 0

# Helper function for robust boolean difference
def _perform_robust_boolean_difference(mesh_a_file: str, mesh_b_file: str, animal_name: str, 
                                       output_directory: str, operation_name: str = "subtraction", preview = False,
                                       debug_plot: bool = True) -> str | None:
    """
    Performs a robust boolean difference (mesh_a - mesh_b) using Trimesh,
    with file-based handling for mesh type conversion.

    Args:
        mesh_a_file (str): The path to the mesh to subtract from.
        mesh_b_file (str): The path to the mesh to subtract.
        output_directory (str): Directory to save temporary and final mesh files.
        operation_name (str): A descriptive name for the current operation (e.g., "chin subtraction").
        debug_plot (bool): If True, plots intermediate meshes and their feature edges for debugging
                           (applies to PyVista inputs before Trimesh conversion).

    Returns:
        str | None: The file path to the resulting mesh after subtraction, or None if the operation failed.
    """
    print(f"\n--- Starting Robust Boolean Operation: {operation_name} ---")

    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)

    
    #Load meshes into Trimesh and perform boolean subtraction ---
    try:
        print(f"Loading meshes into Trimesh for {operation_name}...")
        trimesh_a = trimesh.load_mesh(mesh_a_file)
        print(f'loaded mesh_a {mesh_a_file}')
        trimesh_b = trimesh.load_mesh(mesh_b_file)
        print(f'loaded mesh_b {mesh_b_file}')
        
        # Ensure consistent face winding and manifold properties for robust boolean operations
        trimesh_a.fix_normals()
        trimesh_b.fix_normals()
        
        # check watertightness of volumes
        print(f'Mesh A watertight? {trimesh_a.is_watertight}')
        print(f'Mesh B watertight? {trimesh_b.is_watertight}')
        
        # preview scene before subtraction
        if preview:
            scene = trimesh.Scene()
            scene.add_geometry(trimesh_a)
            scene.add_geometry(trimesh_b)
            trimesh_a.visual.face_colors = [200, 50, 50, 200]
            trimesh_b.visual.face_colors = [50, 50, 200, 200]
            print('Displaying preview of subtraction...')
            scene.show()

        print(f"Performing Trimesh boolean.difference for {operation_name}...")
        trimesh_result = trimesh.boolean.difference([trimesh_a, trimesh_b], 'manifold')

        if trimesh_result is None:
            # Trimesh's boolean operations can return None if inputs are problematic
            raise ValueError("Trimesh boolean.difference returned None. Check input validity and intersection.")
        
        # Optional: Trimesh results are usually good, but an additional fix_normals can't hurt
        trimesh_result.fix_normals()

        print(f"Trimesh {operation_name} successful. Result has {len(trimesh_result.vertices)} vertices, {len(trimesh_result.faces)} faces.")

        # --- 4. Save Trimesh result to output file (PyVista readable) ---
        # Exporting as PLY for general compatibility
        output_result_path = os.path.join(output_directory, f"{animal_name}_helmet.ply")
        trimesh_result.export(output_result_path)
        print(f"Trimesh result saved to {output_result_path}")

        return output_result_path

    except Exception as e:
        print(f"An error occurred during Trimesh boolean {operation_name}: {e}")
        print("Common causes: non-manifold or non-watertight inputs, self-intersections, or numerical issues.")
        print("Ensure input meshes are watertight and well-conditioned before passing to the function.")
        return None


def offset_mesh(input_mesh: pv.PolyData, offset_distance: float, healing_resolution: float | None = None) -> pv.PolyData:
    """
    Applies a uniform offset to a PyVista mesh along its surface normals.
    This expands (positive offset) or contracts (negative offset) the mesh.
    Optionally, it can "heal" self-intersections by voxelizing and re-extracting the surface.

    Args:
        input_mesh (pv.PolyData): The input PyVista mesh object.
        offset_distance (float): The distance to offset along the normal.
                                 Positive for outward, negative for inward.
        healing_resolution (float | None): If a float is provided, the offset mesh
                                           will be voxelized. This value acts as a
                                           factor for voxel size relative to the mesh's
                                           bounding box length.
                                           - A **lower value** (e.g., 50) results in a
                                             **coarser voxel grid**, providing **more aggressive healing**
                                             and smoothing, but less detail.
                                           - A **higher value** (e.g., 200) results in a
                                             **finer voxel grid**, preserving **more detail**
                                             but being less aggressive at healing severe issues.
                                           Common values range from 50 (very coarse) to 200 (quite fine).

    Returns:
        pv.PolyData: A new PyVista mesh object with the offset applied and optionally healed.
    """
    if not isinstance(input_mesh, pv.PolyData):
        try:
            input_mesh = input_mesh.extract_surface()
        except Exception as e:
            raise TypeError(f"Input must be a PyVista PolyData mesh or convertible to one. Error: {e}")

    try:
        mesh_with_normals = input_mesh.compute_normals(inplace=False, cell_normals=False, point_normals=True)
    except Exception as e:
        print(f"Warning: Could not compute normals for offset. Error: {e}")
        raise RuntimeError("Failed to compute mesh normals required for offsetting.") from e

    points = mesh_with_normals.points
    normals = mesh_with_normals.point_normals

    if normals is None or normals.shape[0] == 0:
        raise ValueError("Normals could not be computed for the input mesh, cannot offset.")

    offset_points = points + offset_distance * normals

    offset_mesh_result = pv.PolyData(offset_points, mesh_with_normals.faces)

    if healing_resolution is not None:
        print(f"Attempting to heal offset mesh using voxelization with resolution factor: {healing_resolution}")
        try:
            # First, clean the potentially self-intersecting offset mesh
            offset_mesh_result.clean(inplace=True)
            offset_mesh_result.fill_holes(10.0, inplace=True) # A default hole fill before voxelization

            # Calculate voxel density. A smaller healing_resolution factor means a coarser grid.
            # Example: mesh.length / 50 -> larger voxels; mesh.length / 200 -> smaller voxels.
            if offset_mesh_result.length == 0:
                print("Warning: Offset mesh has zero length, cannot compute voxel density. Skipping healing.")
                return offset_mesh_result
            
            voxel_density = offset_mesh_result.length / healing_resolution
            
            if voxel_density <= 0:
                print(f"Warning: Calculated voxel density is non-positive ({voxel_density}). Using fallback density.")
                voxel_density = offset_mesh_result.length / 100.0 # Fallback to a default reasonable density

            print(f"Voxel density set to: {voxel_density}")
            
            # Voxelize the (potentially self-intersecting) offset surface
            # 'enclosed=False' is important here, we're not trying to determine if points are *inside*
            # an already closed volume, but rather create a volume from a surface.
            voxelized_mesh = pv.voxelize(offset_mesh_result, density=voxel_density, check_surface=False)
            
            # Extract the outer surface (level set 0) from the voxel data
            # This creates a manifold, closed surface from the volume.
            healed_mesh = voxelized_mesh.extract_surface()
            
            if healed_mesh.n_points == 0:
                print("Voxelization healing resulted in an empty mesh. Returning original offset mesh (potentially problematic).")
                return offset_mesh_result

            # Final cleaning and normal computation for the healed surface
            healed_mesh.clean(inplace=True)
            healed_mesh.fill_holes(10.0, inplace=True) # Fill any new holes created by voxelization
            healed_mesh.compute_normals(inplace=True)
            healed_mesh.extract_largest(inplace=True) # Ensure it's one connected component
            healed_mesh.clean(inplace=True)

            print(f"Offset mesh healed successfully. New mesh has {healed_mesh.n_points} points, {healed_mesh.n_cells} faces.")
            return healed_mesh

        except Exception as e:
            print(f"Failed to heal offset mesh using voxelization: {e}")
            print("Returning original offset mesh (potentially problematic).")
            return offset_mesh_result

    return offset_mesh_result


def extract_surface(vol, isovalue=0.0):
    """
    Extract an isosurface from a volume.
    
    Parameters
    ----------
    vol : vtk.vtkImageData
        The volume data
    isovalue : float, optional
        The isovalue to extract, by default 0.0
        
    Returns
    -------
    vtk.vtkPolyData
        The extracted surface mesh
    """
    try:
        t = time.perf_counter()
        iso = vtk.vtkContourFilter()
        if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
            iso.SetInputData(vol)
        else:
            iso.SetInput(vol)
        iso.SetValue(0, isovalue)
        iso.Update()
        print("Surface extracted")
        mesh = iso.GetOutput()
        print("    ", mesh.GetNumberOfPolys(), "polygons")
        elapsed_time(t)
        iso = None
        return mesh
    except Exception:
        print("Iso-surface extraction failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def clean_mesh(mesh, connectivity_filter=False):
    """
    Clean a mesh using VTK's CleanPolyData filter.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The input mesh to clean
    connectivity_filter : bool, optional
        Whether to also apply connectivity filtering, by default False
        
    Returns
    -------
    vtk.vtkPolyData
        The cleaned mesh
    """
    try:
        t = time.perf_counter()
        connect = vtk.vtkPolyDataConnectivityFilter()
        clean = vtk.vtkCleanPolyData()

        if connectivity_filter:
            if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
                connect.SetInputData(mesh)
            else:
                connect.SetInput(mesh)
            connect.SetExtractionModeToLargestRegion()
            clean.SetInputConnection(connect.GetOutputPort())
        else:
            if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
                clean.SetInputData(mesh)
            else:
                clean.SetInput(mesh)

        clean.Update()
        print("Surface cleaned")
        m2 = clean.GetOutput()
        print("    ", m2.GetNumberOfPolys(), "polygons")
        elapsed_time(t)
        clean = None
        connect = None
        return m2
    except Exception:
        print("Surface cleaning failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def smooth_mesh(mesh, n_iterations=10):
    """
    Smooth a mesh using VTK's WindowedSincPolyData filter.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The input mesh to smooth
    n_iterations : int, optional
        Number of smoothing iterations, by default 10
        
    Returns
    -------
    vtk.vtkPolyData
        The smoothed mesh
    """
    try:
        t = time.perf_counter()
        smooth = vtk.vtkWindowedSincPolyDataFilter()
        smooth.SetNumberOfIterations(n_iterations)
        if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
            smooth.SetInputData(mesh)
        else:
            smooth.SetInput(mesh)
        smooth.Update()
        print("Surface smoothed")
        m2 = smooth.GetOutput()
        print("    ", m2.GetNumberOfPolys(), "polygons")
        elapsed_time(t)
        smooth = None
        return m2
    except Exception:
        print("Surface smoothing failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def rotate_mesh(mesh, axis=1, angle=0):
    """
    Rotate a mesh about an arbitrary axis.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The input mesh to rotate
    axis : int, optional
        Axis to rotate around (0=X, 1=Y, 2=Z), by default 1
    angle : float, optional
        Angle in degrees, by default 0
        
    Returns
    -------
    vtk.vtkPolyData
        The rotated mesh
    """
    try:
        print(f"Rotating surface: axis={axis}, angle={angle}")
        matrix = vtk.vtkTransform()
        if axis == 0:
            matrix.RotateX(angle)
        if axis == 1:
            matrix.RotateY(angle)
        if axis == 2:
            matrix.RotateZ(angle)
        tfilter = vtk.vtkTransformPolyDataFilter()
        tfilter.SetTransform(matrix)
        if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
            tfilter.SetInputData(mesh)
        else:
            tfilter.SetInput(mesh)
        tfilter.Update()
        mesh2 = tfilter.GetOutput()
        return mesh2
    except Exception:
        print("Surface rotating failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def reduce_mesh(mesh, reduction_factor):
    """
    Reduce the number of triangles in a mesh using VTK's DecimatePro filter.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The input mesh to reduce
    reduction_factor : float
        Reduction factor (0.0 to 1.0)
        
    Returns
    -------
    vtk.vtkPolyData
        The reduced mesh
    """
    try:
        t = time.perf_counter()
        deci = vtk.vtkDecimatePro()
        deci.SetTargetReduction(reduction_factor)
        if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
            deci.SetInputData(mesh)
        else:
            deci.SetInput(mesh)
        deci.Update()
        print("Surface reduced")
        m2 = deci.GetOutput()
        del deci
        print("    ", m2.GetNumberOfPolys(), "polygons")
        elapsed_time(t)
        return m2
    except Exception:
        print("Surface reduction failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def remove_small_objects(mesh, ratio):
    """
    Remove small parts which are not of interest.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The input mesh
    ratio : float
        A floating-point value between 0.0 and 1.0, the higher the stronger effect
        
    Returns
    -------
    vtk.vtkPolyData
        The cleaned mesh
    """
    # do nothing if ratio is 0
    if ratio == 0:
        return mesh

    try:
        t = time.perf_counter()
        conn_filter = vtk.vtkPolyDataConnectivityFilter()
        conn_filter.SetInputData(mesh)
        conn_filter.SetExtractionModeToAllRegions()
        conn_filter.Update()

        # remove objects consisting of less than ratio vertexes of the biggest object
        region_sizes = conn_filter.GetRegionSizes()

        # find object with most vertices
        max_size = 0
        for i in range(conn_filter.GetNumberOfExtractedRegions()):
            if region_sizes.GetValue(i) > max_size:
                max_size = region_sizes.GetValue(i)

        # append regions of sizes over the threshold
        conn_filter.SetExtractionModeToSpecifiedRegions()
        for i in range(conn_filter.GetNumberOfExtractedRegions()):
            if region_sizes.GetValue(i) > max_size * ratio:
                conn_filter.AddSpecifiedRegion(i)

        conn_filter.Update()
        processed_mesh = conn_filter.GetOutput()
        print("Small parts cleaned")
        print("    ", processed_mesh.GetNumberOfPolys(), "polygons")
        elapsed_time(t)
        return processed_mesh

    except Exception:
        print("Remove small objects failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
        return mesh


def read_mesh(name):
    """
    Read a mesh. Uses suffix to determine specific file type reader.
    
    Parameters
    ----------
    name : str
        Filename to read
        
    Returns
    -------
    vtk.vtkPolyData
        The loaded mesh
    """
    if name.endswith(".vtk"):
        return read_vtk_mesh(name)
    if name.endswith(".ply"):
        return read_ply(name)
    if name.endswith(".stl"):
        return read_stl(name)
    print("Unknown file type: ", name)
    return None


def read_vtk_mesh(name):
    """
    Read a VTK mesh file.
    
    Parameters
    ----------
    name : str
        Filename to read
        
    Returns
    -------
    vtk.vtkPolyData
        The loaded mesh
    """
    try:
        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(name)
        reader.Update()
        print("Input mesh:", name)
        mesh = reader.GetOutput()
        del reader
        return mesh
    except Exception:
        print("VTK mesh reader failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def read_stl(name):
    """
    Read an STL mesh file.
    
    Parameters
    ----------
    name : str
        Filename to read
        
    Returns
    -------
    vtk.vtkPolyData
        The loaded mesh
    """
    try:
        reader = vtk.vtkSTLReader()
        reader.SetFileName(name)
        reader.Update()
        print("Input mesh:", name)
        mesh = reader.GetOutput()
        del reader
        return mesh
    except Exception:
        print("STL Mesh reader failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def read_ply(name):
    """
    Read a PLY mesh file.
    
    Parameters
    ----------
    name : str
        Filename to read
        
    Returns
    -------
    vtk.vtkPolyData
        The loaded mesh
    """
    try:
        reader = vtk.vtkPLYReader()
        reader.SetFileName(name)
        reader.Update()
        print("Input mesh:", name)
        mesh = reader.GetOutput()
        del reader
        return mesh
    except Exception:
        print("PLY Mesh reader failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def write_mesh(mesh, name):
    """
    Write a mesh. Uses suffix to determine specific file type writer.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The mesh to write
    name : str
        Filename to write
    """
    print("Writing", mesh.GetNumberOfPolys(), "polygons to", name)
    if name.endswith(".vtk"):
        write_vtk_mesh(mesh, name)
        return
    if name.endswith(".ply"):
        write_ply(mesh, name)
        return
    if name.endswith(".stl"):
        write_stl(mesh, name)
        return
    print("Unknown file type: ", name)


def write_vtk_mesh(mesh, name):
    """
    Write a VTK mesh file.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The mesh to write
    name : str
        Filename to write
    """
    try:
        writer = vtk.vtkPolyDataWriter()
        if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
            writer.SetInputData(mesh)
        else:
            writer.SetInput(mesh)
        writer.SetFileTypeToBinary()
        writer.SetFileName(name)
        writer.Write()
        print("Output mesh:", name)
        writer = None
    except Exception:
        print("VTK mesh writer failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)


def write_stl(mesh, name):
    """
    Write an STL mesh file.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The mesh to write
    name : str
        Filename to write
    """
    try:
        writer = vtk.vtkSTLWriter()
        if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
            writer.SetInputData(mesh)
        else:
            writer.SetInput(mesh)
        writer.SetFileTypeToBinary()
        writer.SetFileName(name)
        writer.Write()
        print("Output mesh:", name)
        writer = None
    except Exception:
        print("STL mesh writer failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)


def write_ply(mesh, name):
    """
    Write a PLY mesh file.
    
    Parameters
    ----------
    mesh : vtk.vtkPolyData
        The mesh to write
    name : str
        Filename to write
    """
    try:
        writer = vtk.vtkPLYWriter()
        if vtk.vtkVersion.GetVTKMajorVersion() >= 6:
            writer.SetInputData(mesh)
        else:
            writer.SetInput(mesh)
        writer.SetFileTypeToBinary()
        writer.SetFileName(name)
        writer.Write()
        print("Output mesh:", name)
        writer = None
    except Exception:
        print("PLY mesh writer failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)


def read_vtk_volume(name):
    """
    Read a VTK volume image file.
    
    Parameters
    ----------
    name : str
        Filename to read
        
    Returns
    -------
    vtk.vtkStructuredPoints
        The volume data
    """
    try:
        reader = vtk.vtkStructuredPointsReader()
        reader.SetFileName(name)
        reader.Update()
        print("Input volume:", name)
        vol = reader.GetOutput()
        reader = None
        return vol
    except Exception:
        print("VTK volume reader failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def write_vtk_volume(vtkimg, name):
    """
    Write the old VTK Image file format.
    
    Parameters
    ----------
    vtkimg : vtk.vtkImageData
        The volume to write
    name : str
        Filename to write
    """
    try:
        writer = vtk.vtkStructuredPointsWriter()
        writer.SetFileName(name)
        writer.SetInputData(vtkimg)
        writer.SetFileTypeToBinary()
        writer.Update()
    except Exception:
        print("VTK volume writer failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)


def read_vti_volume(name):
    """
    Read a VTK XML volume image file.
    
    Parameters
    ----------
    name : str
        Filename to read
        
    Returns
    -------
    vtk.vtkStructuredPoints
        The volume data
    """
    try:
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(name)
        reader.Update()
        print("Input volume:", name)
        vol = reader.GetOutput()
        reader = None
        return vol
    except Exception:
        print("VTK XML volume reader failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    return None


def write_vti_volume(vtkimg, name):
    """
    Write the new XML VTK Image file format.
    
    Parameters
    ----------
    vtkimg : vtk.vtkImageData
        The volume to write
    name : str
        Filename to write
    """
    try:
        writer = vtk.vtkXMLImageDataWriter()
        writer.SetFileName(name)
        writer.SetInputData(vtkimg)
        writer.Update()
    except Exception:
        print("VTK volume writer failed")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)


# Keep the old function names for compatibility
# These will be imported by the compatibility layer
extractSurface = extract_surface
cleanMesh = clean_mesh
smoothMesh = smooth_mesh
rotateMesh = rotate_mesh
reduceMesh = reduce_mesh
removeSmallObjects = remove_small_objects
readMesh = read_mesh
readVTKMesh = read_vtk_mesh
readSTL = read_stl
readPLY = read_ply
writeMesh = write_mesh
writeVTKMesh = write_vtk_mesh
writeSTL = write_stl
writePLY = write_ply
readVTKVolume = read_vtk_volume
writeVTKVolume = write_vtk_volume
readVTIVolume = read_vti_volume
writeVTIVolume = write_vti_volume
roundThousand = round_thousand
elapsedTime = elapsed_time


if __name__ == "__main__":
    print("vtk_utils.py")
    print("VTK version:", vtk.vtkVersion.GetVTKVersion())
    print("VTK:", vtk)

    try:
        if len(sys.argv) >= 3:
            mesh = read_mesh(sys.argv[1])
            mesh2 = reduce_mesh(mesh, .50)
            write_mesh(mesh2, sys.argv[2])
        else:
            print("Usage: vtk_utils.py input_mesh output_mesh")
    except Exception:
        print("Error processing mesh")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)