#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SegmentationScreen module - GUI for segmenting and extracting STL meshes
"""
import sys
import tkinter as tk
from PyQt5 import QtWidgets
import SimpleITK as sitk

# Import from new locations when available
from amihgosapp.utils.resource_utils import get_image_path, get_template_path

# Import from old locations for modules not yet migrated
from amihgosapp.utils import sitk_utils
from amihgosapp.utils import vtk_utils
from amihgosapp.gui.mesh_manipulation import MeshManipulationWindow


class SegmentationScreen:
    """
    GUI for segmenting an image and extracting an STL mesh.
    
    This class provides functionality to process a SimpleITK image,
    create a mesh, and prepare it for manipulation with a helmet.
    """
    
    def __init__(self, img, animal_name):
        """
        Initialize the segmentation screen.
        
        Parameters
        ----------
        img : SimpleITK.Image
            The image to segment
        animal_name : str
            Name to use for the output STL file
        """
        self.img = img
        self.animal_name = animal_name
        self.output_dir = f'head_stls/{self.animal_name}.stl'
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        # Create main window
        self.root = tk.Tk()
        self.root.title("Segmentation")
        self.root.geometry("300x200")

        # Add logo image
        logo_path = get_image_path('logo3.png')
        self.logo = tk.PhotoImage(file=logo_path)
        self.logo = self.logo.subsample(10, 10)
        self.logo_label = tk.Label(master=self.root, image=self.logo)
        self.logo_label.image = self.logo  # Keep a reference to prevent garbage collection
        self.logo_label.pack(pady=5)

        # Add status text
        self.text_label = tk.Label(self.root, text="Segmenting and extracting .STL mesh...")
        self.text_label.pack(pady=5)
        
        
        # Schedule segmentation to start after the window opens
        self.start()
        self.root.after(1000, self.segment_to_stl)

    def start(self):
        """Start the main UI loop."""
        tk.mainloop()
        
    def close(self):
        """Close the UI window."""
        self.root.destroy()
        
    def segment_to_stl(self):
        """
        Process the image and convert it to an STL mesh.
        
        This method:
        1. Applies image filters (anisotropic smoothing, thresholding, median filter)
        2. Converts to a VTK mesh
        3. Cleans, smooths, and saves the mesh
        4. Updates the UI with helmet selection options
        """        
        # Processing parameters
        anisotropic_smoothing = True
        thresholds = [-300., -200., 400., 2000.]  # Thresholds for skin in HU
        median_filter = True
        connectivity_filter = True
    
        # Downsample image for performance
        img = self.img[::2, ::2, ::2]
    
        # Apply anisotropic smoothing to preserve edges
        if anisotropic_smoothing:
            print("Applying Anisotropic Smoothing")
            pixel_type = img.GetPixelID()
            img = sitk.Cast(img, sitk.sitkFloat32)
            img = sitk.CurvatureAnisotropicDiffusion(img, .012)
            img = sitk.Cast(img, pixel_type)
    
        # Apply double threshold filter
        if len(thresholds) == 4:
            print(f"Applying Double Threshold: {thresholds}")
            img = sitk.DoubleThreshold(
                img, thresholds[0], thresholds[1], thresholds[2], thresholds[3],
                255, 0)
            isovalue = 64.0
        
        # Apply median filter
        if median_filter:
            print("Applying Median filter")
            median_filter_val = 15
            # Filter twice to fill in ear holes
            median_smooth = sitk.Median(img, [median_filter_val, median_filter_val, median_filter_val])
            median_detail = sitk.Median(img, [2, 2, 2])
            img = sitk.Add(median_smooth, median_detail)

        # Pad the image
        stats = sitk.StatisticsImageFilter()
        stats.Execute(img)
        min_val = stats.GetMinimum()
        pad = [5, 5, 5]
        img = sitk.ConstantPad(img, pad, pad, min_val)
    
        # Convert to VTK image and extract surface
        vtkimg = sitk_utils.sitk2vtk(img)
        mesh = vtk_utils.extractSurface(vtkimg, isovalue)
        vtkimg = None
        
        # Clean the mesh
        mesh2 = vtk_utils.cleanMesh(mesh, connectivity_filter)
        mesh = None
        
        # Remove small objects
        mesh_cleaned_parts = vtk_utils.removeSmallObjects(mesh2, .99)
        mesh2 = None
        
        # Smooth the mesh
        mesh3 = vtk_utils.smoothMesh(mesh_cleaned_parts, nIterations=500)
        mesh_cleaned_parts = None
        
        # Save the mesh
        vtk_utils.writeMesh(mesh3, self.output_dir)
        
        # Update UI with completion status and helmet options
        self._show_helmet_selection()
    
    def _show_helmet_selection(self):
        """Show helmet selection UI after segmentation is complete."""
        # Add completion label
        self.done_label = tk.Label(
            self.root, 
            text="DONE! Select helmet then click below to continue to helmet subtraction."
        )
        self.done_label.pack(pady=5)
        
        # Get available helmet templates from templates directory
        import os
        template_dir = 'templates/'
        helmet_options = os.listdir(template_dir)
        
        # Default is flat helmet if available, otherwise first option
        self.helmet_selection = tk.StringVar()
        default_helmet = 'Flat_helmet.STL'
        if default_helmet in helmet_options:
            self.helmet_selection.set(default_helmet)
        elif helmet_options:
            self.helmet_selection.set(helmet_options[0])
        else:
            # Add a default option if no templates found
            helmet_options = ['No templates found']
            self.helmet_selection.set(helmet_options[0])
        
        # Create dropdown menu
        self.dropdown = tk.OptionMenu(self.root, self.helmet_selection, *helmet_options)
        self.dropdown.pack(pady=5)
        
        # Add continue button
        self.continue_button = tk.Button(
            self.root, 
            text='Continue', 
            command=self.run_mesh_manipulation_window
        )
        self.continue_button.pack(pady=5)
    
    def run_mesh_manipulation_window(self):
        """
        Launch the mesh manipulation window with the selected helmet.
        
        This method:
        1. Closes the current window
        2. Gets the selected helmet and mesh paths
        3. Sets up a Qt application
        4. Launches the mesh manipulation window
        """
        # Close current window
        self.root.destroy()
        
        # Get file paths
        selected_helmet = self.helmet_selection.get()
        helmet_mesh_file = get_template_path(selected_helmet)
        head_mesh_file = self.output_dir
        
        # Set up Qt application
        if not QtWidgets.QApplication.instance():
            app = QtWidgets.QApplication(sys.argv)
        else:
            app = QtWidgets.QApplication.instance()
            
        app.setQuitOnLastWindowClosed(True)
        
        # Launch mesh manipulation window with parameters determined by helmet type
        if 'winged' in helmet_mesh_file.lower():
            window = MeshManipulationWindow(
                helmet_mesh_file, 
                head_mesh_file, 
                self.animal_name,
                helmet_type='PET'
            )
        else:
            window = MeshManipulationWindow(
                helmet_mesh_file, 
                head_mesh_file, 
                self.animal_name
            )
            
        window.run()
        sys.exit(app.exec_())