#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 13 15:01:22 2023

@author: mitchell
"""
import numpy as np
import SimpleITK as sitk
from tkinter import *
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import matplotlib.patches as patches
from matplotlib.figure import Figure
import matplotlib.cm as cm
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, 
NavigationToolbar2Tk)
from .RegistrationPointDataAquisition import RegistrationPointDataAquisition
from .sitk2vtk import *
from .vtkutils import *

class ROIDataAquisition(object):
    """
    ***Adapted from SIMPLEITK jupyter notebook tutorials
    This class provides a GUI for selecting box shaped Regions Of Interest (ROIs). Each ROI is represented as a
    tuple: ((min_x,max_x),(min_y,max_y), and possibly (min_z,max_z)) if dealing with a 3D image.
    When using the zoom/pan tool from the toolbar ROI selection is disabled. Once you click again on the zoom/pan
    button zooming/panning will be disabled and ROI selection is enabled.
    Note that when you are marking the ROI on a slice that is outside the Z-range selected by the
    range slider, once you are done selecting the ROI, you will see no change on the current slice. This is the
    correct behavior, though initially you may be surprised by it.
    """

    def __init__(self, image, window, root, frames_list, window_level=None, figure_size=(6, 4)):
        self.window = window
        self.root = root
        self.frames_list = frames_list
        self.root.geometry('1600x400')
        
        # change window location
        # get main window position
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
    
        # add offset
        win_x = root_x + 600
        win_y = root_y + 200

        # set toplevel in new position
        self.root.geometry(f'+{win_x}+{win_y}')
    
        self.window.pack()
        self.image = image
        (
            self.npa,
            self.min_intensity,
            self.max_intensity,
        ) = self.get_window_level_numpy_array(self.image, window_level)
        self.rois = []

        # ROI display settings
        self.roi_display_properties = dict(
            facecolor="red", edgecolor="black", alpha=0.2, fill=True
        )

        self.create_ui()

        # Create a figure with axes for front, middle, and back 
        self.back_fig, self.back_ax = plt.subplots(1, 1, figsize=figure_size)
        self.back_ax.set_title('Back of Head')
        
        self.front_fig, self.front_ax = plt.subplots(1, 1, figsize=figure_size)
        self.front_ax.set_title('Front of Nose')
        
        self.middle_fig, self.middle_ax = plt.subplots(1, 1, figsize=figure_size)
        self.middle_ax.set_title('Outline head')
        
        # only give sliders to the front and back axes, middle axis just gets put in window
        for i, fig in enumerate([self.back_fig, self.front_fig, self.middle_fig]):
            if i < 2:
                canvas = FigureCanvasTkAgg(fig, self.slider_boxes[i])
                canvas.get_tk_widget().pack()
                self.slider_boxes[i].grid(column = i, row = 3)
            else: 
                canvas = FigureCanvasTkAgg(fig, self.window)
                canvas.get_tk_widget().grid(column=3, row = 3)
                
        # Connect the mouse button press to the canvas (__call__ method is the invoked callback).

        self.roi_selector = RectangleSelector(
            self.middle_ax,
            self.onselect,
            useblit=True,
            button=[1, 3],  # Left, right buttons only.
            minspanx=5,
            minspany=5,  # Ignore motion smaller than 5 pixels.
            spancoords="pixels",
            interactive=True,
        )
        self.roi_selector.set_visible(False)

        # Display the data and the controls, first time we display the images is outside the "update_display" method
        # as that method relies on the existance of a previous image which is removed from the figure.
        # .43 gives a slice of the head that is actually near the widest part
        self.middle_slice = round((self.sliders[0].get() + self.sliders[1].get()) * .43)
        for i, ax in enumerate([self.back_ax, self.front_ax, self.middle_ax]):
            ax.imshow(
                self.npa[self.sliders[0].get(), :, :] if i < 2 else self.npa[self.middle_slice, :, :],
                cmap=plt.cm.Greys_r,
                vmin=self.min_intensity,
                vmax=self.max_intensity,
            )

        self.update_display()

    def create_ui(self):
        # Create the active UI components. 
        #
        
        # make a frame to put all of the buttons in
        self.button_frame = Frame(self.window)
        
        self.addroi_button = Button(self.button_frame,
            text="Add ROI", command = self.add_roi)
        self.addroi_button.pack(side='left')
# =============================================================================
#         self.clearlast_button = Button(self.window,
#             text="Clear Last", command = self.clear_last
#         ).grid(column = 2, row=2)
# 
#         self.clearall_button = Button(self.window,
#             text="Clear All").grid(column = 2, row = 3)
# =============================================================================
        
        self.crop_button = Button(self.button_frame, 
                                  text = 'Crop Image',
                                  command = self.crop_moving
                                  )
        self.crop_button.pack(side='left')
        # Add a Quit button
        self.quit_button = Button(self.button_frame, text="Quit", command=self.quit_application)
        self.quit_button.pack(side = BOTTOM) # Adjust row and column as needed
        
        self.button_frame.grid(column=1, columnspan=1, row=4)
        # add frames for each image/slider combo to be packed in
        self.slider_boxes = [Frame(self.window), Frame(self.window)]
        self.sliders = [0,0]
        
        # make slider for most posterior
        self.sliders[0] = Scale(
                self.slider_boxes[0],
                from_=0,
                to=self.npa.shape[0] - 1, 
                command = self.on_slice_slider_value_change
            )
        self.sliders[0].set(150)
        self.sliders[0].pack(side = 'left')
        
        # make slider for most anterior
        self.sliders[1] = Scale(
                self.slider_boxes[1],
                from_=0,
                to=self.npa.shape[0] - 1, 
                command = self.on_slice_slider_value_change
            )
        self.sliders[1].set(370)
        self.sliders[1].pack(side = 'left')

        
    def on_slice_slider_value_change(self, change):
        self.update_display()

    def get_window_level_numpy_array(self, image, window_level):
        npa = sitk.GetArrayViewFromImage(image)
        # We don't take the minimum/maximum values, just in case there are outliers (top/bottom 2%)
        if not window_level:
            min_max = np.percentile(npa.flatten(), [2, 98])
            return npa, min_max[0], min_max[1]
        else:
            return (
                npa,
                window_level[1] - window_level[0] / 2.0,
                window_level[1] + window_level[0] / 2.0,
            )

    def update_display(self):
        # Draw the image and ROIs.
        # imshow adds an image to the axes, so we also remove the previous one.
        # need to do this to front, middle, and back 
        # 43 gives a slice of the head that is actually near the widest part
        self.middle_slice = round((self.sliders[0].get() + self.sliders[1].get()) * .43)
        for i, ax in enumerate([self.back_ax, self.front_ax, self.middle_ax]):
            ax.imshow(
                self.npa[self.sliders[i].get(), :, :] if i < 2 else self.npa[self.middle_slice, :, :],
                cmap=plt.cm.Greys_r,
                vmin=self.min_intensity,
                vmax=self.max_intensity,
            )
            
            ax.images[0].remove()
        

        # Iterate over all of the ROIs and only display/undisplay those that are relevant.
        if self.rois:
            for roi_data in self.rois:
                if (
                    self.sliders[0].get() >= roi_data[3][0]
                    and self.sliders[1].get() <= roi_data[3][1]
                ):
                    roi_data[0].set_visible(True)
                else:
                    roi_data[0].set_visible(False)
        self.middle_ax.set_title(f"selected {len(self.rois)} ROIs")
        self.middle_ax.set_axis_off()
        for fig in [self.back_fig, self.front_fig, self.middle_fig]:
            fig.canvas.draw_idle()

    def add_roi_data(self, roi_data):
        """
        Add regions of interest to this GUI.
        Input is an iterable containing tuples where each tuple contains
        either two or three tuples (min_x,max_x),(min_y,max_y), (min_z,max_z).
        depending on the image dimensionality. The ROI
        is the box defined by these integer values and includes
        both min/max values.
        """
        self.validate_rois(roi_data)

        for roi in roi_data:
            self.rois.append(
                (
                    patches.Rectangle(
                        (roi[0][0], roi[1][0]),
                        roi[0][1] - roi[0][0],
                        roi[1][1] - roi[1][0],
                        **self.roi_display_properties,
                    ),
                    roi[0],
                    roi[1],
                    roi[2] if self.npa.ndim == 3 else None,
                )
            )
            self.axes.add_patch(self.rois[-1][0])
        self.update_display()

    def set_rois(self, roi_data):
        """
        Clear any existing ROIs and set the display to the given ones.
        Input is an iterable containing tuples where each tuple contains
        two or three tuples (min_x,max_x),(min_y,max_y), (min_z,max_z) depending
        on the image dimensionality. The ROI
        is the box defined by these integer values and includes
        both min/max values.
        """
        self.clear_all_data()
        self.add_roi_data(roi_data)

    def validate_rois(self, roi_data):
        for roi in roi_data:
            for i, bounds in enumerate(roi, 1):
                if bounds[0] > bounds[1]:
                    raise ValueError(
                        "First element in each tuple is expected to be smaller than second element, error in ROI ("
                        + ", ".join(map(str, roi))
                        + ")."
                    )
                # Note that SimpleITK uses x-y-z specification vs. numpy's z-y-x
                if not (
                    bounds[0] >= 0 and bounds[1] < self.npa.shape[self.npa.ndim - i]
                ):
                    raise ValueError(
                        "Given ROI ("
                        + ", ".join(map(str, roi))
                        + ") is outside the image bounds."
                    )

    def add_roi(self):
        if self.roi_selector.visible:
            self.roi_selector.set_visible(False)
            # Extent is in sub-pixel coordinates, we need it in pixels/voxels.
            roi_extent = [int(round(coord)) for coord in self.roi_selector.extents]
            # We keep the patch for display and the x,y,z ranges of the ROI.
            self.rois.append(
                (
                    patches.Rectangle(
                        (roi_extent[0], roi_extent[2]),
                        roi_extent[1] - roi_extent[0],
                        roi_extent[3] - roi_extent[2],
                        **self.roi_display_properties,
                    ),
                    (roi_extent[0], roi_extent[1]),
                    (roi_extent[2], roi_extent[3]),
                    [i.get() for i in self.sliders],
                )
            )
            self.middle_ax.add_patch(self.rois[-1][0])
            self.update_display()

    def clear_all_data(self):
        for roi_data in self.rois:
            roi_data[0].remove()
        del self.rois[:]

# =============================================================================
#     def clear_all(self):
#         self.clear_all_data()
#         self.update_display()
# =============================================================================

    def clear_last(self):
        if self.rois:
            self.rois[-1][0].remove()
            self.rois.pop()
            self.update_display()

    def get_rois(self):
        """
        Return a list of tuples representing the ROIs. Each tuple contains either two or three tuples (min_x,max_x),
        (min_y,max_y), (min_z,max_z) depending on image dimensionality. The ROI is the box defined by these integer values and includes
        both min/max values.
        """
        return [
            (roi_data[1], roi_data[2], roi_data[3])
            if self.npa.ndim == 3
            else (roi_data[1], roi_data[2])
            for roi_data in self.rois
        ]
    

    def onselect(self, eclick, erelease):
       
        # Rest of your onselect logic
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        # Your logic to handle the selected region
        print(f"Selected region: x1={x1}, y1={y1}, x2={x2}, y2={y2}")

        # Update the display or perform other actions as needed
        self.update_display()
        
    def on_press(self, event):
        # Handle the button press event
        self._eventpress = event

    def on_release(self, event):

        # Update the display or perform other actions as needed
        self.update_display()

    def quit_application(self):
        # This function will be called when the Quit button is clicked
        self.root.destroy()
    
    def crop_moving(self):
        """
        Using user-selected ROI, crop moving image to just the head

        Returns
        -------
        Cropped moving image
        """
        
        # get rois from gui
        specified_rois = self.get_rois()
        print(specified_rois)
        # select the one ROI we will work on
        ROI_INDEX = 0

        # crop
        roi = specified_rois[ROI_INDEX]
        self.image = self.image[roi[0][0] : roi[0][1] + 1, 
                                        roi[1][0] : roi[1][1] + 1, 
                                        roi[2][0] : roi[2][1] + 1]
        
        # popup window with button for next step, registration
        # Show a popup message with a continue button
        self.popup = Toplevel(self.window)
        self.popup.title("Success")
        self.popup.geometry('200x100')
        message_label = Label(self.popup, text="Cropping successful!")
        message_label.pack(pady=10)

        continue_button = Button(self.popup, text="Continue", command=self.launch_registration_aquisition)
        continue_button.pack()
        
    def launch_registration_aquisition(self):
        self.popup.destroy()  # Close the popup window
        self.window.pack_forget()
        self.root.geometry('1000x500')
        # pixel values that will be shown in the registration window 
        moving_window_level = [250,700]
        fixed_window_level = [39,60]
        
        RegistrationPointDataAquisition(self.image,
                                        self.frames_list[2],
                                        self.root,
                                        fixed_window_level,
                                        moving_window_level)
        