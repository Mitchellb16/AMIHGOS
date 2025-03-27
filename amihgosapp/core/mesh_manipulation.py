#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MeshManipulationWindow module - GUI for manipulating and subtracting head meshes from helmet templates
Written by Mitchell Bishop and optimized with Claude AI
"""
from datetime import date
import os
import pyvista as pv
import pymeshfix
from pyvistaqt import BackgroundPlotter
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

# Import from new locations when available
from amihgosapp.utils.resource_utils import get_template_path


class ManipulationButton:
    """Base class for manipulation buttons (rotation, translation)."""
    
    def __init__(self, label, window, layout):
        """
        Initialize a manipulation button group.
        
        Parameters
        ----------
        label : str
            Label for the button group
        window : MeshManipulationWindow
            Parent window
        layout : QLayout
            Layout to add widgets to
        """
        self.label = label
        self.window = window
        self.value = 0
        self.layout = layout
        self.create_widgets()

    def create_widgets(self):
        """Create the button widgets."""
        # Add minus button
        self.minus_button = QtWidgets.QPushButton("-", self.window)
        self.minus_button.clicked.connect(self.on_minus_click)
        self.layout.addWidget(self.minus_button)

        # Add a label to track the value
        self.value_label = QtWidgets.QLabel(f"{self.label}:{self.value}", self.window)
        self.layout.addWidget(self.value_label)

        # Add plus button
        self.plus_button = QtWidgets.QPushButton("+", self.window)
        self.plus_button.clicked.connect(self.on_plus_click)
        self.layout.addWidget(self.plus_button)

    def on_minus_click(self):
        """Handle minus button click."""
        self.decrease_value()
        self.update_value()

    def on_plus_click(self):
        """Handle plus button click."""
        self.increase_value()
        self.update_value()

    def update_value(self):
        """Update the displayed value and perform the action."""
        self.value_label.setText(f"{self.label}:{self.value}")
        self.perform_action()

    def decrease_value(self):
        """Decrease the value (implemented by subclasses)."""
        raise NotImplementedError("Subclasses should implement this!")

    def increase_value(self):
        """Increase the value (implemented by subclasses)."""
        raise NotImplementedError("Subclasses should implement this!")

    def perform_action(self):
        """Perform the action associated with the button (implemented by subclasses)."""
        raise NotImplementedError("Subclasses should implement this!")


class TranslationButton(ManipulationButton):
    """Button for translating the mesh along an axis."""
    
    def __init__(self, axis, window, layout):
        """
        Initialize a translation button.
        
        Parameters
        ----------
        axis : str
            Axis label (LR, PA, DV)
        window : MeshManipulationWindow
            Parent window
        layout : QLayout
            Layout to add widgets to
        """
        super().__init__(axis, window, layout)

    def decrease_value(self):
        """Decrease translation value."""
        self.value -= 0.5

    def increase_value(self):
        """Increase translation value."""
        self.value += 0.5

    def perform_action(self):
        """Perform translation."""
        self.window.translate_mesh()


class RotationButton(ManipulationButton):
    """Button for rotating the mesh around an axis."""
    
    def __init__(self, axis, window, layout, step_size=2):
        """
        Initialize a rotation button.
        
        Parameters
        ----------
        axis : str
            Axis label (X, Y, Z)
        window : MeshManipulationWindow
            Parent window
        layout : QLayout
            Layout to add widgets to
        step_size : float, optional
            Step size for rotation, by default 2
        """
        self.step_size = step_size
        super().__init__(axis, window, layout)

    def decrease_value(self):
        """Decrease rotation angle."""
        self.value -= self.step_size

    def increase_value(self):
        """Increase rotation angle."""
        self.value += self.step_size

    def perform_action(self):
        """Perform rotation."""
        self.window.rotate_mesh()


class MeshManipulationWindow(QtWidgets.QWidget):
    """
    GUI window for manipulating and subtracting head meshes from helmet templates.
    
    This window allows interactive adjustment of mesh position, orientation, and scale
    before performing a boolean subtraction to create a custom helmet.
    """
    
    def __init__(self, helmet_mesh_file, head_mesh_file, animal_name='Example'):
        """
        Initialize the mesh manipulation window.
        
        Parameters
        ----------
        helmet_mesh_file : str
            Path to helmet template STL file
        head_mesh_file : str
            Path to head mesh STL file
        animal_name : str, optional
            Name to use for labeling the helmet, by default 'Example'
        """
        super().__init__()
        print(f"Loading meshes: {helmet_mesh_file}, {head_mesh_file}")
        
        # Load helmet and head meshes
        self.helmet_mesh_file = helmet_mesh_file
        self.head_mesh_file = head_mesh_file
        self.animal_name = animal_name
        
        # check if one of default helmet types
        if 'Flat' in self.helmet_mesh_file:
            self.helmet_type = 'Flat'
        elif 'Winged' in self.helmet_mesh_file:
            self.helmet_type = 'Winged'
        else:
            self.helmet_type = None
        
        # Load and triangulate meshes
        helmet_mesh = pv.read(self.helmet_mesh_file).triangulate(inplace=True)
        head_mesh = pv.read(self.head_mesh_file).triangulate(inplace=True)
        
        # Clean the head mesh
        head_mesh.clean(inplace=True)
        
        # Determine chin piece based on helmet type and preprocess
        if self.helmet_type is None:
            self.og_head_mesh, self.helmet_mesh = self.mesh_preprocess(head_mesh, 
                                                                       helmet_mesh, 
                                                                       name=self.animal_name)
        else: 
            if self.helmet_type == 'Flat':
                self.chin_mesh_file = get_template_path('FlatChinPiece.stl')
                chin_mesh = pv.read(self.chin_mesh_file).triangulate(inplace=True)
            elif self.helmet_type == 'Winged':
                self.chin_mesh_file = get_template_path('WingedChinPieceTemplate2025.stl')
                chin_mesh = pv.read(self.chin_mesh_file).triangulate(inplace=True)
        
            self.og_head_mesh, self.helmet_mesh, self.chin_mesh = self.mesh_preprocess(head_mesh,
                                                                                       helmet_mesh,
                                                                                       chin_mesh, 
                                                                                       name=self.animal_name)
                
        # Connect quit signals
        self.destroyed.connect(QtWidgets.qApp.quit)
        self.destroyed.connect(self.close_plotter)

        # Set default transformation parameters
        self.offset = [0, 0, 0]
        self.scaling_factor = 1.0
        self.plotter = None  # Initialize plotter to None
        
        # Create a copy of the original mesh for manipulation
        self.head_mesh = self.og_head_mesh.copy(deep=True)
        
        # Initialize UI
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Plot button
        plot_button = QtWidgets.QPushButton("Plot meshes", self)
        plot_button.clicked.connect(self.create_pvplotter)
        self.layout.addWidget(plot_button)

        # Rotation controls
        self._setup_rotation_controls()
        
        # Expansion controls
        self._setup_expansion_controls()
        
        # Translation controls
        self._setup_translation_controls()
        
        # Smoothing controls
        self._setup_smoothing_controls()
                    
        # Chin piece toggle
        self._setup_chin_controls()

        # Operation buttons
        self._setup_operation_buttons()

        # Set the layout to the main window
        self.setLayout(self.layout)

    def _setup_rotation_controls(self):
        """Set up rotation control buttons."""
        rotation_frame = QtWidgets.QFrame(self)
        rotation_layout = QtWidgets.QHBoxLayout(rotation_frame)
        self.layout.addWidget(rotation_frame)

        # Add Rotation buttons
        self.rotation_button_X = RotationButton('Rotation X', self, rotation_layout)
        self.rotation_button_Y = RotationButton('Rotation Y', self, rotation_layout)
        self.rotation_button_Z = RotationButton('Rotation Z', self, rotation_layout)

    def _setup_expansion_controls(self):
        """Set up expansion control buttons."""
        expand_frame = QtWidgets.QFrame(self)
        expand_layout = QtWidgets.QHBoxLayout(expand_frame)
        self.layout.addWidget(expand_frame)

        # Minus button
        minus_button = QtWidgets.QPushButton("-", self)
        minus_button.clicked.connect(self.expand_mesh_minus)
        expand_layout.addWidget(minus_button)

        # Label
        self.scaling_label = QtWidgets.QLabel(f"Expansion: {self.scaling_factor:.2f}", self)
        expand_layout.addWidget(self.scaling_label)

        # Plus button
        plus_button = QtWidgets.QPushButton("+", self)
        plus_button.clicked.connect(self.expand_mesh_plus)
        expand_layout.addWidget(plus_button)

    def _setup_translation_controls(self):
        """Set up translation control buttons."""
        translation_frame = QtWidgets.QFrame(self)
        translation_layout = QtWidgets.QHBoxLayout(translation_frame)
        self.layout.addWidget(translation_frame)

        # Create translation buttons for each axis
        self.LR_translation = TranslationButton('LR', self, translation_layout)  # Left-Right
        self.PA_translation = TranslationButton('PA', self, translation_layout)  # Posterior-Anterior
        self.DV_translation = TranslationButton('DV', self, translation_layout)  # Dorsal-Ventral
        
        # Store in list for easier access
        self.translation_list = [self.LR_translation, self.PA_translation, self.DV_translation]

    def _setup_smoothing_controls(self):
        """Set up smoothing slider control."""
        # Label for smoothing
        self.smoothing_label = QtWidgets.QLabel("Smoothing: 0.00", self)
        self.smoothing_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.smoothing_label)

        # Slider for smoothing
        self.smoothing_slider = QtWidgets.QSlider(Qt.Horizontal, self)
        self.smoothing_slider.setRange(0, 100)  # Integer range 0-100
        self.smoothing_slider.setValue(0)  # Start at 0
        self.smoothing_slider.valueChanged.connect(self.update_smoothing_label)
        self.layout.addWidget(self.smoothing_slider)

    def _setup_chin_controls(self):
        """Set up chin piece controls."""
        self.chin_toggle = QtWidgets.QCheckBox("Subtract chin piece?", self)
        self.chin_toggle.clicked.connect(self.ignore_chin)
        self.chin_subtract_bool = False  # Initially don't subtract chin
        self.layout.addWidget(self.chin_toggle)

    def _setup_operation_buttons(self):
        """Set up operation buttons (subtract, save, close)."""
        # Subtraction button
        send_button = QtWidgets.QPushButton("Send for subtraction", self)
        send_button.clicked.connect(self.send_for_subtraction)
        send_button.setStyleSheet("background-color: green")
        self.layout.addWidget(send_button)
        
        # Save button (disabled until subtraction is done)
        self.save_button = QtWidgets.QPushButton("Save", self)
        self.save_button.clicked.connect(self.save_mesh)
        self.save_button.setDisabled(True)
        self.save_button.setStyleSheet("background-color: grey")
        self.layout.addWidget(self.save_button)

        # Close button
        close_button = QtWidgets.QPushButton("Close", self)
        close_button.clicked.connect(self.close_window)
        self.layout.addWidget(close_button)

    def create_pvplotter(self):
        """Create and initialize the PyVista plotter."""
        self.plotter = BackgroundPlotter(off_screen=False, notebook=False)
        self.plotter.add_mesh(self.helmet_mesh)
        self.plotter.add_mesh(self.chin_mesh)
        self.head_actor = self.plotter.add_mesh(self.head_mesh, color='magenta')
        self.plotter.show_bounds(grid='front', location='outer', all_edges=True)
        self.plotter.show()

    def close_plotter(self):
        """Close the PyVista plotter if it exists."""
        if hasattr(self, 'plotter') and self.plotter is not None:
            self.plotter.close()

    def rotate_mesh(self):
        """Rotate the mesh based on rotation button values."""
        self.update_plotter()

    def expand_mesh_plus(self):
        """Increase the expansion factor."""
        self.scaling_factor += 0.01
        self.scaling_label.setText(f"Expansion: {self.scaling_factor:.2f}")
        self.update_plotter()

    def expand_mesh_minus(self):
        """Decrease the expansion factor."""
        self.scaling_factor -= 0.01
        self.scaling_label.setText(f"Expansion: {self.scaling_factor:.2f}")
        self.update_plotter()

    def translate_mesh(self):
        """Translate the mesh based on translation button values."""
        self.update_plotter()
        
    def update_smoothing_label(self, value):
        """Update the smoothing label when slider value changes."""
        float_value = value / 100.0
        self.smoothing_label.setText(f"Smoothing: {float_value:.2f}")
        self.update_plotter()
    
    def ignore_chin(self):
        """Toggle chin piece subtraction."""
        self.chin_subtract_bool = self.chin_toggle.isChecked()
    
    def send_for_subtraction(self):
        """Perform the boolean subtraction operation."""
        # Check if head mesh is manifold and try to repair if not
        if not self.head_mesh.is_manifold:
            print("Warning, non-manifold head segmentation, attempting repair. "
                  "May cause crashing during subtraction")
            
            # Try to fix the mesh
            meshfix = pymeshfix.MeshFix(self.head_mesh)
            meshfix.repair()
            self.head_mesh = meshfix.mesh              
        
        # Save the smoothed head mesh
        head_mesh_filename = f'head_stls/{self.animal_name}_smoothed.stl'
        self.head_mesh.save(head_mesh_filename)
        print(f'Smoothed headmesh saved at {head_mesh_filename}')
        
        # Subtract chin piece if enabled
        if self.chin_subtract_bool:
            print(f"Chin mesh is manifold: {self.chin_mesh.is_manifold}")
            self.chin_bool_mesh = self.chin_mesh.boolean_difference(self.head_mesh)
            
            # Get rid of small residues from chin topology
            self.chin_bool_mesh.extract_largest(inplace=True)
        
        # Perform the main boolean subtraction    
        bool_mesh = self.helmet_mesh.boolean_difference(self.head_mesh)
        
        # Smooth parts with sharp edges
        # Define a box around the region to smooth
        bounds = [-21, 20, -20, 20, -20, -3]
        clipped = bool_mesh.clip_box(bounds)
        clipping = bool_mesh.clip_box(bounds, invert=False)
        surface = clipping.extract_geometry()
        
        # Apply Taubin smoothing to reduce sharp edges
        smooth = surface.smooth_taubin(n_iter=70, pass_band=0.04, 
                                      non_manifold_smoothing=True, 
                                      normalize_coordinates=True)
        smooth.fill_holes(hole_size=20, inplace=True)
        
        # Combine the smoothed part with the main mesh
        self.final_mesh = clipped + smooth
        self.final_mesh = self.final_mesh.extract_surface()
        
        # Enable save button and update display
        self.save_button.setDisabled(False)
        self.save_button.setStyleSheet("background-color: lightgreen")
        self.update_plotter(final_plot=True)
        
    def save_mesh(self):
        """Save the final helmet mesh and chin piece if enabled."""
        # Create directory if it doesn't exist
        if not os.path.exists('helmets'):
            os.makedirs('helmets')
            
        # Generate filename with metadata
        self.save_file = (f'helmets/{date.today()}_{self.animal_name}_'
                          f'{str(self.scaling_factor)[2:]}_DV_'
                          f'{str(self.DV_translation.value)}.stl')
        
        # Save the helmet mesh
        self.final_mesh.extract_geometry().save(self.save_file)
        
        # Save chin piece if it was subtracted
        if self.chin_subtract_bool:
            chin_save_file = f'helmets/{date.today()}_{self.animal_name}_chinpiece.stl'
            self.chin_bool_mesh.extract_geometry().save(chin_save_file)
            success_message = f'{self.save_file} and chinpiece successfully saved!'
        else:
            success_message = f'{self.save_file} successfully saved!'
            
        # Display success message
        message = QtWidgets.QLabel(success_message)
        self.layout.addWidget(message)
        print(success_message)

    def update_plotter(self, final_plot=False):
        """Update the plotter with current mesh transformations."""
        if not hasattr(self, 'plotter') or self.plotter is None:
            return
            
        # Remove the previous head actor
        if hasattr(self, 'head_actor') and self.head_actor is not None:
            self.plotter.remove_actor(self.head_actor, render=False)
        
        if final_plot:
            # Show final result after subtraction
            self.plotter.clear()
            self.plotter.add_mesh(self.final_mesh)
            if self.chin_subtract_bool and hasattr(self, 'chin_bool_mesh'):
                self.plotter.add_mesh(self.chin_bool_mesh)
        else:
            # Apply transformations to the mesh
            # Start with a fresh copy of the original
            self.head_mesh = self.og_head_mesh.copy(deep=True)
            
            # Apply scaling
            self.head_mesh = self.head_mesh.scale([self.scaling_factor, 1, 1])
            
            # Apply smoothing
            smoothing_factor = self.smoothing_slider.value() / 100.0
            if smoothing_factor > 0:
                self.head_mesh = self.head_mesh.smooth(
                    n_iter=20,
                    relaxation_factor=smoothing_factor
                )
            
            # Apply translation
            self.head_mesh.points = self.head_mesh.points + [
                self.LR_translation.value,
                self.PA_translation.value,
                self.DV_translation.value
            ]
            
            # Apply rotation
            self.head_mesh.rotate_x(self.rotation_button_X.value, inplace=True)
            self.head_mesh.rotate_y(self.rotation_button_Y.value, inplace=True)
            self.head_mesh.rotate_z(self.rotation_button_Z.value, inplace=True)
            
            # Add the updated mesh to the plotter
            self.head_actor = self.plotter.add_mesh(self.head_mesh, color='magenta')
            
        # Update the plotter display
        self.plotter.update()

    def close_window(self):
        """Close the window."""
        self.close()

    def run(self):
        """Show the window and start the event loop."""
        self.show()

    def mesh_preprocess(self, head_mesh, helmet_mesh, chin_mesh,
                        name='Example', separate=False, scaling=1.00):
        """
        Prepare the head and helmet meshes for manipulation.
        
        Parameters
        ----------
        head_mesh : pyvista.PolyData
            Head mesh to position
        helmet_mesh : pyvista.PolyData
            Helmet template mesh
        name : str, optional
            Name to emboss on the helmet, by default 'Example'
        separate : bool, optional
            Whether to keep meshes separate, by default False
        scaling : float, optional
            Initial scaling factor, by default 1.00
            
        Returns
        -------
        tuple
            (head_mesh, helmet_mesh) - Preprocessed meshes
        """
        print(f'Before preprocessing, head mesh is manifold: {head_mesh.is_manifold}')
        
               
        # Scale up and rotate head mesh
        head_mesh.scale([scaling, scaling, scaling], inplace=True)
        head_mesh.rotate_x(270, inplace=True)
        print(f'After scaling and rotating, head mesh is manifold: {head_mesh.is_manifold}')
    
        # Align the centers of both meshes at 0 then translate 
        helmet_mesh.points -= helmet_mesh.center
        head_mesh.points -= head_mesh.center
        print(f'After centering, head mesh is manifold: {head_mesh.is_manifold}')
        
        # Format [LR, PA, DV] or [X, Y, Z]
        LR_offset = 0.7
        PA_offset = -9
        DV_offset = -3.5
        
        offset = [
            LR_offset,
            helmet_mesh.bounds[2] - head_mesh.bounds[2] + PA_offset,
            helmet_mesh.bounds[5] - head_mesh.bounds[5] + DV_offset
        ]
    
        # Translate the head mesh to match the helmet mesh
        head_mesh.translate(offset, inplace=True)
        print(f'After translating, head mesh is manifold: {head_mesh.is_manifold}')
        
        if self.helmet_type == None:
            return head_mesh, helmet_mesh
        
        # Create text object for embossing
        text = pv.Text3D(name, depth=0.9)
        text.scale([2.5, 2.5, 2.5], inplace=True)
        text.rotate_z(90, inplace=True)
        
        # Position text based on helmet type
        if self.helmet_type == 'Flat':
            text_offset = [31, 5, -14.5]
        elif self.helmet_type == 'Winged':
            text_offset = [27, 5, -11.8]
        text.points += text_offset
        
        # Add text to helmet to emboss
        helmet_mesh = helmet_mesh + text
            
        # Zero the center of chin mesh
        chin_mesh.points -= chin_mesh.center
        
        # Position chin piece mesh
        # Format [LR, PA, DV] or [X, Y, Z]
        chin_offset = [0, 8, -27.5]
        chin_mesh.translate(chin_offset, inplace=True)
        
        # Add text label for chin piece
        chin_text = pv.Text3D(name, depth=0.9)
        chin_text.scale([2.5, 2.5, 2.5], inplace=True)
        
        # Position text based on helmet type
        if self.helmet_type == 'Flat':
            chin_text_offset = [28, 5, -22.5]
            chin_text.rotate_z(-90, inplace=True)
            chin_text.rotate_x(180, inplace=True)
            
        elif self.helmet_type == 'Winged':
            chin_text_offset = [28, 5, -19.5]
            chin_text.rotate_z(-90, inplace=True)
            chin_text.rotate_x(180, inplace=True)
            
        chin_text.translate(chin_text_offset, inplace=True)
        chin_mesh = chin_mesh + chin_text
    
        return head_mesh, helmet_mesh, chin_mesh