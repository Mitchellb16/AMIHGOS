#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk
from PyQt5 import QtWidgets
import SimpleITK as sitk
import pyvista as pv

from utils import sitk2vtk
from utils import vtkutils
from utils.mesh_manipulationv2 import MeshManipulationWindow

# Model: Handles data and business logic
class SegmentationModel:
    def __init__(self, img, animal_name):
        self.img = img
        self.animal_name = animal_name
        self.output_dir = f'head_stls/{animal_name}.stl'
        self.helmet_options = ['templates/Flat_helmet.STL', 'templates/winged_helmet.stl']
        self.selected_helmet = self.helmet_options[0]
    
    def segment_image(self, progress_callback=None):
        """Process the image and generate a mesh"""
        # Segmentation parameters
        anisotropic_smoothing = True
        thresholds = [-300., -200., 400., 2000.]  # thresholds for skin in HU 
        median_filter = True
        connectivity_filter = True
        
        # Downsample image for performance
        img = self.img[::2, ::2, ::2]
        
        if progress_callback:
            progress_callback("Applying filters...")
        
        # Apply anisotropic smoothing
        if anisotropic_smoothing:
            pixel_type = img.GetPixelID()
            img = sitk.Cast(img, sitk.sitkFloat32)
            img = sitk.CurvatureAnisotropicDiffusion(img, .012)
            img = sitk.Cast(img, pixel_type)
        
        # Apply double threshold filter
        if len(thresholds) == 4:
            img = sitk.DoubleThreshold(
                img, thresholds[0], thresholds[1], thresholds[2], thresholds[3],
                255, 0)
            isovalue = 64.0
        
        # Apply median filter
        if median_filter:
            if progress_callback:
                progress_callback("Applying median filter...")
            median_filter_val = 15
            median_smooth = sitk.Median(img, [median_filter_val, median_filter_val, median_filter_val])
            median_detail = sitk.Median(img, [2, 2, 2])
            img = sitk.Add(median_smooth, median_detail)
        
        # Pad the image
        stats = sitk.StatisticsImageFilter()
        stats.Execute(img)
        min_val = stats.GetMinimum()
        pad = [5, 5, 5]
        img = sitk.ConstantPad(img, pad, pad, min_val)
        
        # Convert to mesh
        if progress_callback:
            progress_callback("Extracting surface...")
        vtkimg = sitk2vtk.sitk2vtk(img)
        mesh = vtkutils.extractSurface(vtkimg, isovalue)
        vtkimg = None
        
        # Clean mesh
        if progress_callback:
            progress_callback("Cleaning mesh...")
        mesh2 = vtkutils.cleanMesh(mesh, connectivity_filter)
        mesh = None
        
        # Remove small objects
        mesh_cleaned_parts = vtkutils.removeSmallObjects(mesh2, .99)
        mesh2 = None
        
        # Smooth mesh
        if progress_callback:
            progress_callback("Smoothing mesh...")
        mesh3 = vtkutils.smoothMesh(mesh_cleaned_parts, nIterations=500)
        mesh_cleaned_parts = None
        
        # Save the final mesh
        if progress_callback:
            progress_callback("Saving mesh...")
        vtkutils.writeMesh(mesh3, self.output_dir)
        
        return self.output_dir
    
    def set_helmet(self, helmet_path):
        """Set the selected helmet"""
        self.selected_helmet = helmet_path

# View: Handles UI elements
class SegmentationView:
    def __init__(self, master):
        self.root = master
        self.root.title("Segmentation Tool")
        self.root.geometry("400x300")
        self.setup_ui()
        
    def setup_ui(self):
        """Create initial UI elements"""
        # Add logo image
        self.logo = tk.PhotoImage(file='images/logo3.png')
        self.logo = self.logo.subsample(10, 10)
        self.logo_label = tk.Label(master=self.root, image=self.logo)
        self.logo_label.image = self.logo
        self.logo_label.pack(pady=10)
        
        # Progress label
        self.status_label = tk.Label(self.root, text="Initializing...")
        self.status_label.pack(pady=5)
        
        # Progress will be added here dynamically
        
    def update_status(self, message):
        """Update the status message"""
        self.status_label.config(text=message)
        self.root.update()
        
    def show_completion(self, helmet_options, on_continue, on_helmet_change):
        """Show completion UI with helmet options"""
        # Clear previous widgets
        for widget in self.root.winfo_children():
            if widget != self.logo_label:
                widget.destroy()
                
        # Completion message
        self.done_label = tk.Label(
            self.root, 
            text="DONE! Select helmet then click below to continue to helmet subtraction."
        )
        self.done_label.pack(pady=5)
        
        # Helmet selection dropdown
        self.helmet_var = tk.StringVar()
        self.helmet_var.set(helmet_options[0])
        self.helmet_var.trace('w', lambda *args: on_helmet_change(self.helmet_var.get()))
        
        self.dropdown = tk.OptionMenu(self.root, self.helmet_var, *helmet_options)
        self.dropdown.pack(pady=10)
        
        # Continue button
        self.continue_button = tk.Button(
            self.root, 
            text='Continue', 
            command=on_continue
        )
        self.continue_button.pack(pady=10)

# Controller: Coordinates model and view
class SegmentationController:
    def __init__(self, img, animal_name):
        self.model = SegmentationModel(img, animal_name)
        
        # Create Tkinter root
        self.root = tk.Tk()
        self.view = SegmentationView(self.root)
        
        # Schedule segmentation to start after UI is displayed
        self.root.after(1000, self.start_segmentation)
        
    def start_segmentation(self):
        """Begin the segmentation process"""
        try:
            # Run segmentation with progress updates
            self.model.segment_image(progress_callback=self.view.update_status)
            
            # Show completion UI
            self.view.show_completion(
                self.model.helmet_options,
                on_continue=self.run_mesh_manipulation,
                on_helmet_change=self.model.set_helmet
            )
        except Exception as e:
            self.view.update_status(f"Error: {str(e)}")
            
    def run_mesh_manipulation(self):
        """Launch the mesh manipulation window"""
        self.root.destroy()
        
        # Set up Qt application
        if not QtWidgets.QApplication.instance():
            app = QtWidgets.QApplication(sys.argv)
        else:
            app = QtWidgets.QApplication.instance()
        
        app.setQuitOnLastWindowClosed(True)
        
        # Create and run mesh manipulation window
        window = MeshManipulationWindow(
            self.model.selected_helmet, 
            self.model.output_dir, 
            self.model.animal_name
        )
        window.run()
        sys.exit(app.exec_())
        
    def run(self):
        """Start the main application loop"""
        self.root.mainloop()

# Example usage
if __name__ == '__main__':
    # For direct script execution 
    if os.path.basename(os.getcwd()) != os.path.dirname(os.path.abspath(__file__)):
        os.chdir('../')
        
    img = sitk.ReadImage('nifti_files/registered/JORAH_registered.nii.gz')
    animal_name = 'TEST'
    
    controller = SegmentationController(img, animal_name)
    controller.run()