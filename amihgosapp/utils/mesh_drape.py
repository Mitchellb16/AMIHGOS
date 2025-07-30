import pyvista as pv
import vtk
import numpy as np
import trimesh
import os # For path manipulation and directory creation/cleanup
import shutil # For robust directory cleanup

def create_manifold_extrusion(mesh: pv.PolyData, drape_axis: str = 'z', width_axis: str = 'x',
                              n_slices: int = 150, output_ply_filename: str = "extruded_mesh.ply"):
    """
    Extracts the widest slice from a mesh, triangulates it into a
    filled 2D surface, and then extrudes this surface downward to the
    lowest boundary of the input mesh along the drape_axis to create
    a manifold 3D mesh. The extruded mesh is also saved as a .ply file.

    Args:
        mesh (pv.PolyData): The input 3D mesh (PyVista object).
        drape_axis (str, optional): The axis along which to slice. Defaults to 'z'.
        width_axis (str, optional): The axis to measure for width. Defaults to 'x'.
        n_slices (int, optional): Number of slices to check. Defaults to 150.
        output_ply_filename (str, optional): Filename to save the extruded mesh.
                                              Defaults to "extruded_mesh.ply".

    Returns:
        pv.PolyData or None: The manifold 3D extruded mesh as a PyVista object,
                             or None if failed. This object is also saved to file.
    """
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    drape_idx = axis_map[drape_axis.lower()]
    width_idx = axis_map[width_axis.lower()]
    normal = np.array([0., 0., 0.])
    normal[drape_idx] = 1.

    bounds = mesh.bounds
    min_overall_bound = bounds[drape_idx * 2]
    max_overall_bound = bounds[drape_idx * 2 + 1]
    # We only want to look for the widest slice above the middle of the head
    # so that we don't accidentally get the ears
    min_slice_check = 0

    max_width = 0.0
    best_slice_pv = None
    current_best_pos = min_overall_bound

    # Find the slice with the maximum width
    for pos in np.linspace(min_slice_check, max_overall_bound, n_slices):
        slice_ = mesh.slice(normal=normal, origin=(0, 0, pos))
        if slice_.n_points > 2:
            width = slice_.bounds[width_idx * 2 + 1] - slice_.bounds[width_idx * 2]
            if width > max_width:
                max_width = width
                best_slice_pv = slice_
                current_best_pos = pos

    if best_slice_pv is None:
        print("Could not find a valid slice.")
        return None
    
    # Calculate the extrusion depth dynamically
    extrusion_depth = current_best_pos - min_overall_bound
    
    if extrusion_depth <= 1e-6:
        print(f"Extrusion depth is too small ({extrusion_depth:.2e}). Cannot extrude.")
        return None

    # --- Polyline Preparation ---
    try:
        cleaned_slice = best_slice_pv.clean()
        largest_component = cleaned_slice.extract_largest()
        stripper = vtk.vtkStripper()
        stripper.SetInputData(largest_component)
        stripper.Update()
        ordered_polyline = pv.wrap(stripper.GetOutput())

        if ordered_polyline.n_points == 0:
            raise ValueError("Polyline stripping resulted in an empty mesh.")

        planar_points = ordered_polyline.points.copy()
        planar_points[:, drape_idx] = current_best_pos
        
        n_pts = planar_points.shape[0]
        line_cell = np.hstack([[n_pts], np.arange(n_pts)])
        contour_to_fill = pv.PolyData(planar_points, lines=line_cell)

    except Exception as e:
        print(f"ERROR during polyline preparation: {e}")
        return None

    # --- Triangulation using PyVista Constrained Delaunay ---
    print("\n--- Triangulating with PyVista Constrained Delaunay ---")
    filled_face = None
    try:
        filled_face = contour_to_fill.delaunay_2d(tol=1e-5, alpha=0)
        filled_face = filled_face.clean()

        print(f"Filled 2D face manifold (2-manifold with boundary): {filled_face.is_manifold}")
        if filled_face.n_faces == 0:
            raise ValueError("Triangulation resulted in an empty mesh.")

    except Exception as e:
        print(f"ERROR during 2D triangulation: {e}")
        return None
    
    # --- Extrusion to 3D Mesh ---
    print("\n--- Extruding to 3D Mesh ---")
    extruded_mesh = None
    try:
        extrusion_direction = np.array([0., 0., 0.])
        extrusion_direction[drape_idx] = -1.0 # Negative to go "downward"

        extruded_mesh = filled_face.extrude(extrusion_direction * extrusion_depth, capping=True)
        extruded_mesh = extruded_mesh.clean()

        print(f"3D Extruded Mesh Manifold: {extruded_mesh.is_manifold}")
        print(f"3D Extruded Mesh Number of Faces: {extruded_mesh.n_faces}")
        print(f"3D Extruded Mesh Number of Points: {extruded_mesh.n_points}")

        # Save the extruded mesh for Trimesh to load
        try:
            extruded_mesh.save(output_ply_filename)
            print(f"Extruded mesh saved to {output_ply_filename}")
        except Exception as save_e:
            print(f"WARNING: Could not save extruded mesh to {output_ply_filename}: {save_e}")

        return extruded_mesh

    except Exception as e:
        print(f"ERROR during extrusion or manifold check: {e}")
        return None

