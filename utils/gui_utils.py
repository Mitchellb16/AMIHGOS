#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 14 15:53:49 2022

@author: mitchell
"""
import PIL
from itertools import count
import pyvista as pv
import numpy as np
import SimpleITK as sitk
from tkinter import *
from tkinter import filedialog
from RangeSlider import RangeSliderH
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
import matplotlib.patches as patches
import matplotlib.cm as cm
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, 
NavigationToolbar2Tk)
from .sitk2vtk import *
from .vtkutils import *

class ROIDataAquisition(object):
    """
    This class provides a GUI for selecting box shaped Regions Of Interest (ROIs). Each ROI is represented as a
    tuple: ((min_x,max_x),(min_y,max_y), and possibly (min_z,max_z)) if dealing with a 3D image.
    When using the zoom/pan tool from the toolbar ROI selection is disabled. Once you click again on the zoom/pan
    button zooming/panning will be disabled and ROI selection is enabled.
    Note that when you are marking the ROI on a slice that is outside the Z-range selected by the
    range slider, once you are done selecting the ROI, you will see no change on the current slice. This is the
    correct behavior, though initially you may be surprised by it.
    """

    def __init__(self, image, window, window_level=None, figure_size=(3, 2)):
        self.window = window
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

        ui = self.create_ui()

        # Create a figure with axes for front, middle, and back 
        self.back_fig, self.back_ax = plt.subplots(1, 1, figsize=figure_size)
        self.front_fig, self.front_ax = plt.subplots(1, 1, figsize=figure_size)
        self.middle_fig, self.middle_ax = plt.subplots(1, 1, figsize=figure_size)
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
        self.middle_fig.canvas.mpl_connect("button_press_event", self)
        self.roi_selector = RectangleSelector(
            self.middle_ax,
            lambda eclick, erelease: None,
            drawtype="box",
            useblit=True,
            button=[1, 3],  # Left, right buttons only.
            minspanx=5,
            minspany=5,  # Ignore motion smaller than 5 pixels.
            spancoords="pixels",
            interactive=True,
            rectprops=self.roi_display_properties,
        )
        self.roi_selector.set_visible(False)

        # Display the data and the controls, first time we display the images is outside the "update_display" method
        # as that method relies on the existance of a previous image which is removed from the figure.
        # 2.37 gives a slice of the head that is actually near the widest part
        self.middle_slice = round(self.sliders[0].get() + self.sliders[1].get() / 2.16)
        for i, ax in enumerate([self.back_ax, self.front_ax, self.middle_ax]):
            ax.imshow(
                self.npa[self.sliders[0].get(), :, :] if i < 2 else self.npa[self.middle_slice, :, :],
                cmap=plt.cm.Greys_r,
                vmin=self.min_intensity,
                vmax=self.max_intensity,
            )
# =============================================================================
#         self.axes.imshow(
#             self.npa[self.slice_slider.get(), :, :] if self.slice_slider else self.npa,
#             cmap=plt.cm.Greys_r,
#             vmin=self.min_intensity,
#             vmax=self.max_intensity,
#         )
# =============================================================================
        self.update_display()

    def create_ui(self):
        # Create the active UI components. Height and width are specified in 'em' units. This is
        # a html size specification, size relative to current font size.
        self.addroi_button = Button(self.window,
            text="Add ROI", command = self.add_roi
        ).grid(column = 2, row = 1)
        self.clearlast_button = Button(self.window,
            text="Clear Last", command = self.clear_last
        ).grid(column = 2, row=2)

        self.clearall_button = Button(self.window,
            text="Clear All", command = self.clear_all
        ).grid(column = 2, row = 3)
        
        self.crop_button = Button(self.window, 
                                  text = 'Crop Image',
                                  command = self.crop_moving
                                  ).grid(column = 2, row = 5)
        
        # add frames for each image/slider combo to be packed in
        self.slider_boxes = [Frame(self.window), Frame(self.window)]
        self.sliders = []
        # Create sliders only if 3D image
        for box in self.slider_boxes:
                slice_slider = Scale(
                box,
                from_=0,
                to=self.npa.shape[0] - 1, 
                command = self.on_slice_slider_value_change
            )
                slice_slider.pack(side='left')
                
                self.sliders.append(slice_slider)
            
# =============================================================================
#             self.hvars = [IntVar(self.window),IntVar(self.window)]
# 
#             self.roi_range_slider = RangeSliderH(slicer_box, self.hvars,
#                                            min_val = 0, 
#                                            max_val = self.npa.shape[0] - 1, 
#                                            padX=100, digit_precision='.0f')
# 
#             self.roi_range_slider.pack()
#             
# =============================================================================
        return Frame(self.window,
                     [self.addroi_button, self.clearlast_button, self.clearall_button]
                     )

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
        # 2.16 gives a slice of the head that is actually near the widest part
        self.middle_slice = round(self.sliders[0].get() + self.sliders[1].get() / 2.16)
        for i, ax in enumerate([self.back_ax, self.front_ax, self.middle_ax]):
            ax.imshow(
                self.npa[self.sliders[i].get(), :, :] if i < 2 else self.npa[self.middle_slice, :, :],
                cmap=plt.cm.Greys_r,
                vmin=self.min_intensity,
                vmax=self.max_intensity,
            )
            
            ax.images[0].remove()
        
# =============================================================================
#         self.middle_slice = round(self.sliders[0].get() + self.sliders[1].get() / 2)
#         for i, ax in enumerate([self.back_ax, self.front_ax, self.middle_ax]):
#             if i < 2:
#                 slice_val = self.sliders[i].get()
#                 ax.imshow(
#                     self.npa[slice_val, :, :],
#                     cmap=plt.cm.Greys_r,
#                     vmin=self.min_intensity,
#                     vmax=self.max_intensity,
#                 )
#                 ax.images[0].remove()
# 
#             else:
#                 ax.imshow(
#                     self.npa[self.middle_slice, :, :],
#                     cmap=plt.cm.Greys_r,
#                     vmin=self.min_intensity,
#                     vmax=self.max_intensity,
#                 )
#                 ax.images[0].remove()
#                 print('length of middle images:', len(ax.images))
# =============================================================================

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

    def clear_all(self):
        self.clear_all_data()
        self.update_display()

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
        
class MultiImageDisplay(object):
    """
    This class provides a GUI for displaying 3D images. It supports display of
    multiple images in the same UI. The image slices are selected according to
    the axis specified by the user. Each image can have a title and a slider to
    scroll through the stack. The images can also share a single slider if they
    have the same number of slices along the given axis. Images are either
    grayscale or color. The intensity range used for display (window-level) can
    be specified by the user as input to the constructor or set via the displayed
    slider. For color images the intensity control slider will be disabled. This
    allows us to display both color and grayscale images in the same figure with
    a consistent look to the controls. The range of the intensity slider is set
    to be from top/bottom 2% of intensities (accomodating for outliers). Images
    are displayed either in horizontal or vertical layout, depending on the
    users choice.
    """

    def __init__(
        self,
        image_list,
        axis=0,
        title_list=None,
        window_level_list=None,
        intensity_slider_range_percentile=[2, 98],
        figure_size=(10, 8),
        horizontal=True,
    ):

        self.window = window
        self.npa_list, wl_range, wl_init = self.get_window_level_numpy_array(
            image_list, window_level_list, intensity_slider_range_percentile
        )
        self.image_list = image_list
        self.reoriented_image = image_list[-1]
        if title_list:
            if len(image_list) != len(title_list):
                raise ValueError("Title list and image list lengths do not match")
            self.title_list = list(title_list)
        else:
            self.title_list = [""] * len(image_list)

        # Our dynamic slice, based on the axis the user specifies
        self.slc = [slice(None)] * 3
        self.axis = axis
        
        self.multi_image_frame = Frame(self.window)
        ui = self.create_ui(wl_range, wl_init)
# =============================================================================
#         display(ui)
# =============================================================================
        
        
        # Create a figure.
        col_num, row_num = (len(image_list), 1) if horizontal else (1, len(image_list))
        self.fig, self.axes = plt.subplots(row_num, col_num, figsize=figure_size)
        canvas = FigureCanvasTkAgg(self.fig, self.multi_image_frame)
        canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
        if len(image_list) == 1:
            self.axes = [self.axes]

        # Display the data and the controls, first time we display the image is outside the "update_display" method
        # as that method relies on the previous zoom factor which doesn't exist yet.
        for ax, npa, slider, wl_slider in zip(
            self.axes, self.npa_list, self.slider_list, self.wl_list
        ):
            self.slc[self.axis] = slice(slider.get(), slider.get() + 1)
            # Need to use squeeze to collapse degenerate dimension (e.g. RGB image size 124 124 1 3)
            ax.imshow(
                np.squeeze(npa[tuple(self.slc)]),
                cmap=plt.cm.Greys_r,
                vmin=wl_slider.getValues()[0],
                vmax=wl_slider.getValues()[1],
            )
        self.update_display()
        plt.tight_layout()
        
        self.multi_image_frame.pack()
        
    def orient_LPS(self):
        self.reoriented_image = sitk.DICOMOrient(self.image_list[-1], 'LPS')
        self.npa_list[-1] = sitk.GetArrayFromImage(self.reoriented_image)
        self.update_display()
    
    def orient_RIA(self):
        self.reoriented_image = sitk.DICOMOrient(self.image_list[-1], 'RIA')
        self.npa_list[-1] = sitk.GetArrayFromImage(self.reoriented_image)
        self.update_display()
        

    def update_display(self):

        # Draw the image(s)
        for ax, npa, title, slider, wl_slider in zip(
            self.axes, self.npa_list, self.title_list, self.slider_list, self.wl_list
        ):
            # We want to keep the zoom factor which was set prior to display, so we log it before
            # clearing the axes.
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()

            self.slc[self.axis] = slice(slider.get(), slider.get() + 1)
            ax.clear()
            # Need to use squeeze to collapse degenerate dimension (e.g. RGB image size 124 124 1 3)
            ax.imshow(
                np.squeeze(npa[tuple(self.slc)]),
                cmap=plt.cm.Greys_r,
                vmin=wl_slider.getValues()[0],
                vmax=wl_slider.getValues()[1],
            )
            ax.set_title(title)
            ax.set_axis_off()

            # Set the zoom factor back to what it was before we cleared the axes, and rendered our data.
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)

        self.fig.canvas.draw_idle()
    def get_window_level_numpy_array(
        self, image_list, window_level_list, intensity_slider_range_percentile
    ):
        # Using GetArray and not GetArrayView because we don't keep references
        # to the original images. If they are deleted outside the view would become
        # invalid, so we use a copy wich guarentees that the gui is consistent.
        npa_list = list(map(sitk.GetArrayFromImage, image_list))

        wl_range = []
        wl_init = []
        # We need to iterate over the images because they can be a mix of
        # grayscale and color images. If they are color we set the wl_range
        # to [0,255] and the wl_init is equal, ignoring the window_level_list
        # entry.
        for i, npa in enumerate(npa_list):
            if len(npa.shape) == 4:  # color image
                wl_range.append((0, 255))
                wl_init.append((0, 255))
                # ignore any window_level_list entry
            else:
                # We don't necessarily take the minimum/maximum values, just in case there are outliers
                # user can specify how much to take off from top and bottom.
                min_max = np.percentile(
                    npa.flatten(), intensity_slider_range_percentile
                )
                wl_range.append((min_max[0], min_max[1]))
                if not window_level_list:  # No list was given.
                    wl_init.append(wl_range[-1])
                else:
                    wl = window_level_list[i]
                    if wl:
                        wl_init.append((wl[1] - wl[0] / 2.0, wl[1] + wl[0] / 2.0))
                    else:  # We have a list, but for this image the entry was left empty: []
                        wl_init.append(wl_range[-1])
        return (npa_list, wl_range, wl_init)
    def on_slice_slider_value_change(self, change):
        self.update_display()

    def on_wl_slider_value_change(self, change):
        self.update_display()
    def create_ui(self, wl_range, wl_init):
        # Create the active UI components. 
        self.orientLPS_button = Button(
            self.multi_image_frame, text="Orient Coronal", command = self.orient_LPS
        ).pack()
        
        self.orientRIA_button = Button(
            self.multi_image_frame, text="Orient Axial", command = self.orient_RIA
        ).pack()
                
        slicer_box = Frame(self.multi_image_frame)
        slicer_box.pack()
        self.slider_list = []
        for npa in self.npa_list:
            slider = Scale(
                slicer_box,
                from_=0,
                to=npa.shape[self.axis] - 1, 
                command = self.on_slice_slider_value_change
            )
            slider.pack(side='left')
            self.slider_list.append(slider)
        
        
        self.wl_list = []
        wl_box = Frame(self.multi_image_frame)
        wl_box.pack()
# =============================================================================
#         hVar1 = DoubleVar()  #left handle variable
#         hVar2 = DoubleVar()  #right handle variable
# =============================================================================
        # make variables for each range slider
        hvars = [[DoubleVar(),DoubleVar()] for i in range(len(npa))]
        
        # add commands to each variable (this is broken for now)
# =============================================================================
#         for i in hvars:
#             i[0].trace_add('write', self.on_wl_slider_value_change)
#             i[1].trace_add('write', self.on_wl_slider_value_change)
# =============================================================================
        
        # Each image has a window-level slider, but it is disabled if the image
        # is a color image len(npa.shape)==4 . This allows us to display both
        # color and grayscale images in the same UI while retaining a reasonable
        # layout for the sliders.
        slider_counter = 0
        for r_values, i_values, npa in zip(wl_range, wl_init, self.npa_list):
            wl_range_slider = RangeSliderH(wl_box, hvars[slider_counter],
                                           min_val = r_values[0], 
                                           max_val = r_values[1], 
                                           padX=100)

            wl_range_slider.pack()
            self.wl_list.append(wl_range_slider)
            slider_counter += 1 
        
        
        return Frame(self.window, [slicer_box, wl_box])

class RegistrationPointDataAquisition(object):
    """
    This class provides a GUI for localizing corresponding points in two images, and for evaluating registration results using a linked cursor
    approach, user clicks in one image and the corresponding point is added to the other image.
    """

    def __init__(
        self,
        fixed_image,
        moving_image,
        window,
        fixed_window_level=None,
        moving_window_level=None,
        figure_size=(10, 8),
        known_transformation=None,
    ):
        self.window = window
        self.window.pack()
        self.fixed_image = fixed_image
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
                

# =============================================================================
#         # self.fig.canvas.set_window_title('Registration Points Acquisition')
#         self.fixed_axes = axes[0]
#         self.moving_axes = axes[1]
# =============================================================================

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
        self.clearlast_button = Button(self.window,
            text="Clear Last", command = self.clear_last
        ).grid(column = 1, row = 1)

        self.clearall_button = Button(self.window,
            text="Clear All", command = self.clear_all
        ).grid(column = 1, row = 2)
        
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
            self.fixed_slider.pack()
            
            self.moving_slider = Scale(
                self.moving_frame,
                from_=0,
                to=self.moving_npa.shape[0] - 1,
                command = self.on_slice_slider_value_change,
            )
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

        init_transform = sitk.AffineTransform(
           sitk.LandmarkBasedTransformInitializer(
               sitk.AffineTransform(3), fixed_image_points_flat, moving_image_points_flat
           )
        )
        print("manual initial transformation is: " + str(init_transform.GetParameters()))




        final_transform, _ = self.multires_registration(fixed_image, moving_image, init_transform)
        
        minmax_filt = sitk.MinimumMaximumImageFilter()
        minmax_filt.Execute(moving_image)
        min_voxel = minmax_filt.GetMinimum()
        
        global moving_resampled 
        
        moving_resampled = sitk.Resample(
            moving_image,
            fixed_image,
            init_transform,
            sitk.sitkLinear,
            min_voxel,
            moving_image.GetPixelID(),
        )
        print('Registration Complete!')
    
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
  
def segment_to_stl(img, animal_name):
    output_dir = 'head_stls/' + animal_name + '.stl'
    anisotropicSmoothing = True
    thresholds = [-300., -200., 400., 2000.] # this thresholds for skin in HU 
    medianFilter=True
    connectivityFilter = True

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
    
    mesh_file = '/home/mitchell/Documents/Projects/CT_helmets/stl_files/Helmets/helmet_remeshed.stl'
    
    helmet_mesh = pv.read(mesh_file)
    head_mesh = pv.read(output_dir)
    # scale up and rotate head mesh
    head_mesh.scale([1.04,1.04,1.04], inplace=True)
    head_mesh.rotate_x(290, inplace=True)
    
    # align the centers of both meshes at 0 then translate 
    helmet_mesh.points -= helmet_mesh.center
    head_mesh.points -= head_mesh.center
    offset = [.75,12,-5.5]
    head_mesh.points += offset
    
    # create text object for embossing
    text = pv.Text3D(animal_name, depth=.7)
    text.scale([2.5,2.5,2.5], inplace = True)
    text.rotate_z(90, inplace=True)
    text_offset = [27,6,-12.2]
    text.points += text_offset
    
    # add text to helmet to emboss
    helmet_mesh = helmet_mesh + text
    
    plotter = pv.Plotter(off_screen = False, notebook=False)
    plotter.add_mesh(helmet_mesh)
    plotter.add_mesh(head_mesh)
    plotter.show()
    
    plotter2 = pv.Plotter(off_screen=False, notebook = False)
    bool_mesh = helmet_mesh.boolean_difference(head_mesh)
    plotter2.add_mesh(bool_mesh)
    plotter2.show()
    
# developed by user Novel https://stackoverflow.com/questions/43770847/play-an-animated-gif-in-python-with-tkinter
class ImageLabel(Label):
    """a label that displays images, and plays them if they are gifs"""
    def load(self, im):
        if isinstance(im, str):
            im = PIL.Image.open(im)
        self.loc = 0
        self.frames = []

        try:
            for i in count(1):
                self.frames.append(PIL.ImageTk.PhotoImage(im.copy()))
                im.seek(i)
        except EOFError:
            pass

        try:
            self.delay = im.info['duration']
        except:
            self.delay = 100

        if len(self.frames) == 1:
            self.config(image=self.frames[0])
        else:
            self.next_frame()

    def unload(self):
        self.config(image="")
        self.frames = None

    def next_frame(self):
        if self.frames:
            self.loc += 1
            self.loc %= len(self.frames)
            self.config(image=self.frames[self.loc])
            self.after(self.delay, self.next_frame)
