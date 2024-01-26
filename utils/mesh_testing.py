#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov  5 14:22:21 2022

@author: mitchell
"""
from datetime import date
import pyvista as pv

# change this to True and change the head_file and name variables if you want to 
# run this script on a head stl that has already been generated
separate = True
if separate:
    head_file = '/home/mitchell/Documents/Projects/CT_helmets/AMIHGOS/head_stls/M279_16.stl'
    name = "Colorado"
    head_mesh = pv.read(head_file)
def mesh_sub(head_mesh, name='Example', separate = False):
    """
    Given pyvista mesh of head stl, return a subtraction of the head from 
    the helmet template

    Returns
    -------
    helmet_mesh: pyvista mesh

    """
    if separate:
        mesh_file = '../templates/helmet_top_BST3_v3.STL'
        save_file = f'../helmets/{str(date.today()) + name}.stl'
    else:
        mesh_file = '../templates/helmet_remeshed_v2.stl'
        save_file = '../helmets/{str(date.today()) + name}.stl'
    animal_name = name
    helmet_mesh = pv.read(mesh_file).triangulate(inplace = True)
    
    
    # scale up and rotate head mesh
    head_mesh.scale([1.12,1.05,1.05], inplace=True)
    head_mesh.rotate_x(290, inplace=True)
    head_mesh = head_mesh.decimate(.5)
    
    # rotate helmet mesh
    helmet_mesh.rotate_x(0, inplace=True)
    helmet_mesh.rotate_z(0, inplace = True)
    
    # align the centers of both meshes at 0 then translate 
    helmet_mesh.points -= helmet_mesh.center
    head_mesh.points -= head_mesh.center
    head_test = head_mesh.copy()
    # format [LR, PA, DV] or [X, Y, Z]
    # therefor bounds[2] is the back of the head, which we are aligning to the
    # back of the helmet, then nudging it forward a little
    offset = [.1,
              helmet_mesh.bounds[2]-head_mesh.bounds[2] + 3,
              helmet_mesh.bounds[-1]-head_mesh.bounds[-1] - 5]
    
    head_mesh.points += offset
    
    # create text object for embossing
    text = pv.Text3D(animal_name, depth=.9)
    text.scale([2.5,2.5,2.5], inplace = True)
    text.rotate_z(90, inplace=True)
    text_offset = [28,-3,-15.5]
    text.points += text_offset
    
    # add text to helmet and chin to emboss
    helmet_mesh = helmet_mesh + text
    
    # display the mesh
    # every once in a while this starts crashing, just restart computer to solve
    plotter = pv.Plotter(off_screen = False, notebook=False)
    plotter.add_mesh(helmet_mesh)
    plotter.add_mesh(head_mesh)
    plotter.show_bounds(
            grid='front',
            location='outer',
            all_edges=True,
        )
    plotter.show()
    
    plotter2 = pv.Plotter(off_screen=False, notebook = False)
    bool_mesh = helmet_mesh.boolean_difference(head_mesh)
                
    bool_mesh.save(save_file)
    plotter2.add_mesh(bool_mesh)
    plotter2.show()
    
    return helmet_mesh, head_test
if separate:
    _, test = mesh_sub(head_mesh, name, separate = separate)