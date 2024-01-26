#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov  5 14:22:21 2022

@author: mitchell
"""
import os
from datetime import date
import pyvista as pv
import tkinter as tk
from pyvistaqt import BackgroundPlotter
# Change this to true then modify head_file and name if you want to run this on
# a head stl that has already been segmented
separate = True
PET_restrainer = False

if separate:
    scaling = 1.15
    head_file = '/home/mitchell/Documents/Projects/CT_helmets/AMIHGOS/head_stls/JORAH.stl'
    name = "JORAH"

class MeshManipulationWindow:
    def __init__(self, helmet_mesh, head_mesh):
    
        self.root = tk.Tk()
        self.root.title("Mesh Manipulation Controls")
        self.helmet_mesh = helmet_mesh
        self.head_mesh = head_mesh

        self.scaling_factor = 1.0
        self.subtraction_button_pressed = False  # Flag to track if the subtraction button has been pressed

        # Plot button
        plot_button = tk.Button(self.root, text="Plot meshes", command=self.create_pvplotter)
        plot_button.pack()

        # Rotation button
        rotate_button = tk.Button(self.root, text="Rotate", command=self.rotate_mesh)
        rotate_button.pack()
    
        # Expansion buttons
        expand_frame = tk.Frame(self.root)
        expand_frame.pack()
        minus_button = tk.Button(expand_frame, text="-", command=self.expand_mesh_minus)
        minus_button.grid(row=0, column=0)
        self.scaling_label = tk.Label(expand_frame, text=f"{self.scaling_factor:.2f}")
        self.scaling_label.grid(row=0, column=1)
        plus_button = tk.Button(expand_frame, text="+", command=self.expand_mesh_plus)
        plus_button.grid(row=0, column=2)
    
        # Translation button
        translate_button = tk.Button(self.root, text="Translate", command=self.translate_mesh)
        translate_button.pack()
        
        # Send for subtraction button (green)
        send_button = tk.Button(self.root, text="Send for subtraction", command=self.send_for_subtraction, bg="green")
        send_button.pack()
        
        # Save button (greyed out initially)
        self.save_button = tk.Button(self.root, text="Save", command=self.save_mesh, state=tk.DISABLED, bg="grey")
        self.save_button.pack()
    
        # Close button
        close_button = tk.Button(self.root, text="Close", command=self.close_window)
        close_button.pack()
       
        
        
    def create_pvplotter(self):
        # display the mesh
        # every once in a while this starts crashing, just restart computer to solve
        self.plotter = BackgroundPlotter(off_screen = False, notebook=False)
        self.plotter.add_mesh(self.helmet_mesh)
        self.plotter.add_mesh(self.head_mesh)
        self.plotter.show_bounds(
                grid='front',
                location='outer',
                all_edges=True,
            )
        self.plotter.show()

    def rotate_mesh(self):
        # Implement your rotation logic here
        self.update_plotter()
        

    def expand_mesh_plus(self):
        # Increase the scaling factor by 0.1
        self.scaling_factor += 0.01
        self.scaling_label.config(text=f"{self.scaling_factor:.2f}")
        # Implement your expansion logic here
        # Implement your expansion logic here
        head_mesh.scale([self.scaling_factor,
                         self.scaling_factor,
                         self.scaling_factor],
                        inplace=True)
        self.update_plotter()

    def expand_mesh_minus(self):
        # Decrease the scaling factor by 0.1, but ensure it stays positive
        self.scaling_factor = max(1, self.scaling_factor - 0.01)
        self.scaling_label.config(text=f"{self.scaling_factor:.2f}")
        # Implement your expansion logic here
        head_mesh.scale([self.scaling_factor,
                         self.scaling_factor,
                         self.scaling_factor],
                        inplace=True)
        # update the plot
        self.update_plotter()

    def translate_mesh(self):
        # Implement your translation logic here
        self.update_plotter()
        
    
    def send_for_subtraction(self):
        # Implement logic to send the mesh for subtraction
        bool_mesh = self.helmet_mesh.boolean_difference(self.head_mesh)
        # clip out the region of the helmet that becomes sharp 
        bounds = [-21, 20, -20, 20, -18, -3]
        # this is the helmet - the sharp part
        clipped = bool_mesh.clip_box(bounds)
        
        # this is the sharp part
        clipping = bool_mesh.clip_box(bounds, invert=False)
        
        # smoothing
        surface = clipping.extract_geometry()
        smooth = surface.smooth_taubin(n_iter=70, pass_band = .04,
                                       non_manifold_smoothing=True, normalize_coordinates=True)
        smooth.fill_holes(hole_size = 20, inplace=True)
        
        # add back to the clipped mesh
        self.final_mesh = clipped + smooth
    
    def save_mesh(self):
        # Implement logic to save the mesh
        self.final_mesh.extract_geometry().save(self.save_file)
        
    
    def update_plotter(self):
        # get current states of all the transformers and plot the meshes
        self.plotter.update()
        
    def close_window(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()
    
 
def mesh_sub(head_mesh, name='Example', separate = False, PET_restrainer = False, scaling = 1.15):
    """
    Given pyvista mesh of head stl, return a subtraction of the head from 
    the helmet template

    Returns
    -------
    helmet_mesh: pyvista mesh

    """
    # these strings need to be the relative directories of the template helmets
    if separate == True:
        if PET_restrainer:
# =============================================================================
#             mesh_file = '../templates/helmet_remeshed_v2.stl'
# =============================================================================
            mesh_file = '../templates/headpost_helmet_template.stl'
        else:
            mesh_file = '../templates/helmet_top_BST3_v3.STL'
# =============================================================================
#             mesh_file = '../templates/Template_flat_Helmet_2023_Top.STL'
# =============================================================================
        save_file = f'../helmets/{str(date.today()) + name +str(scaling)[-2:]}.stl'
    else: 
        mesh_file = './templates/helmet_top_BST3_v3.STL'
        save_file = f'./helmets/{str(date.today()) + name}.stl'
    animal_name = name
    helmet_mesh = pv.read(mesh_file).triangulate(inplace = True)
    
    
    # scale up and rotate head mesh
    # LR, PA, DV
    head_mesh.scale([1.20,scaling,scaling], inplace=True)
    head_mesh.rotate_x(290, inplace=True)
    head_mesh = head_mesh.decimate(.5)
    
# =============================================================================
#     # rotate helmet mesh
#     helmet_mesh.rotate_x(90, inplace=True)
#     helmet_mesh.rotate_z(90, inplace = True)
# =============================================================================
    
    # align the centers of both meshes at 0 then translate 
    helmet_mesh.points -= helmet_mesh.center
    head_mesh.points -= head_mesh.center
    head_test = head_mesh.copy()
    # format [LR, PA, DV] or [X, Y, Z]
    # therefor bounds[2] is the back of the head, which we are aligning to the
    # back of the helmet, then nudging it forward a little
    LR_offset = .7
    PA_offset = 3
    DV_offset = -3.5
    
    offset = [LR_offset,
              helmet_mesh.bounds[2]-head_mesh.bounds[2]+PA_offset, # 3
              helmet_mesh.bounds[-1]-head_mesh.bounds[-1] + DV_offset] #3.5
    
    head_mesh.points += offset
    
    # create text object for embossing
    text = pv.Text3D(animal_name, depth=.9)
    text.scale([2.5,2.5,2.5], inplace = True)
    text.rotate_z(90, inplace=True)
    if PET_restrainer:
        text_offset = [28,-3,-12.5] #12.5
    else:
        text_offset = [28,-3,-15.5]
    text.points += text_offset
    
    # add text to helmet and chin to emboss
    helmet_mesh = helmet_mesh + text
    
# =============================================================================
#     # display the mesh
#     # every once in a while this starts crashing, just restart computer to solve
#     plotter = pv.Plotter(off_screen = False, notebook=False)
#     plotter.add_mesh(helmet_mesh)
#     plotter.add_mesh(head_mesh)
#     plotter.show_bounds(
#             grid='front',
#             location='outer',
#             all_edges=True,
#         )
# =============================================================================
#     plotter.show()
# =============================================================================
# =============================================================================
    
    
    # Tkinter window with buttons for rotation, expansion, and translation
    # Create an instance of MeshManipulationWindow
    manipulation_window = MeshManipulationWindow(helmet_mesh, head_mesh)
    manipulation_window.run()
    
    
# =============================================================================
#     plotter2 = pv.Plotter(off_screen=False, notebook = False)
#     bool_mesh = helmet_mesh.boolean_difference(head_mesh)
#     # clip out the region of the helmet that becomes sharp 
#     bounds = [-21, 20, -20, 20, -18, -3]
#     # this is the helmet - the sharp part
#     clipped = bool_mesh.clip_box(bounds)
#     
#     # this is the sharp part
#     clipping = bool_mesh.clip_box(bounds, invert=False)
#     
#     # smoothing
#     surface = clipping.extract_geometry()
#     smooth = surface.smooth_taubin(n_iter=70, pass_band = .04,
#                                    non_manifold_smoothing=True, normalize_coordinates=True)
#     smooth.fill_holes(hole_size = 20, inplace=True)
#     
#     # add back to the clipped mesh
#     final_mesh = clipped + smooth
#     
#     # save and plot mesh          
#     final_mesh.extract_geometry().save(save_file)
#     plotter2.add_mesh(final_mesh)
#     # offset the unsmoothed mesh for comparison
#     bool_mesh.points += [0,0,50]
#     plotter2.add_mesh(bool_mesh)
#     plotter2.show_bounds(
#             grid='front',
#             location='outer',
#             all_edges=True,
#         )
#     plotter2.show()
#     
#     return helmet_mesh, head_test
# =============================================================================

if separate:
    for scale_val in [scaling]:
# =============================================================================
#         try:
# =============================================================================
        head_mesh = pv.read(head_file)
        _, test = mesh_sub(head_mesh, name, separate, PET_restrainer=PET_restrainer, scaling=scale_val)
# =============================================================================
#         except:
#             print("Looks like you are running this separately! If not, change separate to False.")
# =============================================================================
