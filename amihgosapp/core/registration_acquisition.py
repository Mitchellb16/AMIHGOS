#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RegistrationPointDataAcquisition module - GUI for landmark-based registration

Adapted from SimpleITK jupyter notebook tutorials
"""
import SimpleITK as sitk
from tkinter import Frame, Button, Scale, Toplevel, Label, StringVar, Entry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import from new locations when available
from amihgosapp.utils.resource_utils import get_ct_path
from amihgosapp.gui.visualize_registration import visualize_registration
from amihgosapp.core.segmentation import SegmentationScreen


class RegistrationPointDataAcquisition:
    """
    GUI for localizing corresponding points in two images for registration.
    
    This class provides a GUI for selecting corresponding landmark points in fixed and 
    moving images, then performing landmark-based registration between them.
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
        """
        Initialize the registration interface.
        
        Parameters
        ----------
        moving_image : SimpleITK.Image
            The moving image to register
        window : tkinter.Frame
            Frame to place UI elements in
        root : tkinter.Tk
            Root window
        fixed_window_level : tuple, optional
            Window level for fixed image display, by default None
        moving_window_level : tuple, optional
            Window level for moving image display, by default None
        figure_size : tuple, optional
            Size of the figure, by default (5, 4)
        known_transformation : SimpleITK.Transform, optional
            If provided, will use this transform to automatically find corresponding points
        """
        self.window = window
        self.window.pack()
        self.root = root
        self.animal_name = 'TEST'  # Default animal name
        
        # Load fixed image (template)
        fixed_dir = get_ct_path('padded_template_image.nii.gz')
        self.fixed_image = sitk.ReadImage(fixed_dir, outputPixelType=sitk.sitkFloat32)
        self.fixed_image = sitk.DICOMOrient(self.fixed_image, 'RIA')
        
        # Get numpy arrays with correct window/level settings
        self.fixed_npa, self.fixed_min_intensity, self.fixed_max_intensity = \
            self._get_window_level_numpy_array(self.fixed_image, fixed_window_level)
        
        self.moving_image = moving_image
        self.moving_npa, self.moving_min_intensity, self.moving_max_intensity = \
            self._get_window_level_numpy_array(self.moving_image, moving_window_level)
        
        # Initialize point lists
        self.fixed_point_indexes = []
        self.moving_point_indexes = []
        self.click_history = []  # Keep history for undo functionality
        self.known_transformation = known_transformation
        self.text_and_marker_color = "red"

        # Set up UI components and figures
        self._create_ui()
        self._setup_figures(figure_size)
        
        # Initialize display
        self._update_initial_display()

    def _create_ui(self):
        """Create UI components (buttons, sliders)."""
        # Create buttons for point manipulation
        self.clearlast_button = Button(
            self.window,
            text="Clear Last", 
            command=self.clear_last
        )
        self.clearlast_button.grid(column=1, row=1)

        self.clearall_button = Button(
            self.window,
            text="Clear All", 
            command=self.clear_all
        )
        self.clearall_button.grid(column=1, row=2)
        
        self.save_points_button = Button(
            self.window, 
            text='Save Points and Register', 
            command=self.save_points
        )
        self.save_points_button.grid(column=1, row=3)
        
        # Make frames for image displays
        self.fixed_frame = Frame(self.window)
        self.fixed_frame.grid(column=0, row=2)
        
        self.moving_frame = Frame(self.window)
        self.moving_frame.grid(column=3, row=2)
        
        # Create sliders for 3D images
        self.fixed_slider = self.moving_slider = None
        if self.fixed_npa.ndim == 3:
            self.fixed_slider = Scale(
                self.fixed_frame,
                from_=0,
                to=self.fixed_npa.shape[0] - 1,
                command=self._on_slice_slider_value_change,
            )
            self.fixed_slider.set(274)  # Default position
            self.fixed_slider.pack()
            
            self.moving_slider = Scale(
                self.moving_frame,
                from_=0,
                to=self.moving_npa.shape[0] - 1,
                command=self._on_slice_slider_value_change,
            )
            self.moving_slider.set(140)  # Default position
            self.moving_slider.pack()

    def _setup_figures(self, figure_size):
        """Set up matplotlib figures for visualization."""
        # Create figures for fixed and moving images
        self.fixed_fig, self.fixed_axes = plt.subplots(1, 1, figsize=figure_size)
        self.moving_fig, self.moving_axes = plt.subplots(1, 1, figsize=figure_size)
        
        # Add figures to frames
        self.fixed_canvas = FigureCanvasTkAgg(self.fixed_fig, self.fixed_frame)
        self.fixed_canvas.get_tk_widget().pack()
        
        self.moving_canvas = FigureCanvasTkAgg(self.moving_fig, self.moving_frame)
        self.moving_canvas.get_tk_widget().pack()
                
        # Connect mouse button press events
        self.fixed_fig.canvas.mpl_connect("button_press_event", self)
        self.moving_fig.canvas.mpl_connect("button_press_event", self)

    def _update_initial_display(self):
        """Initialize the display with images."""
        # Display initial images
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
        
        # Update display with titles, points, etc.
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
            return npa, npa.min(), npa.max()
        else:
            return (
                npa,
                window_level[1] - window_level[0] / 2.0,
                window_level[1] + window_level[0] / 2.0,
            )

    def _on_slice_slider_value_change(self, _):
        """Handle slider value changes."""
        self.update_display()

    def update_display(self):
        """Update the display with current slice positions and points."""
        # Store current zoom levels
        fixed_xlim = self.fixed_axes.get_xlim()
        fixed_ylim = self.fixed_axes.get_ylim()
        moving_xlim = self.moving_axes.get_xlim()
        moving_ylim = self.moving_axes.get_ylim()

        # Update fixed image display
        self._update_fixed_image_display(fixed_xlim, fixed_ylim)
        
        # Update moving image display
        self._update_moving_image_display(moving_xlim, moving_ylim)

        # Refresh canvases
        self.fixed_fig.canvas.draw_idle()
        self.moving_fig.canvas.draw_idle()

    def _update_fixed_image_display(self, xlim, ylim):
        """Update the fixed image display with current points."""
        self.fixed_axes.clear()
        
        # Display the current slice
        self.fixed_axes.imshow(
            self.fixed_npa[self.fixed_slider.get(), :, :]
            if self.fixed_slider
            else self.fixed_npa,
            cmap=plt.cm.Greys_r,
            vmin=self.fixed_min_intensity,
            vmax=self.fixed_max_intensity,
        )
        
        # Display points on this slice
        text_x_offset = -10
        text_y_offset = -10
        
        for i, pnt in enumerate(self.fixed_point_indexes):
            # Only show points on the current slice
            if ((self.fixed_slider and int(pnt[2] + 0.5) == self.fixed_slider.get()) 
                or not self.fixed_slider):
                # Draw the point marker
                self.fixed_axes.scatter(
                    pnt[0], pnt[1], s=90, marker="+", color=self.text_and_marker_color
                )
                
                # Calculate text position
                text_in_data_coords = self.fixed_axes.transData.transform([pnt[0], pnt[1]])
                text_in_data_coords = self.fixed_axes.transData.inverted().transform(
                    (text_in_data_coords[0] + text_x_offset, text_in_data_coords[1] + text_y_offset)
                )
                
                # Add point label
                self.fixed_axes.text(
                    text_in_data_coords[0],
                    text_in_data_coords[1],
                    str(i),
                    color=self.text_and_marker_color,
                )
                
        # Set title and axis properties
        self.fixed_axes.set_title(f"Fixed image - localized {len(self.fixed_point_indexes)} points")
        self.fixed_axes.set_axis_off()
        
        # Restore zoom level
        self.fixed_axes.set_xlim(xlim)
        self.fixed_axes.set_ylim(ylim)

    def _update_moving_image_display(self, xlim, ylim):
        """Update the moving image display with current points."""
        self.moving_axes.clear()
        
        # Display the current slice
        self.moving_axes.imshow(
            self.moving_npa[self.moving_slider.get(), :, :]
            if self.moving_slider
            else self.moving_npa,
            cmap=plt.cm.Greys_r,
            vmin=self.moving_min_intensity,
            vmax=self.moving_max_intensity,
        )
        
        # Display points on this slice
        text_x_offset = -10
        text_y_offset = -10
        
        for i, pnt in enumerate(self.moving_point_indexes):
            # Only show points on the current slice
            if ((self.moving_slider and int(pnt[2] + 0.5) == self.moving_slider.get()) 
                or not self.moving_slider):
                # Draw the point marker
                self.moving_axes.scatter(
                    pnt[0], pnt[1], s=90, marker="+", color=self.text_and_marker_color
                )
                
                # Calculate text position
                text_in_data_coords = self.moving_axes.transData.transform([pnt[0], pnt[1]])
                text_in_data_coords = self.moving_axes.transData.inverted().transform(
                    (text_in_data_coords[0] + text_x_offset, text_in_data_coords[1] + text_y_offset)
                )
                
                # Add point label
                self.moving_axes.text(
                    text_in_data_coords[0],
                    text_in_data_coords[1],
                    str(i),
                    color=self.text_and_marker_color,
                )
                
        # Set title and axis properties
        self.moving_axes.set_title(f"Moving image - localized {len(self.moving_point_indexes)} points")
        self.moving_axes.set_axis_off()
        
        # Restore zoom level
        self.moving_axes.set_xlim(xlim)
        self.moving_axes.set_ylim(ylim)

    def clear_all(self):
        """Remove all points from both images."""
        self.fixed_point_indexes.clear()
        self.moving_point_indexes.clear()
        self.click_history.clear()
        self.update_display()

    def clear_last(self):
        """Remove the most recently added point pair."""
        # Direct approach: just remove the last point from each list
        if self.fixed_point_indexes:
            self.fixed_point_indexes.pop()
        if self.moving_point_indexes:
            self.moving_point_indexes.pop()
        
        # Clear the click history to avoid inconsistencies
        self.click_history.clear()
        
        self.update_display()

    def multires_registration(self, fixed_image, moving_image, initial_transform):
        """
        Perform multi-resolution registration between fixed and moving images.
        
        Parameters
        ----------
        fixed_image : SimpleITK.Image
            Fixed (reference) image
        moving_image : SimpleITK.Image
            Moving image to register to fixed image
        initial_transform : SimpleITK.Transform
            Initial transform estimate
            
        Returns
        -------
        tuple
            (final_transform, metric_value)
        """
        registration_method = sitk.ImageRegistrationMethod()
        
        # Set up registration parameters
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
        
        # Run registration
        final_transform = registration_method.Execute(fixed_image, moving_image)
        
        # Log results
        print(f"Final metric value: {registration_method.GetMetricValue()}")
        print(
            f"Optimizer's stopping condition: {registration_method.GetOptimizerStopConditionDescription()}"
        )
        print(f"Final transformation parameters: {final_transform.GetParameters()}")
        
        return (final_transform, registration_method.GetMetricValue())
    
    def get_points(self):
        """
        Get the selected points in physical coordinates.
        
        Returns
        -------
        tuple
            (fixed_point_list, moving_point_list) in physical coordinates
        
        Raises
        ------
        Exception
            If the number of points in fixed and moving images doesn't match
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
        Handle click events in the image views.
        
        Parameters
        ----------
        event : matplotlib.backend_bases.MouseEvent
            Mouse click event
        """
        # Handle clicks in the fixed image
        if event.inaxes == self.fixed_axes:
            self._handle_fixed_image_click(event)
                
        # Handle clicks in the moving image
        elif event.inaxes == self.moving_axes:
            self._handle_moving_image_click(event)
                
    def _handle_fixed_image_click(self, event):
        """Handle click in the fixed image."""
        # Only add a point if we have equal or fewer fixed points than moving points
        if len(self.fixed_point_indexes) - len(self.moving_point_indexes) <= 0:
            # Record the point coordinates
            point = (
                (event.xdata, event.ydata, self.fixed_slider.get())
                if self.fixed_slider
                else (event.xdata, event.ydata)
            )
            self.fixed_point_indexes.append(point)
            self.click_history.append(self.fixed_point_indexes)
            
            # If we know the transformation, add corresponding point in moving image
            if self.known_transformation:
                self._add_corresponding_moving_point(point)
                
            # Update the display
            self.update_display()
            
    def _handle_moving_image_click(self, event):
        """Handle click in the moving image."""
        # Only add a point if we have equal or fewer moving points than fixed points
        if len(self.moving_point_indexes) - len(self.fixed_point_indexes) <= 0:
            # Record the point coordinates
            point = (
                (event.xdata, event.ydata, self.moving_slider.get())
                if self.moving_slider
                else (event.xdata, event.ydata)
            )
            self.moving_point_indexes.append(point)
            self.click_history.append(self.moving_point_indexes)
            
            # If we know the transformation, add corresponding point in fixed image
            if self.known_transformation:
                self._add_corresponding_fixed_point(point)
                
            # Update the display
            self.update_display()
            
    def _add_corresponding_moving_point(self, fixed_point):
        """
        Add a point in the moving image corresponding to a fixed image point.
        
        Parameters
        ----------
        fixed_point : tuple
            Point in the fixed image (in index coordinates)
        """
        # Convert fixed point from index to physical space
        fixed_point_physical = self.fixed_image.TransformContinuousIndexToPhysicalPoint(fixed_point)
        
        # Transform to moving image physical space
        moving_point_physical = self.known_transformation.TransformPoint(fixed_point_physical)
        
        # Convert to moving image index space
        moving_point_indexes = self.moving_image.TransformPhysicalPointToContinuousIndex(
            moving_point_physical
        )
        
        # Add the point
        self.moving_point_indexes.append(moving_point_indexes)
        self.click_history.append(self.moving_point_indexes)
        
        # Update moving image slice if needed
        if self.moving_slider:
            z_index = int(moving_point_indexes[2] + 0.5)
            if (self.moving_slider.cget('to') >= z_index >= self.moving_slider.cget('from')):
                self.moving_slider.set(z_index)
                
    def _add_corresponding_fixed_point(self, moving_point):
        """
        Add a point in the fixed image corresponding to a moving image point.
        
        Parameters
        ----------
        moving_point : tuple
            Point in the moving image (in index coordinates)
        """
        # Convert moving point from index to physical space
        moving_point_physical = self.moving_image.TransformContinuousIndexToPhysicalPoint(moving_point)
        
        # Transform to fixed image physical space
        inverse_transform = self.known_transformation.GetInverse()
        fixed_point_physical = inverse_transform.TransformPoint(moving_point_physical)
        
        # Convert to fixed image index space
        fixed_point_indexes = self.fixed_image.TransformPhysicalPointToContinuousIndex(
            fixed_point_physical
        )
        
        # Add the point
        self.fixed_point_indexes.append(fixed_point_indexes)
        self.click_history.append(self.fixed_point_indexes)
        
        # Update fixed image slice if needed
        if self.fixed_slider:
            z_index = int(fixed_point_indexes[2] + 0.5)
            if (self.fixed_slider.cget('to') >= z_index >= self.fixed_slider.cget('from')):
                self.fixed_slider.set(z_index)
                
    def save_points(self):
        """
        Use the selected landmark points to perform registration.
        """
        try:
            # Get the manually specified points
            fixed_image_points, moving_image_points = self.get_points()
            
            # Flatten point lists for landmark initializer
            fixed_image_points_flat = [c for p in fixed_image_points for c in p]
            moving_image_points_flat = [c for p in moving_image_points for c in p]

            # Initialize a rigid transform using landmark-based initialization
            self.init_transform = sitk.LandmarkBasedTransformInitializer(
                sitk.VersorRigid3DTransform(), 
                fixed_image_points_flat, 
                moving_image_points_flat
            )
            
            print("Manual initial transformation parameters:", self.init_transform.GetParameters())

            # Perform registration
            self.final_transform, _ = self.multires_registration(
                self.fixed_image, 
                self.moving_image, 
                self.init_transform
            )
            
            # Determine padding value for resampling
            minmax_filter = sitk.MinimumMaximumImageFilter()
            minmax_filter.Execute(self.moving_image)
            min_voxel = minmax_filter.GetMinimum()
            
            # Resample moving image into fixed image space using the final transform
            self.moving_resampled = sitk.Resample(
                self.moving_image,
                self.fixed_image,
                self.final_transform,
                sitk.sitkLinear,
                min_voxel,
                self.moving_image.GetPixelID(),
            )
                    
            print('Registration Complete!')
            
            # Visualize the registration result
            visualize_registration(self.fixed_image, self.moving_resampled, root=self.root)
            
            # Show success popup with options for next steps
            self._show_success_popup()
            
        except Exception as e:
            print(f"Error during registration: {str(e)}")
            # Could add error handling UI here
        
    def _show_success_popup(self):
        """Show a success popup with continue button and name entry field."""
        self.popup = Toplevel(self.window)
        self.popup.title("Registration Complete")
        self.popup.geometry('250x150')
        
        message_label = Label(self.popup, text="Registration successful?")
        message_label.pack(pady=10)
        
        # Get user entry for name to go on helmet
        entry_label = Label(self.popup, text='Type animal name for helmet labeling')
        entry_label.pack()
        
        file_var = StringVar(self.popup, 'Animal_name')
        self.name_entry = Entry(self.popup, textvariable=file_var)
        self.name_entry.pack(pady=5)
        
        # Continue to STL generation
        continue_button = Button(
            self.popup, 
            text="Continue", 
            command=self.launch_segmentation
        )
        continue_button.pack(pady=10)
        
    def name_change(self):
        """Get the animal name from the entry field."""
        self.animal_name = self.name_entry.get()
        
    def launch_segmentation(self):
        """Launch the segmentation screen with the registered image."""
        # Get animal name for helmet label
        self.name_change()
        
        # Close windows
        self.popup.destroy()
        self.root.destroy()
        
        # Launch segmentation screen
        seg_screen = SegmentationScreen(self.moving_resampled, self.animal_name)