def create_draped_mesh_from_files(original_mesh_path: str, extruded_ply_filename: str, draped_output_ply_filename: str) -> str:
    """
    Performs a boolean union of the original mesh and the extruded mesh,
    both loaded from files using trimesh.load(). The result is saved to a new PLY file.

    Args:
        original_mesh_path (str): The file path to the original 3D mesh (e.g., .stl).
        extruded_ply_filename (str): The file path to the .ply file containing
                                     the 3D mesh extruded from the widest slice.
        draped_output_ply_filename (str): The file path to save the final draped mesh.

    Returns:
        str or None: The file path to the saved draped mesh, or None if the operation fails.
    """
    print("\n--- Performing Boolean Union with Trimesh (loading from files) ---")
    try:
        # Load the original mesh using trimesh
        if not os.path.exists(original_mesh_path):
            print(f"Error: Original mesh file not found at {original_mesh_path}")
            return None
        trimesh_original = trimesh.load(original_mesh_path)
        print(f"Loaded original mesh from {original_mesh_path}")
        print(f'Original mesh Watertight? {trimesh_original.is_watertight}')
        print(f'Original mesh Volume? {trimesh_original.is_volume}')

        # Load the extruded mesh using trimesh
        if not os.path.exists(extruded_ply_filename):
            print(f"Error: Extruded mesh file not found at {extruded_ply_filename}")
            return None
        trimesh_extruded = trimesh.load(extruded_ply_filename)
        print(f"Loaded extruded mesh from {extruded_ply_filename}")
        print(f'Extruded mesh Watertight? {trimesh_extruded.is_watertight}')
        print(f'Extruded mesh Volume? {trimesh_extruded.is_volume}')
        # Ensure consistent face winding for robust boolean operations
        trimesh_original.fix_normals()
        trimesh_extruded.fix_normals()

        # Perform the boolean union
        draped_trimesh = trimesh.boolean.union([trimesh_original, trimesh_extruded], 'manifold')
        
        # Try convex hull to solve watertight issue
        #draped_trimesh = draped_trimesh.convex_hull

        if draped_trimesh is None:
            raise ValueError("Trimesh boolean union returned None.")

        print(f"Draped Trimesh Number of Faces: {len(draped_trimesh.faces)}")
        print(f"Draped Trimesh Number of Vertices: {len(draped_trimesh.vertices)}")
        print(f'Draped Trimesh Watertight? {draped_trimesh.is_watertight}')

        # Save the draped mesh to a file using trimesh's export
        try:
            draped_trimesh.export(draped_output_ply_filename)
            print(f"Draped mesh saved to {draped_output_ply_filename}")
        except Exception as export_e:
            print(f"WARNING: Could not save draped mesh to {draped_output_ply_filename}: {export_e}")
            return None # Return None if saving failed

        return draped_output_ply_filename

    except Exception as e:
        print(f"ERROR during Trimesh boolean union: {e}")
        print("Ensure input meshes are valid and accessible files.")
        return None

