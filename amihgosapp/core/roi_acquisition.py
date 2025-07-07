#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROIDataAcquisition module - GUI for selecting box-shaped Regions Of Interest (ROIs)

Adapted from SimpleITK jupyter notebook tutorials
Written by Mitchell Bishop and optimized with Claude AI
"""
import numpy as np
import SimpleITK as sitk
from tkinter import Frame, Button, Scale, Toplevel, Label, BOTTOM
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import RectangleSelector
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import from new locations when available
from amihgosapp.utils.resource_utils import get_image_path
from amihgosapp.core.registration_acquisition import RegistrationPointDataAcquisition


class ROIDataAcquisition:
    """
    GUI for selecting box-shaped Regions Of Interest (ROIs).
    
    Each ROI is represented as a tuple: ((min_x,max_x),(min_y,max_y), and (min_z,max_z)).
    """
    
    def __init__(self, image, window, root, frames_list, window_level=None, figure_size=(3, 2)):
        """
        Initialize the ROI selection interface.
        
        Parameters
        ----------
        image : SimpleITK.Image
            The image to select ROIs from
        window : tkinter.Frame
            Frame to place UI elements in
        root : tkinter.Tk
            Root window
        frames_list : list
            List of frames for different stages of the application
        window_level : tuple, optional
            Window and level for image display, by default None
        figure_size : tuple, optional
            Size of the figure, by default (6, 4)
        """
        self.window = window
        self.root = root
        self.frames_list = frames_list
        self.root.geometry("")
        self.window.pack()
        self.image = image
        
        # Get numpy array and intensity range for display
        self.npa, self.min_intensity, self.max_intensity = self._get_window_level_numpy_array(
            self.image, window_level
        )
        self.rois = []

        # ROI display settings
        self.roi_display_properties = dict(
            facecolor="red", edgecolor="black", alpha=0.2, fill=True
        )

        # Set up the UI
        self._create_ui()
        self._setup_figures(figure_size)
        
        # Initialize display
        self._update_initial_display()

    def _create_ui(self):
        """Create UI components (buttons, sliders)."""
        # Create a frame for buttons
        self.button_frame = Frame(self.window)
        
        # Add Crop button
        self.crop_button = Button(
            self.button_frame, 
            text="Crop Image",
            command=self.crop_moving
        )
        self.crop_button.pack(side='left')
        
        # Add Quit button
        self.quit_button = Button(
            self.button_frame, 
            text="Quit", 
            command=self.quit_application
        )
        self.quit_button.pack(side=BOTTOM)
        
        self.button_frame.grid(column=1, columnspan=1, row=4)
        
        # Create frames for image sliders
        self.slider_boxes = [Frame(self.window), Frame(self.window)]
        self.sliders = [None, None]
        
        # Posterior slider
        self.sliders[0] = Scale(
            self.slider_boxes[0],
            from_=0,
            to=self.npa.shape[0] - 1, 
            command=self._on_slice_slider_value_change
        )
        self.sliders[0].set(110)  # Default position
        self.sliders[0].pack(side='left')
        
        # Anterior slider
        self.sliders[1] = Scale(
            self.slider_boxes[1],
            from_=0,
            to=self.npa.shape[0] - 1, 
            command=self._on_slice_slider_value_change
        )
        self.sliders[1].set(370)  # Default position
        self.sliders[1].pack(side='left')

    def _setup_figures(self, figure_size):
        """Set up matplotlib figures for visualization."""
        # Create figures for back, front, and middle views
        self.back_fig, self.back_ax = plt.subplots(1, 1, figsize=figure_size)
        self.back_ax.set_title('Back of Head')
        
        self.front_fig, self.front_ax = plt.subplots(1, 1, figsize=figure_size)
        self.front_ax.set_title('Front of Nose')
        
        self.middle_fig, self.middle_ax = plt.subplots(1, 1, figsize=figure_size)
        self.middle_ax.set_title('Outline Head')
        
        # Add figures to the UI
        for i, fig in enumerate([self.back_fig, self.front_fig, self.middle_fig]):
            if i < 2:
                canvas = FigureCanvasTkAgg(fig, self.slider_boxes[i])
                canvas.get_tk_widget().pack()
                self.slider_boxes[i].grid(column=i, row=1)
            else: 
                canvas = FigureCanvasTkAgg(fig, self.window)
                canvas.get_tk_widget().grid(column=3, row=1, padx=20)
        
        # Set up ROI selector for the middle view
        self.roi_selector = RectangleSelector(
            self.middle_ax,
            self.onselect,
            useblit=True,
            button=[1, 3],  # Left, right buttons only
            minspanx=5,
            minspany=5,  # Ignore motion smaller than 5 pixels
            spancoords="pixels",
            interactive=True,
        )
        self.roi_selector.set_visible(False)

    def _update_initial_display(self):
        """Initialize the display with images."""
        # Calculate middle slice based on current slider positions
        self.middle_slice = round((self.sliders[0].get() + self.sliders[1].get()) * 0.46)
        
        # Display initial images
        for i, ax in enumerate([self.back_ax, self.front_ax, self.middle_ax]):
            ax.imshow(
                self.npa[self.sliders[i].get() if i < 2 else self.middle_slice, :, :],
                cmap=plt.cm.Greys_r,
                vmin=self.min_intensity,
                vmax=self.max_intensity,
            )
            ax.set_axis_off()
        
        # Update the display
        self.update_display()

    def _on_slice_slider_value_change(self, _):
        """Handle slider value changes."""
        self.update_display()

    def _get_window_level_numpy_array(self, image, window_level):
        """
        Get numpy array from image with appropriate window/level settings.
        
        Parameters
        ----------
        image : SimpleITK.Image
            Input image
        window_level : tuple or None
            Window level settings (window, level)
            
        Returns
        -------
        tuple
            (numpy_array, min_intensity, max_intensity)
        """
        npa = sitk.GetArrayViewFromImage(image)
        
        if not window_level:
            # Use percentiles to avoid outliers
            min_max = np.percentile(npa.flatten(), [2, 98])
            return npa, min_max[0], min_max[1]
        else:
            # Use specified window/level
            return (
                npa,
                window_level[1] - window_level[0] / 2.0,
                window_level[1] + window_level[0] / 2.0,
            )

    def update_display(self):
        """Update the display with current slice positions and ROIs."""
        # Calculate middle slice based on current slider positions
        self.middle_slice = round((self.sliders[0].get() + self.sliders[1].get()) * 0.46)
        
        # Update images for each view
        for i, ax in enumerate([self.back_ax, self.front_ax, self.middle_ax]):
            # Remove previous image
            if ax.images:
                ax.images[0].remove()
                
            # Show current slice
            ax.imshow(
                self.npa[self.sliders[i].get() if i < 2 else self.middle_slice, :, :],
                cmap=plt.cm.Greys_r,
                vmin=self.min_intensity,
                vmax=self.max_intensity,
            )
            ax.set_axis_off()

        # Update ROI visibility based on current slice
        if self.rois:
            for roi_data in self.rois:
                if (
                    self.sliders[0].get() >= roi_data[3][0]
                    and self.sliders[1].get() <= roi_data[3][1]
                ):
                    roi_data[0].set_visible(True)
                else:
                    roi_data[0].set_visible(False)
                    
        # Update title and redraw figures
        self.middle_ax.set_title(f"Selected {len(self.rois)} ROIs")
        for fig in [self.back_fig, self.front_fig, self.middle_fig]:
            fig.canvas.draw_idle()

    def add_roi_data(self, roi_data):
        """
        Add regions of interest to this GUI.
        
        Parameters
        ----------
        roi_data : list of tuples
            Each tuple contains ((min_x,max_x), (min_y,max_y), (min_z,max_z))
        """
        self._validate_rois(roi_data)

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
            self.middle_ax.add_patch(self.rois[-1][0])
        self.update_display()

    def set_rois(self, roi_data):
        """
        Clear existing ROIs and set to the given ones.
        
        Parameters
        ----------
        roi_data : list of tuples
            Each tuple contains ((min_x,max_x), (min_y,max_y), (min_z,max_z))
        """
        self._clear_all_data()
        self.add_roi_data(roi_data)

    def _validate_rois(self, roi_data):
        """
        Validate that ROIs are within image bounds.
        
        Parameters
        ----------
        roi_data : list of tuples
            Each tuple contains ((min_x,max_x), (min_y,max_y), (min_z,max_z))
            
        Raises
        ------
        ValueError
            If ROIs are invalid or outside image bounds
        """
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
        """Add the currently selected ROI to the list."""
        if self.roi_selector.visible:
            self.roi_selector.set_visible(False)
            # Extent is in sub-pixel coordinates, we need it in pixels/voxels
            roi_extent = [int(round(coord)) for coord in self.roi_selector.extents]
            # We keep the patch for display and the x,y,z ranges of the ROI
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

    def _clear_all_data(self):
        """Remove all ROIs from the display."""
        for roi_data in self.rois:
            roi_data[0].remove()
        self.rois.clear()

    def clear_last(self):
        """Remove the most recently added ROI."""
        if self.rois:
            self.rois[-1][0].remove()
            self.rois.pop()
            self.update_display()

    def get_rois(self):
        """
        Get the current list of ROIs.
        
        Returns
        -------
        list of tuples
            Each tuple contains ((min_x,max_x), (min_y,max_y), (min_z,max_z))
        """
        return [
            (roi_data[1], roi_data[2], roi_data[3])
            if self.npa.ndim == 3
            else (roi_data[1], roi_data[2])
            for roi_data in self.rois
        ]

    def onselect(self, eclick, erelease):
        """Handle the ROI selection event."""
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        # Log the selected region
        print(f"Selected region: x1={x1}, y1={y1}, x2={x2}, y2={y2}")

        # Update the display
        self.update_display()

    def quit_application(self):
        """Close the application."""
        self.root.destroy()
    
    def crop_moving(self):
        """
        Crop the moving image to the selected ROI.
        """
        # Add the current ROI
        self.add_roi()
        
        # Get ROIs from GUI
        specified_rois = self.get_rois()
        print(specified_rois)
        
        # Select the one ROI we will work on
        ROI_INDEX = 0

        # Crop the image
        if specified_rois:
            roi = specified_rois[ROI_INDEX]
            self.image = self.image[
                roi[0][0]:roi[0][1] + 1, 
                roi[1][0]:roi[1][1] + 1, 
                roi[2][0]:roi[2][1] + 1
            ]
            
            # Show a success popup
            self._show_success_popup()
        else:
            print("No ROI selected. Please select a region before cropping.")
    
    def _show_success_popup(self):
        """Show a success popup with continue button."""
        self.popup = Toplevel(self.window)
        self.popup.title("Success")
        self.popup.geometry('200x100')
        
        message_label = Label(self.popup, text="Cropping successful!")
        message_label.pack(pady=10)

        continue_button = Button(
            self.popup, 
            text="Continue", 
            command=self.launch_registration_acquisition
        )
        continue_button.pack()
        
    def launch_registration_acquisition(self):
        """Launch the registration acquisition screen."""
        self.popup.destroy()  # Close the popup window
        self.window.pack_forget()
        
        # Define window levels for registration window
        moving_window_level = [250, 700]
        fixed_window_level = [39, 60]
        
        # Launch registration
        RegistrationPointDataAcquisition(
            self.image,
            self.frames_list[2],
            self.root,
            fixed_window_level,
            moving_window_level
        )