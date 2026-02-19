import pyvista as pv
import numpy as np


def drape_mesh(mesh: pv.PolyData, drape_axis: str = 'z', resolution: int = 200) -> pv.PolyData:
    """
    Drapes a mesh by projecting its true upper surface (envelope) downwards
    for its entire height.

    This method uses a robust ray-tracing approach to accurately find the
    upper envelope. It creates a grid of points above the mesh and casts rays
    downwards to find the first intersection with the mesh. The surface is
    reconstructed by leveraging the grid topology of the casting plane,
    avoiding triangulation issues with complex boundaries.

    Args:
        mesh (pv.PolyData): The input mesh to drape. Must be a triangulated mesh.
        drape_axis (str): The axis along which to drape ('x', 'y', or 'z').
                          This is the "up" direction. Defaults to 'z'.
        resolution (int): The resolution of the grid used for ray tracing.
                          Higher values produce a more detailed drape but take
                          longer to compute. Defaults to 200.

    Returns:
        pv.PolyData: The single, draped mesh with a clean surface topology.
    """
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    if drape_axis.lower() not in axis_map:
        raise ValueError(f"drape_axis must be one of {list(axis_map.keys())}")
    drape_idx = axis_map[drape_axis.lower()]
    plane_indices = [i for i in range(3) if i != drape_idx]

    # Get the bounds of the mesh
    bounds = mesh.bounds
    min_bound_drape = bounds[drape_idx * 2]
    max_bound_drape = bounds[drape_idx * 2 + 1]
    extrusion_length = max_bound_drape - min_bound_drape

    # --- Create the Upper Envelope using Ray Tracing ---
    
    # 1. Create a grid of points above the mesh to cast rays from.
    # The grid is created on the plane perpendicular to the drape axis.
    i_size = bounds[plane_indices[0]*2+1] - bounds[plane_indices[0]*2]
    j_size = bounds[plane_indices[1]*2+1] - bounds[plane_indices[1]*2]
    
    # Determine resolution for the plane based on drape axis
    if drape_idx == 0: # Drape along X
        i_res, j_res = resolution, resolution
    elif drape_idx == 1: # Drape along Y
        i_res, j_res = resolution, resolution
    else: # Drape along Z
        i_res, j_res = resolution, resolution

    plane = pv.Plane(
        center=mesh.center,
        direction=tuple(v if i == drape_idx else 0 for i, v in enumerate([1,0,0])),
        i_size=i_size,
        j_size=j_size,
        i_resolution=i_res,
        j_resolution=j_res,
    )
    
    # Move the plane above the mesh
    plane_center = list(plane.center)
    plane_center[drape_idx] = max_bound_drape + extrusion_length * 0.01 # Place slightly above
    
    # 2. Perform the ray trace
    ray_origins = plane.points
    ray_direction = np.array([0.0, 0.0, 0.0])
    ray_direction[drape_idx] = -1.0
    all_directions = np.tile(ray_direction, (ray_origins.shape[0], 1))
    
    # Run the ray tracing, getting back the points and the indices of the rays that hit
    intersection_points, ray_indices, _ = mesh.multi_ray_trace(ray_origins, all_directions)

    # 3. Create a surface by reusing the ray-casting plane's topology
    if ray_indices.size < 3:
        raise ValueError(
            f"Ray tracing resulted in only {ray_indices.size} intersection points. "
            "Ensure the mesh is valid and the resolution is high enough."
        )

    # Start with a copy of the casting plane
    top_surface = plane.copy()
    
    # Update the points that had a successful intersection
    top_surface.points[ray_indices] = intersection_points

    # Remove cells where one or more vertices did not have a successful intersection
    hit_point_mask = np.zeros(top_surface.n_points, dtype=bool)
    hit_point_mask[ray_indices] = True
    
    # Get cell connectivity and check if all points in a cell were hit
    cells = top_surface.faces.reshape(-1, 5)[:, 1:]
    cell_point_hits = hit_point_mask[cells]
    valid_cell_mask = np.all(cell_point_hits, axis=1)
    
    top_surface = top_surface.extract_cells(valid_cell_mask)

    # It's good practice to fill any holes that might have been created
    top_surface = top_surface.fill_holes(hole_size=i_size * j_size)

    # --- Extrude the Surface ---
    extrusion_vector = np.array([0.0, 0.0, 0.0])
    extrusion_vector[drape_idx] = -extrusion_length

    draped_mesh = top_surface.extrude(extrusion_vector, capping=True)

    # A final clean to merge points and ensure a manifold surface
    draped_mesh = draped_mesh.clean(point_merging=True)

    return draped_mesh
