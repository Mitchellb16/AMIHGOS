#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 18 15:43:53 2023

@author: mitchell
"""
import os
# Example usage
if __name__ == '__main__':
    os.chdir('../')

import SimpleITK as sitk
import pyvista as pv
import sys
import tkinter as tk
from PyQt5 import QtWidgets
from utils import sitk2vtk
from utils import vtkutils
from utils.mesh_manipulationv2 import MeshManipulationWindow

class SegmentationScreen:
    def __init__(self, img, animal_name):
        self.img = img
        self.animal_name = animal_name
        self.root = tk.Tk()
        self.root.title("Loading...")
        self.root.geometry("300x200")

        # Add logo image
        self.logo = tk.PhotoImage(file='images/logo3.png')
        self.logo = self.logo.subsample(10,10)
        self.logo_label = tk.Label(master=self.root, image=self.logo)
        self.logo_label.image = self.logo

        self.text_label = tk.Label(self.root, text="Segmenting and extracting .STL mesh...")
        self.text_label.pack(pady=5)
        
        # set segmentation to start after the window opens 
        self.root.after(1000, self.segment_to_stl)
        
        # start window
        self.start()

    def start(self):
        tk.mainloop()
        
    def close(self):
        self.root.destroy()
        
    def segment_to_stl(self):
        self.output_dir = 'head_stls/' + self.animal_name + '.stl'
        anisotropicSmoothing = True
        thresholds = [-300., -200., 400., 2000.] # this thresholds for skin in HU 
        medianFilter=True
        connectivityFilter = True
    
        # Downsample image, we don't need high resolution detail 
        img = self.img[::2, ::2, ::2]
    
        # Apply anisotropic smoothing to the volume image.  That's a smoothing filter
        # that preserves edges.

        if anisotropicSmoothing:
            print("Anisotropic Smoothing")
            pixelType = img.GetPixelID()
            img = sitk.Cast(img, sitk.sitkFloat32)
            img = sitk.CurvatureAnisotropicDiffusion(img, .012)
            img = sitk.Cast(img, pixelType)
        
# =============================================================================
#         # testing
#         sitk.WriteImage(img, 'nifti_files/anisotropic_smooth.nii')
# =============================================================================
    
        # Apply the double threshold filter to the volume
        #
        if len(thresholds) == 4:
            print("Double Threshold: ", thresholds)
            img = sitk.DoubleThreshold(
                img, thresholds[0], thresholds[1], thresholds[2], thresholds[3],
                255, 0)
            isovalue = 64.0
        
        # Apply a N*N*N median filter.  
        if medianFilter:
            print("Median filter")
            median_filter_val = 15
            # we filter twice to fill in the ear holes
            median_smooth = sitk.Median(img, [median_filter_val, median_filter_val, median_filter_val])
            median_detail = sitk.Median(img,[2,2,2])
            img = sitk.Add(median_smooth, median_detail)
            
        # testing
# =============================================================================
#         sitk.WriteImage(img, f'nifti_files/median_added.nii')
# =============================================================================

        # Get the minimum image intensity for padding the image
        #
        stats = sitk.StatisticsImageFilter()
        stats.Execute(img)
        minVal = stats.GetMinimum()
    
        # Pad black to the boundaries of the image
        #
        pad = [5, 5, 5]
        img = sitk.ConstantPad(img, pad, pad, minVal)
    
        vtkimg = sitk2vtk.sitk2vtk(img)
        mesh = vtkutils.extractSurface(vtkimg, isovalue)
# =============================================================================
#         vtkutils.writeMesh(mesh, 'head_stls/original.stl')
# =============================================================================
        vtkimg = None
        mesh2 = vtkutils.cleanMesh(mesh, connectivityFilter)
        mesh = None
# =============================================================================
#         vtkutils.writeMesh(mesh2, 'head_stls/cleaned.stl')
# =============================================================================
        mesh_cleaned_parts =  vtkutils.removeSmallObjects(mesh2, .99)
        mesh2 = None
# =============================================================================
#         vtkutils.writeMesh(mesh_cleaned_parts, 'head_stls/small_obj.stl')
# =============================================================================
        mesh3 = vtkutils.smoothMesh(mesh_cleaned_parts, nIterations=500)
        mesh_cleaned_parts = None
        
       
# =============================================================================
#         vtkutils.writeMesh(mesh3, 'head_stls/smoothed.stl')
# =============================================================================
    
# =============================================================================
#         mesh4 = vtkutils.reduceMesh(mesh3, .97)
#         mesh3 = None
# =============================================================================
        
        vtkutils.writeMesh(mesh3, self.output_dir)
        
        self.done_label = tk.Label(self.root, text="DONE! Select helmet then click below to continue to helmet subtraction.")
        self.done_label.pack(pady=5)
        
        # define helmet options for dropdown
        helmet_options = ['templates/Flat_helmet.STL', 'templates/winged_helmet.stl']
        
        # default is flat helmet
        self.helmet_selection = tk.StringVar()
        self.helmet_selection.set('templates/Flat_helmet.STL')
        
        self.dropdown = tk.OptionMenu(self.root, self.helmet_selection, *helmet_options)
        self.dropdown.pack()
        
        # add continue button
        self.continue_button = tk.Button(self.root, 
                                         text = 'Continue', 
                                         command = self.run_mesh_manipulation_window)
        self.continue_button.pack()
          
    
    def run_mesh_manipulation_window(self):
        self.root.destroy()
        helmet_mesh_file = self.helmet_selection.get()
        head_mesh_file = self.output_dir
        
        # run mesh manipulation window
        # setting up Qt application stuff
        if not QtWidgets.QApplication.instance():
            app = QtWidgets.QApplication(sys.argv)
        else:
            app = QtWidgets.QApplication.instance()
        app.setQuitOnLastWindowClosed(True) 
        window = MeshManipulationWindow(helmet_mesh_file, head_mesh_file, self.animal_name)
        window.run()
        sys.exit(app.exec_())

 
# Example usage
if __name__ == '__main__':
    img = sitk.ReadImage('nifti_files/registered/JORAH_registered.nii.gz')
    animal_name = 'TEST'
    seg_screen = SegmentationScreen(img, animal_name)
# =============================================================================
#     seg_screen.run_mesh_manipulation_window()
# =============================================================================
