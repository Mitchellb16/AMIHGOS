import trimesh
import pyvista as pv

def analyze_single_mesh(file_path):
    """
    Analyzes a single mesh file and returns its manifold and watertight status.

    Args:
        file_path (str): The full path to the mesh file.

    Returns:
        dict: A dictionary with 'manifold' and 'watertight' keys,
              each with a boolean value. Returns None if the file
              cannot be loaded.
    """
    try:
        # Load the mesh using trimesh for the watertight check.
        # This is a separate read operation from the pyvista read below.
        trimesh_to_analyze = trimesh.load_mesh(file_path)

        

        # Check for watertightness using trimesh
        is_watertight = trimesh_to_analyze.is_watertight
        
        if not is_watertight:
            print('self intersecting?',trimesh_to_analyze.is_self_intersecting)
            broken_idx = trimesh.repair.broken_faces(trimesh_to_analyze, color = [255, 0, 0, 255])
            print(broken_idx)
            trimesh_to_analyze.show()

        # Load the mesh again, this time using pyvista for the manifold check.
        # This ensures the check is performed on a native pyvista object.
        pyvista_mesh = pv.read(file_path)

        # Check for manifoldness using pyvista
        is_manifold = pyvista_mesh.is_manifold

        return {
            "manifold": is_manifold,
            "watertight": is_watertight
        }

    except Exception as e:
        print(f"Error: Could not load or process the file '{file_path}': {e}")
        return None

# --- Example Usage ---
if __name__ == '__main__':
    # Define the file path you want to analyze
    my_mesh_file = "/home/mitchell/Documents/Projects/CT_helmets/AMIHGOS_V3/amihgosapp/resources/head_stls/TEST.stl" # <-- Please provide the file path here

    if my_mesh_file:
        print(f"Analyzing file: {my_mesh_file}")
        analysis_results = analyze_single_mesh(my_mesh_file)

        if analysis_results:
            print("\n--- Analysis Results ---")
            print(f"Manifold: {analysis_results['manifold']}")
            print(f"Watertight: {analysis_results['watertight']}")