# =============================================================================
# def drape_mesh(mesh: pv.PolyData, drape_axis: str = 'z', resolution: int = 200) -> pv.PolyData:
#     """
#     Drapes a mesh by projecting its true upper surface (envelope) downwards
#     for its entire height.
# 
#     This method uses a robust ray-tracing approach to accurately find the
#     upper envelope. It creates a grid of points above the mesh and casts rays
#     downwards to find the first intersection with the mesh. This handles
#     complex geometries, including overhangs and vertical walls, correctly.
# 
#     Args:
#         mesh (pv.PolyData): The input mesh to drape.
#         drape_axis (str): The axis along which to drape ('x', 'y', or 'z').
#                           This is the "up" direction. Defaults to 'z'.
#         resolution (int): The resolution of the grid used for ray tracing.
#                           Higher values produce a more detailed drape but take
#                           longer to compute. Defaults to 200.
# 
#     Returns:
#         pv.PolyData: The single, draped mesh with a clean surface topology.
#     """
#     axis_map = {'x': 0, 'y': 1, 'z': 2}
#     if drape_axis.lower() not in axis_map:
#         raise ValueError(f"drape_axis must be one of {list(axis_map.keys())}")
#     drape_idx = axis_map[drape_axis.lower()]
#     
#     # makes a 1x1 plane orthogonal to the drape direction
#     plane_indices = [i for i in range(3) if i != drape_idx]
# 
#     # Get the bounds of the mesh
#     bounds = mesh.bounds
#     min_bound_drape = bounds[drape_idx * 2]
#     max_bound_drape = bounds[drape_idx * 2 + 1]
#     extrusion_length = max_bound_drape - min_bound_drape
# 
#     # --- Create the Upper Envelope using Ray Tracing ---
#     
#     # 1. Create a grid of points above the mesh to cast rays from.
#     # The grid is created on the plane perpendicular to the drape axis.
#     x_res = resolution if plane_indices[0] == 0 else 1
#     y_res = resolution if plane_indices[0] == 1 or plane_indices[1] == 1 else 1
#     z_res = resolution if plane_indices[0] == 2 or plane_indices[1] == 2 else 1
# 
#     # Create a plane that will be moved to the top of the mesh
#     plane = pv.Plane(
#         center = mesh.center,
#         i_size=bounds[plane_indices[0]*2+1] - bounds[plane_indices[0]*2],
#         j_size=bounds[plane_indices[1]*2+1] - bounds[plane_indices[1]*2],
#         i_resolution=x_res if drape_idx != 0 else y_res,
#         j_resolution=y_res if drape_idx != 1 else z_res,
#     )
#     
#     # Center and move the plane above the mesh
#     plane_center = list(plane.center)
#     plane_center[drape_idx] = max_bound_drape + extrusion_length * 0.01 # Place slightly above
#     plane.points[:, drape_idx] += plane_center[drape_idx] - plane.center[drape_idx]
#     
#     # 2. Perform the ray trace
#     # The origin of each ray is a point on the plane
#     ray_origins = plane.points
#     # The direction of each ray is straight down the drape axis
#     ray_direction = [0.0, 0.0, 0.0]
#     ray_direction[drape_idx] = -1.0
#     all_directions = [ray_direction] * len(ray_origins)
#     
#     # Run the ray tracing
#     intersection_points, _, _ = mesh.multi_ray_trace(ray_origins, all_directions, first_point=True)
# 
#     # 3. Create a surface from the valid intersection points
#     if intersection_points.shape[0] < 3:
#         raise ValueError(
#             "Ray tracing resulted in fewer than 3 intersection points. "
#             "Ensure the mesh is valid and the resolution is high enough."
#         )
# 
#     top_surface_cloud = pv.PolyData(intersection_points)
#     
#     # Use delaunay_2d to create a surface from the point cloud.
#     # This is safe now because the points are from a structured grid trace.
#     top_surface = top_surface_cloud.delaunay_2d(tol=1e-05)
# 
#     # It's good practice to fill any holes that might have been created
#     top_surface = top_surface.fill_holes(hole_size=1000.0)
# 
#     # --- Extrude the Surface ---
#     # Define the extrusion vector (e.g., [0, 0, -height])
#     extrusion_vector = np.array([0.0, 0.0, 0.0])
#     extrusion_vector[drape_idx] = -extrusion_length
# 
#     # Extrude the top surface downwards and create caps to form a solid
#     draped_mesh = top_surface.extrude(extrusion_vector, capping=True)
# 
#     # A final clean to merge points and ensure a manifold surface
#     draped_mesh = draped_mesh.clean(point_merging=True)
# 
#     return draped_mesh, plane
# =============================================================================