def perform_draping_workflow(original_mesh_pv: pv.PolyData, animal_name: str, output_directory: str,
                             drape_axis: str = 'z', width_axis: str = 'x', n_slices: int = 150) -> tuple[str | None, pv.PolyData | None]:
    """
    Orchestrates the entire draping process: finds the widest slice, extrudes it,
    combines it with the original mesh using Trimesh, and saves the final result.

    Args:
        original_mesh_pv (pv.PolyData): The original input 3D mesh as a PyVista object.
        output_directory (str): The directory where all intermediate and final mesh files will be saved.
        drape_axis (str, optional): The axis along which to slice for extrusion. Defaults to 'z'.
        width_axis (str, optional): The axis to measure for width. Defaults to 'x'.
        n_slices (int, optional): Number of slices to check for the widest slice. Defaults to 150.

    Returns:
        tuple[str | None, pv.PolyData | None]: A tuple containing:
            - The file path to the final draped mesh (str), or None if failed.
            - The PyVista object of the extruded mesh (pv.PolyData), or None if failed,
              useful for visualizing intermediate steps.
    """
    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)
    print(f"\n--- Starting Draping Workflow in '{output_directory}' ---")

    # Define paths for temporary and final files
    temp_original_mesh_path = os.path.join(output_directory, "temp_original_mesh.stl")
    extruded_mesh_path = os.path.join(output_directory, f"{animal_name}_extruded_mesh.ply")
    final_draped_mesh_path = os.path.join(output_directory, f"{animal_name}_final_draped_mesh.ply")

    extruded_pv_for_display = None # To hold the PyVista object of the extruded mesh

    # 1. Save the original mesh for Trimesh to read
    try:
        original_mesh_pv.save(temp_original_mesh_path)
        print(f"Original mesh (PyVista) saved to {temp_original_mesh_path}")
    except Exception as save_e:
        print(f"ERROR: Could not save original mesh to {temp_original_mesh_path}: {save_e}")
        return None, None

    # 2. Create the manifold extrusion
    # This function saves the extruded mesh and returns it as a PyVista object
    extruded_pv_for_display = create_manifold_extrusion(
        original_mesh_pv,
        drape_axis=drape_axis,
        width_axis=width_axis,
        n_slices=n_slices,
        output_ply_filename=extruded_mesh_path
    )
    if extruded_pv_for_display is None:
        print("Manifold extrusion failed. Cannot proceed with draping.")
        return None, None

    # 3. Perform the boolean union using Trimesh (loading from files)
    final_draped_file_path = create_draped_mesh_from_files(
        temp_original_mesh_path,
        extruded_mesh_path,
        final_draped_mesh_path
    )

    if final_draped_file_path is None:
        print("Boolean union failed. Final draped mesh not created.")
        return None, None
    
    print(f"--- Draping Workflow Completed. Final mesh at: {final_draped_file_path} ---")
    return final_draped_file_path, extruded_pv_for_display, extruded_mesh_path

# --- Example Usage ---
if __name__ == '__main__':
    
    # Define an output directory for all generated files
    output_dir = "draping_output"

    # For a general runnable example, using a PyVista built-in shape:
    custom_shape = pv.read('/home/mitchell/Documents/Projects/CT_helmets/AMIHGOS_V3/amihgosapp/resources/head_stls/Tinsel_smoothed_mmoffset7.stl')
    #custom_shape = pv.Sphere(radius=5.0) 
    # custom_shape = pv.Cylinder(height=10, radius=3, resolution=50) # Another good test case

    p = pv.Plotter(shape=(1, 3), window_size=[2400, 800])

    # Subplot 1: Original Mesh (PyVista for display)
    p.subplot(0, 0)
    p.add_text("Original Mesh (PyVista)", font_size=15)
    p.add_mesh(custom_shape, show_edges=True, color='orange')
    p.view_isometric()

    # --- Run the full draping workflow ---
    # This single call orchestrates all the steps and file interactions
    final_draped_ply_path, extruded_pv_for_display, _ = perform_draping_workflow(
        original_mesh_pv=custom_shape, animal_name='TEST',
        output_directory=output_dir,
        drape_axis='z',
        n_slices=100
    )

    # Subplot 2: Extruded 3D Mesh (PyVista for display, returned by workflow)
    p.subplot(0, 1)
    p.add_text("Extruded 3D Mesh (PyVista)", font_size=15)
    if extruded_pv_for_display:
        p.add_mesh(extruded_pv_for_display, show_edges=True, color='lightgreen')
    else:
        p.add_text("3D Extrusion Failed", font_size=20, color='red')
    p.view_isometric()

    # Subplot 3: Draped Mesh (Boolean Union - loaded from file by PyVista for display)
    p.subplot(0, 2)
    p.add_text("Draped Mesh (Boolean Union - Trimesh)", font_size=15)
    draped_mesh_pv_for_display = None
    if final_draped_ply_path and os.path.exists(final_draped_ply_path):
        try:
            draped_mesh_pv_for_display = pv.read(final_draped_ply_path)
            draped_mesh_pv_for_display = draped_mesh_pv_for_display.clean()
            p.add_mesh(draped_mesh_pv_for_display, show_edges=True, color='cyan')
        except Exception as load_e:
            print(f"ERROR: Could not load draped mesh from {final_draped_ply_path}: {load_e}")
            p.add_text("Draping Failed (Load Error)", font_size=20, color='red')
    else:
        p.add_text("Draping Failed (File Missing)", font_size=20, color='red')
    p.view_isometric()

    p.link_views()
    p.show()

    # Final manifold checks for clarity (using PyVista's check on PV objects)
    if extruded_pv_for_display:
        print(f"\nFinal Check (PyVista): Is the extruded 3D mesh manifold? {extruded_pv_for_display.is_manifold}")
    if draped_mesh_pv_for_display:
        print(f"Final Check (PyVista): Is the draped mesh manifold? {draped_mesh_pv_for_display.is_manifold}")

    # --- Optional: Clean up created output directory ---
    try:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir) # Removes the directory and all its contents
            print(f"\nCleaned up: Removed output directory '{output_dir}' and its contents.")
    except Exception as cleanup_e:
        print(f"Error during directory cleanup: {cleanup_e}")