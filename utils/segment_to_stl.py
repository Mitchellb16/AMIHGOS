#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 18 15:43:53 2023

@author: mitchell
"""
import SimpleITK as sitk
import pyvista as pv
import sys

from pyvistaqt import BackgroundPlotter

from PyQt5 import QtWidgets
from . import sitk2vtk
from . import vtkutils
from .mesh_manipulationv2 import MeshManipulationWindow

def segment_to_stl(img, animal_name):
    output_dir = 'head_stls/' + animal_name + '.stl'
    anisotropicSmoothing = True
    thresholds = [-300., -200., 400., 2000.] # this thresholds for skin in HU 
    medianFilter=True
    connectivityFilter = True

    # Downsample image, we don't need high resolution detail 
    img = img[::2, ::2, ::2]

    # Apply anisotropic smoothing to the volume image.  That's a smoothing filter
    # that preserves edges.
    #
    if anisotropicSmoothing:
        print("Anisotropic Smoothing")
        pixelType = img.GetPixelID()
        img = sitk.Cast(img, sitk.sitkFloat32)
        img = sitk.CurvatureAnisotropicDiffusion(img, .012)
        img = sitk.Cast(img, pixelType)

    # Apply the double threshold filter to the volume
    #
    if len(thresholds) == 4:
        print("Double Threshold: ", thresholds)
        img = sitk.DoubleThreshold(
            img, thresholds[0], thresholds[1], thresholds[2], thresholds[3],
            255, 0)
        isovalue = 64.0
    
    # Apply a N*N*N median filter.  
    #
    if medianFilter:
        print("Median filter")
        img = sitk.Median(img, [15, 15, 15])
    #
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
    vtkimg = None
    mesh2 = vtkutils.cleanMesh(mesh, connectivityFilter)
    mesh = None

    mesh_cleaned_parts =  vtkutils.removeSmallObjects(mesh2, .99)
    mesh2 = None

    mesh3 = vtkutils.smoothMesh(mesh_cleaned_parts, nIterations=100)
    mesh_cleaned_parts = None

    mesh4 = vtkutils.reduceMesh(mesh3, .97)
    mesh3 = None

    vtkutils.writeMesh(mesh4, output_dir)
    
    # read mesh into pyvista object and call mesh function
    head_mesh = pv.read(output_dir)
    
    helmet_mesh_file = './templates/helmet_top_BST3_v3.STL'
    helmet_mesh = pv.read(helmet_mesh_file).triangulate(inplace = True)
    
    # run mesh manipulation window
    app = QtWidgets.QApplication(sys.argv)
    window = MeshManipulationWindow(helmet_mesh, head_mesh)
    window.run()
    sys.exit(app.exec_())