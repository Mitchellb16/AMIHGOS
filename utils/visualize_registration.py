#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun  2 11:09:06 2023

@author: mitchell
"""

import tkinter as tk
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
testing = False

def visualize_registration(fixed, moving, root):
    """
    

    Parameters
    ----------
    fixed : Fixed (template) image, loaded by simpleITK
        
    moving : Moving image after registration
        

    Returns
    -------
    None.

    """
    # Create a tkinter window
    window = tk.Toplevel(root)
    window.title("Registration Confirmation")

    # Create a figure and axes to display the image
    fig, ax = plt.subplots(figsize=(6, 6))

    # Create the canvas and pack it into the tkinter window
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.get_tk_widget().pack()

    # Initial values for image_z and alpha
    image_z = 0
    alpha = 0.5

    def display_images_with_alpha(image_z, alpha, fixed, moving):
        fixed_np = sitk.GetArrayViewFromImage(fixed)
        moving_np = sitk.GetArrayViewFromImage(moving)

        img = (1.0 - alpha) * fixed_np[:, :, image_z] + alpha * moving_np[:, :, image_z]

        # Clear the previous plot
        ax.clear()

        # Plot the image
        ax.imshow(img, cmap='gray')
        ax.axis('off')

        # Update the canvas with the new figure
        canvas.draw()

    # Display the initial image
    display_images_with_alpha(image_z, alpha, fixed, moving)

    # Update the displayed image when sliders change
    def update_image(*args):
        display_images_with_alpha(image_slider.get(), alpha_slider.get(), fixed, moving)

    # Create sliders for image_z and alpha
    image_slider = tk.Scale(window, from_=0, to=fixed.GetDepth() - 1, 
                            orient=tk.HORIZONTAL, command=update_image, label='Image Z')
    image_slider.pack()

    alpha_slider = tk.Scale(window, from_=0.0, to=1.0, resolution=0.05,
                            orient=tk.HORIZONTAL, command=update_image, label='Alpha')
    alpha_slider.pack()


if testing == True:
    # Example usage
    fixed_dir = '/home/mitchell/Documents/Projects/CT_helmets/Data/template_largeFOV_CT.nii.gz'
    moving_dir = '/home/mitchell/Documents/Projects/CT_helmets/AMIHGOS/nifti_files/registered/M1_16_C0_registered.nii.gz'
    fixed_image = sitk.DICOMOrient(sitk.ReadImage(fixed_dir, sitk.sitkFloat32), 'LPS')
    moving_image = sitk.DICOMOrient(sitk.ReadImage(moving_dir, sitk.sitkFloat32), 'LPS')
    
    visualize_registration(fixed_image, moving_image)

