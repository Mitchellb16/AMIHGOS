#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug  1 12:01:09 2025

@author: mitchell
"""

import os
import trimesh
import pyvista as pv

def analyze_meshes(directory_path):
    """
    Loops through mesh files in a given directory and returns the names of
    files that are non-manifold or non-watertight.

    Args:
        directory_path (str): The path to the directory containing mesh files.

    Returns:
        dict: A dictionary with two lists: 'non_manifold_files' and 'non_watertight_files'.
              Each list contains the base names of the respective problematic mesh files.
    """
    non_manifold_files = []
    non_watertight_files = []

    # Define common mesh file extensions
    mesh_extensions = ('.obj', '.stl', '.ply', '.off', '.gltf', '.glb')

    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found at '{directory_path}'")
        return {"non_manifold_files": [], "non_watertight_files": []}

    print(f"Analyzing meshes in directory: {directory_path}")

    for filename in os.listdir(directory_path):
        if filename.lower().endswith(mesh_extensions):
            filepath = os.path.join(directory_path, filename)
            print(f"  Processing: {filename}")
            try:
                # Load the mesh using trimesh for the watertight check.
                trimesh_loaded_object = trimesh.load_mesh(filepath)

                # Handle different return types from trimesh.load
                trimesh_to_analyze = None
                if isinstance(trimesh_loaded_object, trimesh.Trimesh):
                    trimesh_to_analyze = trimesh_loaded_object
                elif isinstance(trimesh_loaded_object, trimesh.Scene) and len(trimesh_loaded_object.geometry) == 1:
                    trimesh_to_analyze = list(trimesh_loaded_object.geometry.values())[0]
                elif isinstance(trimesh_loaded_object, trimesh.Scene) and len(trimesh_loaded_object.geometry) > 1:
                    print(f"    - Note: The file '{filename}' contains multiple meshes. Analyzing the first one.")
                    trimesh_to_analyze = list(trimesh_loaded_object.geometry.values())[0]
                else:
                    print(f"    - Could not load a valid Trimesh object from '{filename}'.")
                    continue

                # Check for non-watertightness using trimesh
                if not trimesh_to_analyze.is_watertight:
                    non_watertight_files.append(filename)
                    print(f"    - Non-watertight detected.")

                # Load the mesh again, this time using pyvista for the manifold check.
                pyvista_mesh = pv.read(filepath)

                # Check for non-manifoldness using pyvista
                if not pyvista_mesh.is_manifold:
                    non_manifold_files.append(filename)
                    print(f"    - Non-manifold detected.")

            except Exception as e:
                print(f"    - Could not load or process '{filename}': {e}")
                continue

    return {
        "non_manifold_files": non_manifold_files,
        "non_watertight_files": non_watertight_files
    }

# --- Example Usage ---
if __name__ == '__main__':
    # Define the directory path you want to analyze
    my_mesh_directory = "/home/mitchell/Documents/Projects/CT_helmets/AMIHGOS_V3/amihgosapp/resources/head_stls" # <-- Please provide the directory path here

    if my_mesh_directory:
        analysis_results = analyze_meshes(my_mesh_directory)

        print("\n--- Analysis Results ---")
        if analysis_results["non_manifold_files"]:
            print("Non-manifold files:")
            for f in analysis_results["non_manifold_files"]:
                print(f"- {f}")
        else:
            print("No non-manifold files found.")

        if analysis_results["non_watertight_files"]:
            print("\nNon-watertight files:")
            for f in analysis_results["non_watertight_files"]:
                print(f"- {f}")
        else:
            print("\nNo non-watertight files found.")
