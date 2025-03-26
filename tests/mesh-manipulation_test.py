#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for MeshManipulationWindow class.

This script creates a test environment to verify the functionality
of the MeshManipulationWindow class without running the full application.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure we can find our modules
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock PyVista before importing the class
sys.modules['pyvista'] = MagicMock()
sys.modules['pyvistaqt'] = MagicMock()
sys.modules['pymeshfix'] = MagicMock()

# Now we can import the class to test
from amihgosapp.core.mesh_manipulation import MeshManipulationWindow, ManipulationButton, TranslationButton, RotationButton


class TestMeshManipulationWindow(unittest.TestCase):
    """Test cases for MeshManipulationWindow class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create test directories if they don't exist
        cls.head_stls_dir = os.path.join(project_root, 'head_stls')
        cls.helmets_dir = os.path.join(project_root, 'helmets')
        cls.templates_dir = os.path.join(project_root, 'templates')
        
        for directory in [cls.head_stls_dir, cls.helmets_dir, cls.templates_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
        # Create dummy STL files if they don't exist
        cls.test_head_file = os.path.join(cls.head_stls_dir, 'TEST_HEAD.stl')
        cls.test_helmet_file = os.path.join(cls.templates_dir, 'TEST_HELMET.stl')
        
        for test_file in [cls.test_head_file, cls.test_helmet_file]:
            if not os.path.exists(test_file):
                with open(test_file, 'w') as f:
                    f.write("dummy stl content")
    
    def setUp(self):
        """Set up for each test."""
        # Mock PyQt
        self.qapp_patch = patch('PyQt5.QtWidgets.QApplication')
        self.mock_qapp = self.qapp_patch.start()
        self.mock_qapp_instance = MagicMock()
        self.mock_qapp.instance.return_value = self.mock_qapp_instance
        
        # Mock PyVista read
        self.pv_read_patch = patch('pyvista.read')
        self.mock_pv_read = self.pv_read_patch.start()
        
        # Mock mesh objects
        self.mock_helmet_mesh = self._create_mock_mesh()
        self.mock_head_mesh = self._create_mock_mesh()
        self.mock_chin_mesh = self._create_mock_mesh()
        
        # Set up the mock read function to return our mock meshes
        self.mock_pv_read.side_effect = [
            self.mock_helmet_mesh,  # First call for helmet mesh
            self.mock_head_mesh,    # Second call for head mesh
            self.mock_chin_mesh     # Third call for chin mesh
        ]
        
        # Mock Text3D
        self.pv_text_patch = patch('pyvista.Text3D')
        self.mock_text = self.pv_text_patch.start()
        mock_text_instance = self._create_mock_mesh()
        self.mock_text.return_value = mock_text_instance
        
        # Mock resource utilities
        self.resource_patch = patch('amihgosapp.core.mesh_manipulation.get_template_path')
        self.mock_get_template = self.resource_patch.start()
        self.mock_get_template.return_value = self.test_helmet_file
        
        # Mock plotter
        self.plotter_patch = patch('pyvistaqt.BackgroundPlotter')
        self.mock_plotter_class = self.plotter_patch.start()
        self.mock_plotter = MagicMock()
        self.mock_plotter_class.return_value = self.mock_plotter
        
        # Mock QWidget and its methods
        self.qwidget_patch = patch('PyQt5.QtWidgets.QWidget.__init__')
        self.mock_qwidget_init = self.qwidget_patch.start()
        self.mock_qwidget_init.return_value = None
        
        # Mock QVBoxLayout
        self.layout_patch = patch('PyQt5.QtWidgets.QVBoxLayout')
        self.mock_layout = self.layout_patch.start()
        
        # Mock all PyQt widgets
        self.widgets_to_mock = [
            'QPushButton', 'QFrame', 'QHBoxLayout', 'QLabel', 
            'QSlider', 'QCheckBox'
        ]
        self.widget_patches = {}
        self.mock_widgets = {}
        
        for widget in self.widgets_to_mock:
            patch_path = f'PyQt5.QtWidgets.{widget}'
            self.widget_patches[widget] = patch(patch_path)
            self.mock_widgets[widget] = self.widget_patches[widget].start()
            self.mock_widgets[widget].return_value = MagicMock()
    
    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        self.qapp_patch.stop()
        self.pv_read_patch.stop()
        self.pv_text_patch.stop()
        self.resource_patch.stop()
        self.plotter_patch.stop()
        self.qwidget_patch.stop()
        self.layout_patch.stop()
        
        for widget in self.widgets_to_mock:
            self.widget_patches[widget].stop()
    
    def _create_mock_mesh(self):
        """Create a mock PyVista mesh with common methods."""
        mesh = MagicMock()
        
        # Setup common mesh properties
        mesh.center = [0, 0, 0]
        mesh.bounds = [-10, 10, -10, 10, -10, 10]
        mesh.is_manifold = True
        
        # Setup mesh methods
        mesh.triangulate.return_value = mesh
        mesh.clean.return_value = mesh
        mesh.scale.return_value = mesh
        mesh.rotate_x.return_value = mesh
        mesh.rotate_y.return_value = mesh
        mesh.rotate_z.return_value = mesh
        mesh.copy.return_value = mesh
        mesh.translate.return_value = mesh
        mesh.boolean_difference.return_value = mesh
        mesh.extract_largest.return_value = mesh
        mesh.clip_box.return_value = mesh
        mesh.extract_geometry.return_value = mesh
        mesh.extract_surface.return_value = mesh
        mesh.smooth.return_value = mesh
        mesh.smooth_taubin.return_value = mesh
        mesh.fill_holes.return_value = mesh
        
        # Setup operator overloading for mesh addition
        mesh.__add__.return_value = mesh
        
        return mesh
    
    def test_initialization(self):
        """Test that the class initializes properly."""
        # Initialize the window
        window = MeshManipulationWindow(
            self.test_helmet_file, 
            self.test_head_file, 
            animal_name='TEST_ANIMAL'
        )
        
        # Check that meshes were loaded
        self.mock_pv_read.assert_called()
        
        # Check key attributes
        self.assertEqual(window.animal_name, 'TEST_ANIMAL')
        self.assertEqual(window.helmet_mesh_file, self.test_helmet_file)
        self.assertEqual(window.head_mesh_file, self.test_head_file)
        self.assertEqual(window.scaling_factor, 1.0)
        
        # Check UI initialization
        self.mock_layout.assert_called_once()
    
    def test_winged_helmet_initialization(self):
        """Test initialization with winged helmet type."""
        # Initialize with winged helmet
        window = MeshManipulationWindow(
            self.test_helmet_file, 
            self.test_head_file, 
            animal_name='TEST_ANIMAL',
            helmet_type='PET'
        )
        
        # Verify helmet type is set
        self.assertEqual(window.helmet_type, 'PET')
        
        # Verify correct chin piece is selected
        self.mock_get_template.assert_called()
    
    def test_manipulation_buttons(self):
        """Test manipulation button classes."""
        # Create a mock window and layout
        mock_window = MagicMock()
        mock_layout = MagicMock()
        
        # Create a TranslationButton
        trans_button = TranslationButton('LR', mock_window, mock_layout)
        
        # Test decrease/increase methods
        trans_button.decrease_value()
        self.assertEqual(trans_button.value, -0.5)
        
        trans_button.increase_value()
        self.assertEqual(trans_button.value, 0)
        
        # Create a RotationButton
        rot_button = RotationButton('X', mock_window, mock_layout)
        
        # Test decrease/increase methods
        rot_button.decrease_value()
        self.assertEqual(rot_button.value, -2)
        
        rot_button.increase_value()
        self.assertEqual(rot_button.value, 0)
    
    def test_create_pvplotter(self):
        """Test plotter creation."""
        # Initialize the window
        window = MeshManipulationWindow(
            self.test_helmet_file, 
            self.test_head_file
        )
        
        # Run create_pvplotter method
        window.create_pvplotter()
        
        # Verify plotter was created and meshes were added
        self.mock_plotter_class.assert_called_once()
        self.mock_plotter.add_mesh.assert_called()
        self.mock_plotter.show_bounds.assert_called_once()
        self.mock_plotter.show.assert_called_once()
    
    def test_send_for_subtraction(self):
        """Test the boolean subtraction process."""
        # Initialize the window
        window = MeshManipulationWindow(
            self.test_helmet_file, 
            self.test_head_file
        )
        
        # Set up the plotter
        window.plotter = self.mock_plotter
        
        # Mock pymeshfix
        with patch('pymeshfix.MeshFix') as mock_meshfix:
            mock_meshfix_instance = MagicMock()
            mock_meshfix_instance.mesh = self.mock_head_mesh
            mock_meshfix.return_value = mock_meshfix_instance
            
            # Run the subtraction
            window.send_for_subtraction()
        
        # Verify the head mesh was saved
        self.mock_head_mesh.save.assert_called()
        
        # Verify boolean operation was performed
        self.mock_helmet_mesh.boolean_difference.assert_called_with(self.mock_head_mesh)
        
        # Verify save button was enabled
        self.assertFalse(window.save_button.isDisabled())
    
    def test_save_mesh(self):
        """Test saving the final mesh."""
        # Initialize the window
        window = MeshManipulationWindow(
            self.test_helmet_file, 
            self.test_head_file,
            animal_name='TEST_ANIMAL'
        )
        
        # Set up a mock final mesh
        window.final_mesh = self.mock_helmet_mesh
        
        # Set up translations for filename generation
        window.DV_translation = MagicMock()
        window.DV_translation.value = 5
        
        # Run save_mesh
        window.save_mesh()
        
        # Verify mesh was saved
        self.mock_helmet_mesh.extract_geometry.assert_called()
        self.mock_helmet_mesh.extract_geometry().save.assert_called()
        
        # Test with chin piece enabled
        window.chin_subtract_bool = True
        window.chin_bool_mesh = self.mock_chin_mesh
        
        # Run save_mesh again
        window.save_mesh()
        
        # Verify both meshes were saved
        self.mock_chin_mesh.extract_geometry.assert_called()
        self.mock_chin_mesh.extract_geometry().save.assert_called()
    
    def test_update_plotter(self):
        """Test the plotter update process."""
        # Initialize the window
        window = MeshManipulationWindow(
            self.test_helmet_file, 
            self.test_head_file
        )
        
        # Create mock plotter and actor
        window.plotter = self.mock_plotter
        window.head_actor = MagicMock()
        
        # Set up manipulation values
        window.LR_translation = MagicMock(value=1.0)
        window.PA_translation = MagicMock(value=2.0)
        window.DV_translation = MagicMock(value=3.0)
        window.rotation_button_X = MagicMock(value=10)
        window.rotation_button_Y = MagicMock(value=20)
        window.rotation_button_Z = MagicMock(value=30)
        window.smoothing_slider = MagicMock()
        window.smoothing_slider.value.return_value = 50
        
        # Run update_plotter
        window.update_plotter()
        
        # Verify actor was removed and added
        self.mock_plotter.remove_actor.assert_called_with(window.head_actor, render=False)
        self.mock_plotter.add_mesh.assert_called()
        self.mock_plotter.update.assert_called_once()
        
        # Test with final_plot=True
        window.final_mesh = self.mock_helmet_mesh
        window.update_plotter(final_plot=True)
        
        # Verify plotter was cleared
        self.mock_plotter.clear.assert_called_once()


if __name__ == "__main__":
    # Configure unittest to output more detailed information
    unittest.main(verbosity=2)