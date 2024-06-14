#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 18 14:16:55 2023

@author: mitchell
"""

import SimpleITK as sitk
from tkinter import *
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.cm as cm
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, 
NavigationToolbar2Tk)
from .visualize_registration import visualize_registration
from .segment_to_stl import SegmentationScreen
from .sitk2vtk import *
from .vtkutils import *

class RegistrationPointDataAquisition(object):
    """
    ***Adapted from SIMPLEITK jupyter notebook tutorials
    This class provides a GUI for localizing corresponding points in two images, and for evaluating registration results using a linked cursor
    approach, user clicks in one image and the corresponding point is added to the other image.
    """

    def __init__(
        self,
        moving_image,
        window,
        root,
        fixed_window_level=None,
        moving_window_level=None,
        figure_size=(5, 4),
        known_transformation=None,
    ):
        self.window = window
        self.window.pack()
        self.root = root
        # location of the template file 
        fixed_dir = 'fixed_image/padded_template_image.nii.gz'
        self.fixed_image = sitk.ReadImage(fixed_dir, outputPixelType=sitk.sitkFloat32)
        self.fixed_image = sitk.DICOMOrient(self.fixed_image, 'RIA')
        
        (
            self.fixed_npa,
            self.fixed_min_intensity,
            self.fixed_max_intensity,
        ) = self.get_window_level_numpy_array(self.fixed_image, fixed_window_level)
        self.moving_image = moving_image
        (
            self.moving_npa,
            self.moving_min_intensity,
            self.moving_max_intensity,
        ) = self.get_window_level_numpy_array(self.moving_image, moving_window_level)
        self.fixed_point_indexes = []
        self.moving_point_indexes = []
        self.click_history = (
            []
        )  # Keep a history of user point localizations, enabling undo of last localization.
        self.known_transformation = known_transformation  # If the transformation is valid (not None) then corresponding points are automatically added.
        self.text_and_marker_color = "red"

        ui = self.create_ui()
      

        # Create a figure with two axes for the fixed and moving images.
        self.fixed_fig, self.fixed_axes = plt.subplots(1, 1, figsize=figure_size)
        self.moving_fig, self.moving_axes = plt.subplots(1, 1, figsize=figure_size)
        
        # put fixed and moving images in their frames
        self.fixed_canvas = FigureCanvasTkAgg(self.fixed_fig, self.fixed_frame)
        self.fixed_canvas.get_tk_widget().pack()
        
        self.moving_canvas = FigureCanvasTkAgg(self.moving_fig, self.moving_frame)
        self.moving_canvas.get_tk_widget().pack()
                
        # Connect the mouse button press to the canvas (__call__ method is the invoked callback).
        self.fixed_fig.canvas.mpl_connect("button_press_event", self)

        self.moving_fig.canvas.mpl_connect("button_press_event", self)

        # Display the data and the controls, first time we display the images is outside the "update_display" method
        # as that method relies on the previous zoom factor which doesn't exist yet.
        self.fixed_axes.imshow(
            self.fixed_npa[self.fixed_slider.get(), :, :]
            if self.fixed_slider
            else self.fixed_npa,
            cmap=plt.cm.Greys_r,
            vmin=self.fixed_min_intensity,
            vmax=self.fixed_max_intensity,
        )
        self.moving_axes.imshow(
            self.moving_npa[self.moving_slider.get(), :, :]
            if self.moving_slider
            else self.moving_npa,
            cmap=plt.cm.Greys_r,
            vmin=self.moving_min_intensity,
            vmax=self.moving_max_intensity,
        )
        self.update_display()

    def create_ui(self):
        # Create buttons for clearing and saving manual registration points
# =============================================================================
#         self.clearlast_button = Button(self.window,
#             text="Clear Last", command = self.clear_last
#         ).grid(column = 1, row = 1)
# 
#         self.clearall_button = Button(self.window,
#             text="Clear All", command = self.clear_all
#         ).grid(column = 1, row = 2)
#         
# =============================================================================
        self.save_points_button = Button(self.window, 
                                         text = 'Save Points and Register', 
                                         command = self.save_points).grid(column = 1, row = 3)
        
        # make frames to put each image and its slider into
        self.fixed_frame = Frame(self.window)
        self.fixed_frame.grid(column = 0, row = 2)
        self.moving_frame = Frame(self.window)
        self.moving_frame.grid(column = 3, row = 2)
        # Sliders are only created if a 3D image, otherwise no need.
        self.fixed_slider = self.moving_slider = None
        if self.fixed_npa.ndim == 3:
            self.fixed_slider = Scale(
                self.fixed_frame,
                from_=0,
                to=self.fixed_npa.shape[0] - 1,
                command = self.on_slice_slider_value_change,
            )
            self.fixed_slider.set(274)
            self.fixed_slider.pack()
            
            self.moving_slider = Scale(
                self.moving_frame,
                from_=0,
                to=self.moving_npa.shape[0] - 1,
                command = self.on_slice_slider_value_change,
            )
            self.moving_slider.set(140)
            self.moving_slider.pack()
        

    def get_window_level_numpy_array(self, image, window_level):
        """
        Get the numpy array representation of the image and the min and max of the intensities
        used for display.
        """
        npa = sitk.GetArrayViewFromImage(image)
        if not window_level:
            return npa, npa.min(), npa.max()
        else:
            return (
                npa,
                window_level[1] - window_level[0] / 2.0,
                window_level[1] + window_level[0] / 2.0,
            )

    def on_slice_slider_value_change(self, change):
        self.update_display()

    def update_display(self):
        """
        Display the two images based on the slider values, if relevant, and the points which are on the
        displayed slices.
        """
        # We want to keep the zoom factor which was set prior to display, so we log it before
        # clearing the axes.
        fixed_xlim = self.fixed_axes.get_xlim()
        fixed_ylim = self.fixed_axes.get_ylim()
        moving_xlim = self.moving_axes.get_xlim()
        moving_ylim = self.moving_axes.get_ylim()

        # Draw the fixed image in the first subplot and the localized points.
        self.fixed_axes.clear()
        self.fixed_axes.imshow(
            self.fixed_npa[self.fixed_slider.get(), :, :]
            if self.fixed_slider
            else self.fixed_npa,
            cmap=plt.cm.Greys_r,
            vmin=self.fixed_min_intensity,
            vmax=self.fixed_max_intensity,
        )
        # Positioning the text is a bit tricky, we position relative to the data coordinate system, but we
        # want to specify the shift in pixels as we are dealing with display. We therefore (a) get the data
        # point in the display coordinate system in pixel units (b) modify the point using pixel offset and
        # transform back to the data coordinate system for display.
        text_x_offset = -10
        text_y_offset = -10
        for i, pnt in enumerate(self.fixed_point_indexes):
            if (
                self.fixed_slider and int(pnt[2] + 0.5) == self.fixed_slider.get()
            ) or not self.fixed_slider:
                self.fixed_axes.scatter(
                    pnt[0], pnt[1], s=90, marker="+", color=self.text_and_marker_color
                )
                # Get point in pixels.
                text_in_data_coords = self.fixed_axes.transData.transform(
                    [pnt[0], pnt[1]]
                )
                # Offset in pixels and get in data coordinates.
                text_in_data_coords = self.fixed_axes.transData.inverted().transform(
                    (
                        text_in_data_coords[0] + text_x_offset,
                        text_in_data_coords[1] + text_y_offset,
                    )
                )
                self.fixed_axes.text(
                    text_in_data_coords[0],
                    text_in_data_coords[1],
                    str(i),
                    color=self.text_and_marker_color,
                )
        self.fixed_axes.set_title(
            f"fixed image - localized {len(self.fixed_point_indexes)} points"
        )
        self.fixed_axes.set_axis_off()

        # Draw the moving image in the second subplot and the localized points.
        self.moving_axes.clear()
        self.moving_axes.imshow(
            self.moving_npa[self.moving_slider.get(), :, :]
            if self.moving_slider
            else self.moving_npa,
            cmap=plt.cm.Greys_r,
            vmin=self.moving_min_intensity,
            vmax=self.moving_max_intensity,
        )
        for i, pnt in enumerate(self.moving_point_indexes):
            if (
                self.moving_slider and int(pnt[2] + 0.5) == self.moving_slider.get()
            ) or not self.moving_slider:
                self.moving_axes.scatter(
                    pnt[0], pnt[1], s=90, marker="+", color=self.text_and_marker_color
                )
                text_in_data_coords = self.moving_axes.transData.transform(
                    [pnt[0], pnt[1]]
                )
                text_in_data_coords = self.moving_axes.transData.inverted().transform(
                    (
                        text_in_data_coords[0] + text_x_offset,
                        text_in_data_coords[1] + text_y_offset,
                    )
                )
                self.moving_axes.text(
                    text_in_data_coords[0],
                    text_in_data_coords[1],
                    str(i),
                    color=self.text_and_marker_color,
                )
        self.moving_axes.set_title(
            f"moving image - localized {len(self.moving_point_indexes)} points"
        )
        self.moving_axes.set_axis_off()

        # Set the zoom factor back to what it was before we cleared the axes, and rendered our data.
        self.fixed_axes.set_xlim(fixed_xlim)
        self.fixed_axes.set_ylim(fixed_ylim)
        self.moving_axes.set_xlim(moving_xlim)
        self.moving_axes.set_ylim(moving_ylim)

        self.fixed_fig.canvas.draw_idle()
        self.moving_fig.canvas.draw_idle()

    def clear_all(self, button):
        """
        Get rid of all the data.
        """
        del self.fixed_point_indexes[:]
        del self.moving_point_indexes[:]
        del self.click_history[:]
        self.update_display()

    def clear_last(self, button):
        """
        Remove last point or point-pair addition (depends on whether the interface is used for localizing point pairs or
        evaluation of registration).
        """
        if self.click_history:
            if self.known_transformation:
                self.click_history.pop().pop()
            self.click_history.pop().pop()
            self.update_display()

    
    
    # This is the registration configuration which we use in all cases. The only parameter that we vary
    # is the initial_transform.
    def multires_registration(self, fixed_image, moving_image, initial_transform):
        registration_method = sitk.ImageRegistrationMethod()
        registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
        registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
        registration_method.SetMetricSamplingPercentage(0.1)
        registration_method.SetInterpolator(sitk.sitkLinear)
        registration_method.SetOptimizerAsGradientDescent(
            learningRate=1,
            numberOfIterations=1000,
            estimateLearningRate=registration_method.Once,
        )
        registration_method.SetOptimizerScalesFromPhysicalShift()
        registration_method.SetInitialTransform(initial_transform, inPlace=False)
    #     registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    #     registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    #     registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
        
     

        final_transform = registration_method.Execute(fixed_image, moving_image)
        print(f"Final metric value: {registration_method.GetMetricValue()}")
        print(
            f"Optimizer's stopping condition, {registration_method.GetOptimizerStopConditionDescription()}"
        )
        print(f"Final transformation: {final_transform.GetParameters()}")
        return (final_transform, registration_method.GetMetricValue())
    
    def get_points(self):
        """
        Get the points in the image coordinate systems.
        """
        
        if len(self.fixed_point_indexes) != len(self.moving_point_indexes):
            raise Exception(
                "Number of localized points in fixed and moving images does not match."
            )
        fixed_point_list = [
            self.fixed_image.TransformContinuousIndexToPhysicalPoint(pnt)
            for pnt in self.fixed_point_indexes
        ]
        moving_point_list = [
            self.moving_image.TransformContinuousIndexToPhysicalPoint(pnt)
            for pnt in self.moving_point_indexes
        ]
        return fixed_point_list, moving_point_list

    def __call__(self, event):
        """
        Callback invoked when the user clicks inside the figure.
        """
        # We add points only in 'edit' mode. If the spatial transformation between the two images is known, self.known_transformation was set,
        # then every button_press_event will generate a point in each of the images. Finally, we enforce that all points have a corresponding
        # point in the other image by not allowing the user to add multiple points in the same image, they have to add points by switching between
        # the two images.
        if event.inaxes == self.fixed_axes:
            if len(self.fixed_point_indexes) - len(self.moving_point_indexes) <= 0:
                self.fixed_point_indexes.append(
                    (event.xdata, event.ydata, self.fixed_slider.get())
                    if self.fixed_slider
                    else (event.xdata, event.ydata)
                )
                self.click_history.append(self.fixed_point_indexes)
                if self.known_transformation:
                    moving_point_physical = self.known_transformation.TransformPoint(
                        self.fixed_image.TransformContinuousIndexToPhysicalPoint(
                            self.fixed_point_indexes[-1]
                        )
                    )
                    moving_point_indexes = (
                        self.moving_image.TransformPhysicalPointToContinuousIndex(
                            moving_point_physical
                        )
                    )
                    self.moving_point_indexes.append(moving_point_indexes)
                    self.click_history.append(self.moving_point_indexes)
                    if self.moving_slider:
                        z_index = int(moving_point_indexes[2] + 0.5)
                        if (
                            self.moving_slider.max >= z_index
                            and self.moving_slider.min <= z_index
                        ):
                            self.moving_slider.set(z_index) 
                self.update_display()
        if event.inaxes == self.moving_axes:
            if len(self.moving_point_indexes) - len(self.fixed_point_indexes) <= 0:
                self.moving_point_indexes.append(
                    (event.xdata, event.ydata, self.moving_slider.get())
                    if self.moving_slider
                    else (event.xdata, event.ydata)
                )
                self.click_history.append(self.moving_point_indexes)
                if self.known_transformation:
                    inverse_transform = self.known_transformation.GetInverse()
                    fixed_point_physical = inverse_transform.TransformPoint(
                        self.moving_image.TransformContinuousIndexToPhysicalPoint(
                            self.moving_point_indexes[-1]
                        )
                    )
                    fixed_point_indexes = (
                        self.fixed_image.TransformPhysicalPointToContinuousIndex(
                            fixed_point_physical
                        )
                    )
                    self.fixed_point_indexes.append(fixed_point_indexes)
                    self.click_history.append(self.fixed_point_indexes)
                    if self.fixed_slider:
                        z_index = int(fixed_point_indexes[2] + 0.5)
                        if (
                            self.fixed_slider.max >= z_index
                            and self.fixed_slider.min <= z_index
                        ):
                            self.fixed_slider.set(z_index)
                self.update_display()
                
    def save_points(self):
        """
        Gets points from registration gui and saves them to a global variable 
        for the registration function to use.
        """
        global fixed_image_points, moving_image_points
        # Get the manually specified points and compute the transformation.
        fixed_image_points, moving_image_points = self.get_points()
        
        fixed_image_points_flat = [c for p in fixed_image_points for c in p]
        moving_image_points_flat = [c for p in moving_image_points for c in p]

# =============================================================================
#         self.init_transform = sitk.AffineTransform(
#            sitk.LandmarkBasedTransformInitializer(
#                sitk.AffineTransform(3), fixed_image_points_flat, moving_image_points_flat
#            )
#         )
# =============================================================================

        # Initialize a Rigid3DTransform using landmark-based initialization
        self.init_transform = sitk.LandmarkBasedTransformInitializer(sitk.VersorRigid3DTransform(), 
                                                                fixed_image_points_flat, 
                                                                moving_image_points_flat)
        

        print("manual initial transformation is: " + str(self.init_transform.GetParameters()))




        self.final_transform, _ = self.multires_registration(self.fixed_image, 
                                                        self.moving_image, 
                                                        self.init_transform)
        
        minmax_filt = sitk.MinimumMaximumImageFilter()
        minmax_filt.Execute(self.moving_image)
        min_voxel = minmax_filt.GetMinimum()
        
        # execute the transformation
        self.moving_resampled = sitk.Resample(
            self.moving_image,
            self.fixed_image,
            self.final_transform,
            sitk.sitkLinear,
            min_voxel,
            self.moving_image.GetPixelID(),
        )
# =============================================================================
#         # execute the transformation (init only for testing!!!)
#         self.moving_resampled = sitk.Resample(
#             self.moving_image,
#             self.fixed_image,
#             self.init_transform,
#             sitk.sitkLinear,
#             min_voxel,
#             self.moving_image.GetPixelID(),
#         )
# =============================================================================
                
        print('Registration Complete!')
        visualize_registration(self.fixed_image, self.moving_resampled, root=self.root)
        
        # popup window with button for next step, segmentation
        # Show a popup message with a continue button
        self.popup = Toplevel(self.window)
        self.popup.title("Registration Complete")
        self.popup.geometry('200x100')
        message_label = Label(self.popup, text="Registration successful?")
        message_label.pack(pady=10)
        
        # get user entry for name to go on helmet
        entry_label = Label(self.popup, text = 'Type animal name and press enter')
        entry_label.pack()
        fileVar = StringVar(self.popup, 'Animal_name')
        self.animal_name='TEST'
        name_entry = Entry(self.popup, textvariable=fileVar)
        name_entry.bind("<Return>", self.name_change)
        name_entry.pack()
        
        # continue to stl generation
        continue_button = Button(self.popup, text="Continue", command=self.launch_segmentation)
        continue_button.pack()
        
    # command to set animal name upon user entry
    def name_change(self, name_entry):
        self.animal_name = name_entry.widget.get()
        
    def launch_segmentation(self):
        # output registration for debugging
# =============================================================================
#         sitk.WriteImage(self.moving_resampled, fileName=f'nifti_files/registered/registered_{self.animal_name}.nii.gz')
# =============================================================================
        
        # destroy windows for mesh manipulation
        self.popup.destroy()
        self.root.destroy()
        seg_screen = SegmentationScreen(self.moving_resampled, self.animal_name)
        seg_screen.run_mesh_manipulation_window()
        
        