def drape_by_width(mesh: pv.PolyData, drape_axis: str = 'z', width_axis: str = 'x', n_slices: int = 150) -> pv.PolyData:
    """
    Original function signature preserved for backward compatibility.
    This function now calls the new, more robust `drape_mesh` function.
    The `width_axis` and `n_slices` parameters are ignored.
    """
    print("Warning: `drape_by_width` is deprecated. Calling `drape_mesh` instead.")
    return drape_mesh(mesh, drape_axis)


# --- Example Usage ---
if __name__ == '__main__':
    # 1. Create a sample mesh with some complex topography to test the function
    # Create a wavy surface with a hole in it to test robustness
    x = np.arange(-10, 10, 0.5)
    y = np.arange(-10, 10, 0.5)
    xx, yy = np.meshgrid(x, y)
    zz = -np.sin(xx/2) * np.cos(yy/2) * 2.0
    base_surface = pv.StructuredGrid(xx, yy, zz).extract_surface()
    
    # Create a hole in the surface
    hole = pv.Cylinder(center=(0,0,-2), direction=(0,0,1), radius=2, height=5)

    # FIX: Triangulate both meshes before the boolean operation
    base_surface.triangulate(inplace=True)
    hole.triangulate(inplace=True)
    
    # Now the boolean operation will succeed
    base_surface = base_surface.boolean_difference(hole)


    # 2. Add a second, separate object above the first one
    # sphere = pv.Sphere(radius=3)
    sphere = pv.read('/home/mitchell/Documents/Projects/CT_helmets/AMIHGOS_V3/amihgosapp/resources/head_stls/JESTER_smoothed_mmoffset6.stl')
    
    # Combine the two meshes into a single object
    combined_mesh = base_surface + sphere
    combined_mesh = combined_mesh.triangulate() # Triangulate again for consistency

    # 3. Run the draping function
    try:
        # Using a lower resolution for the example to run faster
        draped_object, plane = drape_mesh(sphere, drape_axis='z', resolution=100)

        # 4. Plot the original and the result for comparison
        plotter = pv.Plotter(shape=(1, 2), window_size=[1600, 800])
        
        plotter.subplot(0, 0)
        plotter.add_text("Original Mesh", font_size=15)
        plotter.add_mesh(sphere, style='surface', show_edges=False, color='tan')
        plotter.add_axes()
        plotter.camera_position = 'xy'
        plotter.camera.zoom(1.5)

        plotter.subplot(0, 1)
        plotter.add_text("Draped Mesh (Ray-Traced)", font_size=15)
        plotter.add_mesh(draped_object, style='surface', show_edges=False, color='lightblue')
        plotter.add_mesh(plane, style = 'surface', show_edges = False)
        plotter.add_axes()

        plotter.link_views()
        plotter.show()

    except ValueError as e:
        print(f"An error occurred during draping: {e}")
