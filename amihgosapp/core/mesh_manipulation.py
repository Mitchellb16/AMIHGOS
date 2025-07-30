#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MeshManipulationWindow module - GUI for manipulating and subtracting head meshes from helmet templates
Written by Mitchell Bishop and optimized with Claude AI
"""
from datetime import date
import os
import pyvista as pv
#import pymeshfix # Keep this commented out until you decide to use it
from pyvistaqt import BackgroundPlotter
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

# Import from new locations when available
from amihgosapp.utils.resource_utils import get_template_path
from amihgosapp.utils.mesh_drape import perform_draping_workflow
from amihgosapp.utils.vtk_utils import offset_mesh, _perform_robust_boolean_difference, _is_mesh_watertight


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

        # --- Configurable Parameters for Mesh Processing ---
        # General cleaning tolerance for merging close points
        self.GLOBAL_CLEAN_TOLERANCE = 0.01
        # Default hole size for filling general small holes (used in initial cleaning, chin, helmet)
        # This will be used in _perform_robust_boolean_difference too if its DEFAULT_HOLE_SIZE is linked to this.
        self.DEFAULT_FILL_HOLE_SIZE = 1000.0

        # Parameters specific to head mesh decimation and post-decimation healing
        self.HEAD_MESH_DECIMATION_THRESHOLD_FACES = 8000 # Only decimate if more than this many faces
        self.HEAD_MESH_DECIMATION_TARGET_REDUCTION = 0.5 # Target for head mesh decimation (e.g., 0.5 = 50% reduction)
        self.HEAD_MESH_POST_DECIMATION_FILL_HOLE_SIZE = 500.0 # Increased significantly for decimation-induced holes

        # Parameters for final helmet clipping and smoothing
        self.FINAL_CLIPPING_BOUNDS = [-25, 22, -23, 23, -12, -6]
        self.SMOOTHING_ITERATIONS = 70
        self.SMOOTHING_PASS_BAND = 0.04
        self.SMOOTHING_FILL_HOLE_SIZE = 20.0 # For the smoothed surface section

        # Debugging flags - set to True/False as needed
        self.DEBUG_HEAD_MESH_HEALING_PLOT = True # To visually inspect head mesh after decimation+healing
        self.DEBUG_BOOLEAN_PLOTS = True # Flag for _perform_robust_boolean_difference debug plots
        # --- End Configurable Parameters ---

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
        # Using the centralized GLOBAL_CLEAN_TOLERANCE
        head_mesh.clean(tolerance=self.GLOBAL_CLEAN_TOLERANCE, inplace=True)

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
                self.chin_mesh_file = get_template_path('WingedChinPiece.stl')
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

        # Calculate scaling required to give Nmm of padding from L to R
        # this is actually an offset distance not a scaling
        self.scaling_factor = 0.7

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
        self.scaling_label = QtWidgets.QLabel(f"Offset(mm): {self.scaling_factor:.2f}", self)
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
        self.plotter.add_mesh(self.helmet_mesh, opacity = .8)
        self.plotter.add_mesh(self.chin_mesh)
        self.head_actor = self.plotter.add_mesh(self.head_mesh, color='magenta')
        self.plotter.show_bounds(grid='front', location='outer', all_edges=True)
        self.plotter.show()

        # Update intial plot
        self.update_plotter()

    def close_plotter(self):
        """Close the PyVista plotter if it exists."""
        if hasattr(self, 'plotter') and self.plotter is not None:
            self.plotter.close()

    def rotate_mesh(self):
        """Rotate the mesh based on rotation button values."""
        self.update_plotter()

    def expand_mesh_plus(self):
        """Increase the expansion factor."""
        self.scaling_factor += 0.1
        self.scaling_label.setText(f"Expansion: {self.scaling_factor:.2f}")
        self.update_plotter()

    def expand_mesh_minus(self):
        """Decrease the expansion factor."""
        self.scaling_factor -= 0.1
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

        print("--- Starting initial mesh preparation ---")

        # Initial cleaning for head mesh
        self.head_mesh = self.head_mesh.clean(tolerance=self.GLOBAL_CLEAN_TOLERANCE, inplace=False)
        self.head_mesh.fill_holes(hole_size=self.DEFAULT_FILL_HOLE_SIZE, inplace=True)
        self.head_mesh.compute_normals(inplace=True)
        self.head_mesh.extract_largest(inplace=True)
        self.head_mesh.clean(tolerance=self.GLOBAL_CLEAN_TOLERANCE, inplace=True)

        # --- Head Mesh Decimation and Post-Decimation Healing ---
        initial_faces = self.head_mesh.n_faces
        # Only decimate if the head mesh is large enough to benefit significantly
        if initial_faces > self.HEAD_MESH_DECIMATION_THRESHOLD_FACES:
            print(f"Decimating head mesh from {initial_faces} faces...")
            self.head_mesh.triangulate(inplace=True)
            self.head_mesh = self.head_mesh.decimate(target_reduction=self.HEAD_MESH_DECIMATION_TARGET_REDUCTION)
            print(f"Head mesh decimated to {self.head_mesh.n_faces} faces.")

            # --- IMPORTANT: Apply healing steps to head_mesh after decimation ---
            print("Applying post-decimation healing to head mesh...")
            self.head_mesh.clean(tolerance=self.GLOBAL_CLEAN_TOLERANCE, inplace=True)
            self.head_mesh = self.head_mesh.extract_surface() # Re-extract surface if decimation introduced internal issues

            # Use the specific hole size for post-decimation healing
            self.head_mesh.fill_holes(hole_size=self.HEAD_MESH_POST_DECIMATION_FILL_HOLE_SIZE, inplace=True)

            self.head_mesh.extract_largest(inplace=True)
            self.head_mesh.clean(tolerance=self.GLOBAL_CLEAN_TOLERANCE, inplace=True)
            self.head_mesh.compute_normals(inplace=True, cell_normals=False, point_normals=True)
            print("Post-decimation healing for head mesh complete.")

            # --- Optional: Debug plot for the head mesh after its healing ---
            if self.DEBUG_HEAD_MESH_HEALING_PLOT:
                print("Displaying head mesh after decimation and healing for debugging...")
                head_debug_plotter = pv.Plotter()
                head_debug_plotter.add_text("Head Mesh After Decimation + Healing", font_size=10)
                head_debug_plotter.add_mesh(self.head_mesh, color='lightgreen', opacity=0.8, show_edges=True)
                head_debug_plotter.add_mesh(self.head_mesh.extract_feature_edges(boundary_edges=True), color='black', line_width=5)
                head_debug_plotter.show()
            # --- END Optional Debug Plot ---

        
        # Drape head mesh
        head_mesh_filename = f'amihgosapp/resources/head_stls/{self.animal_name}_mmoffset{int(self.scaling_factor * 10)}.stl'
        self.head_mesh.save(head_mesh_filename)
        os.makedirs(os.path.dirname(head_mesh_filename), exist_ok=True)
        draped_dir = 'amihgosapp/resources/head_stls/'
        
        # right now the draped mesh is not watertight, and thus we can't perform the
        # subtraction directly on the draped_head_mesh
        self.draped_mesh_file, self.draped_head_mesh, self.extruded_mesh_file = perform_draping_workflow(self.head_mesh, 
                                                                                                         self.animal_name,
                                                            draped_dir
                                                            )
        
        print(f'Smoothed headmesh saved at {head_mesh_filename}')
        print(f"Head mesh (final pre-boolean) manifold: {self.head_mesh.is_manifold}, watertight: {_is_mesh_watertight(self.head_mesh)}")
        
        # --- Chin Mesh Processing ---
        # NEED TO UPDATE WITH NEW BOOLEAN FUNCTION
        if self.chin_subtract_bool:
            
            # Perform chin subtraction
            self.chin_bool_mesh_file = _perform_robust_boolean_difference(
                mesh_a_file=self.chin_mesh_file,
                mesh_b_file=head_mesh_filename,
                animal_name = self.animal_name,
                output_directory = 'helmets/',
                operation_name="chin subtraction",
                debug_plot=self.DEBUG_BOOLEAN_PLOTS # Use class-level debug flag
            )
            if self.chin_bool_mesh_file is None:
                print("Chin subtraction failed or resulted in an empty mesh. Skipping chin post-processing.")
            else:
                self.chin_bool_mesh = pv.read(self.chin_bool_mesh_file)
                print(f"Chin boolean result manifold: {self.chin_bool_mesh.is_manifold}, watertight: {_is_mesh_watertight(self.chin_bool_mesh)}")

        
        
        # Perform extruded helmet-head subtraction
        bool_mesh_file = _perform_robust_boolean_difference(
            mesh_a_file=self.helmet_mesh_file,
            mesh_b_file=self.extruded_mesh_file,
            animal_name=self.animal_name,
            operation_name="extruded helmet-head subtraction",
            output_directory = 'helmets/extruded_',
            debug_plot=self.DEBUG_BOOLEAN_PLOTS # Use class-level debug flag
        )
        # Perform final subtraction with head_mesh and extruded helmet mesh
        self.final_mesh_file = _perform_robust_boolean_difference(
            mesh_a_file=bool_mesh_file,
            mesh_b_file=head_mesh_filename,
            animal_name=self.animal_name,
            operation_name="main helmet-head subtraction",
            output_directory = 'helmets/',
            debug_plot=self.DEBUG_BOOLEAN_PLOTS # Use class-level debug flag
        )
        
        if bool_mesh_file is None:
            print("Main helmet-head subtraction failed or resulted in an empty mesh. Cannot proceed with smoothing/combination.")
            self.final_mesh = pv.PolyData()
            self.save_button.setDisabled(True)
            self.save_button.setStyleSheet("background-color: lightgray")
            self.update_plotter(final_plot=True)
            return
        
        self.final_mesh = pv.read(self.final_mesh_file)        
         
        self.save_button.setDisabled(False)

        self.update_plotter(final_plot=True)
    
    def emboss_mesh(self):
        # Create text object for embossing
        text = pv.Text3D(self.animal_name, depth=0.9)
        text.scale([2.5, 2.5, 2.5], inplace=True)
        text.rotate_z(90, inplace=True)

        # Position text based on helmet type
        if self.helmet_type == 'Flat':
            text_offset = [31, 5, -14.5]
        elif self.helmet_type == 'Winged':
            text_offset = [27, 5, -11.8]
        text.points += text_offset

        # Add text to helmet to emboss
        self.final_mesh = self.final_mesh + text

        # ZAdd text to chin mesh
        if self.chin_subtract_bool:
            
            # Add text label for chin piece
            chin_text = pv.Text3D(self.animal_name, depth=0.9)
            chin_text.scale([2.5, 2.5, 2.5], inplace=True)

            # Position text based on helmet type
            if self.helmet_type == 'Flat':
                chin_text_offset = [28, 5, -19.8]
                chin_text.rotate_z(-90, inplace=True)
                chin_text.rotate_x(180, inplace=True)

            elif self.helmet_type == 'Winged':
                chin_text_offset = [27, 5, -16]
                chin_text.rotate_z(-90, inplace=True)
                chin_text.rotate_x(180, inplace=True)

            chin_text.translate(chin_text_offset, inplace=True)
            self.chin_bool_mesh = self.chin_bool_mesh + chin_text


    def save_mesh(self):
        """Save the final helmet mesh and chin piece if enabled."""
        # Create directory if it doesn't exist
        if not os.path.exists('helmets'):
            os.makedirs('helmets')

        # Generate filename with metadata
        self.save_file = (f'helmets/{date.today()}_{self.animal_name}_offset'
                          f'{str(int(self.scaling_factor*10))}_DV'
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
            if 'auditory' not in self.helmet_mesh_file:
                self.emboss_mesh()
            self.plotter.add_mesh(self.final_mesh, color = 'grey', opacity = .5)
            
            # load original head mesh and just do rotations and translation to 
            # see how this would fit on the original head topology            
            self.head_mesh = self.og_head_mesh.copy(deep=True)
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
            
            self.plotter.add_mesh(self.head_mesh, color = 'cyan',
                                  style = 'wireframe', opacity = .5)
            if self.chin_subtract_bool and hasattr(self, 'chin_bool_mesh'):
                self.plotter.add_mesh(self.chin_bool_mesh)
        else:
            # Apply transformations to the mesh
            # Start with a fresh copy of the original
            self.head_mesh = self.og_head_mesh.copy(deep=True)

            
            # Apply smoothing
            smoothing_factor = self.smoothing_slider.value() / 100.0
            if smoothing_factor > 0:
                self.head_mesh = self.head_mesh.smooth(
                    n_iter=20,
                    relaxation_factor=smoothing_factor
                )
                
            # Apply scaling
            self.head_mesh = offset_mesh(self.head_mesh, self.scaling_factor)
            print(f'After scaling and rotating, head mesh is manifold: {self.head_mesh.is_manifold}') # Relocated print
            

            # Apply translation
            self.head_mesh.points = self.head_mesh.points + [
                self.LR_translation.value,
                self.PA_translation.value,
                self.DV_translation.value
            ]
            print(f'After centering, head mesh is manifold: {self.head_mesh.is_manifold}') # Relocated print
            print(f'After translating, head mesh is manifold: {self.head_mesh.is_manifold}') # Relocated print

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

    def mesh_preprocess(self, head_mesh, helmet_mesh, chin_mesh=None,
                        name='Example', separate=False):
        """
        Prepare the head and helmet meshes for manipulation.

        Parameters
        ----------
        head_mesh : pyvista.PolyData
            Head mesh to position
        helmet_mesh : pyvista.PolyData
            Helmet template mesh
        chin_mesh : pyvista.PolyData, optional
            Chin mesh, by default None
        name : str, optional
            Name to emboss on the helmet, by default 'Example'
        separate : bool, optional
            Whether to keep meshes separate, by default False
        """
        print(f'Before preprocessing, head mesh is manifold: {head_mesh.is_manifold}')

        # rotate head mesh
        head_mesh.rotate_x(270, inplace=True)
        # Note: The manifold check here is likely redundant as no topological changes occurred yet.
        # print(f'After scaling and rotating, head mesh is manifold: {head_mesh.is_manifold}') # Moved to update_plotter

        # Align the centers of both meshes at 0 then translate
        helmet_mesh.points -= helmet_mesh.center
        head_mesh.points -= head_mesh.center
        
        # Save the helmet mesh after this translation so it is preserved in
        # the subtraction step
        helmet_mesh.save(self.helmet_mesh_file)
        
        # print(f'After centering, head mesh is manifold: {head_mesh.is_manifold}') # Moved to update_plotter

        # initial transform of head_mesh
        # Format [LR, PA, DV] or [X, Y, Z]
        LR_offset = 0.0
        PA_offset = -2.75
        DV_offset = -3.25

        offset = [
            LR_offset,
            helmet_mesh.bounds[2] - head_mesh.bounds[2] + PA_offset,
            helmet_mesh.bounds[5] - head_mesh.bounds[5] + DV_offset
        ]

        # Translate the head mesh to match the helmet mesh
        head_mesh.translate(offset, inplace=True)
        # print(f'After translating, head mesh is manifold: {head_mesh.is_manifold}') # Moved to update_plotter

        if self.helmet_type == None:
            return head_mesh, helmet_mesh

        # Create text object for embossing
        text = pv.Text3D(name, depth=0.9)
        text.scale([2.5, 2.5, 2.5], inplace=True)
        text.rotate_z(90, inplace=True)

        # Position text based on helmet type
        if self.helmet_type == 'Flat':
            text_offset = [31, 5, -14]
        elif self.helmet_type == 'Winged':
            text_offset = [27, 5, -11.8]
        text.points += text_offset

        # Add text to helmet to emboss
        # this is just for preview, the actual text is added by the emboss
        # function after subtraction
        helmet_mesh = helmet_mesh + text

        # Zero the center of chin mesh
        if chin_mesh is not None:
            chin_mesh.points -= chin_mesh.center

            # Position chin piece mesh
            # Format [LR, PA, DV] or [X, Y, Z]
            if self.helmet_type == 'Flat':
                chin_offset = [0, 7.4, -25.5]
            if self.helmet_type == 'Winged':
                chin_offset = [0,6,-22.3]
            chin_mesh.translate(chin_offset, inplace=True)
            chin_mesh.save(self.chin_mesh_file)

       
        return head_mesh, helmet_mesh, chin_mesh if chin_mesh is not None else None