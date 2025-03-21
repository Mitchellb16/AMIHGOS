#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for SegmentationScreen class.

This script creates a test environment to verify the functionality
of the SegmentationScreen class without running the full application.
"""
import os
import sys
import unittest
import numpy as np
import SimpleITK as sitk
import tkinter as tk
from PyQt5 import QtWidgets
from unittest.mock import patch, MagicMock

# Ensure we can find our modules
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the class to test
# Adjust the import based on where you place the optimized class
from amihgosapp.core.segmentation import SegmentationScreen


class MockMeshManipulationWindow:
    """Mock class to replace MeshManipulationWindow for testing."""
    
    def __init__(self, helmet_mesh_file, head_mesh_file, animal_name, helmet_type=None):
        self.helmet_mesh_file = helmet_mesh_file
        self.head_mesh_file = head_mesh_file
        self.animal_name = animal_name
        self.helmet_type = helmet_type
        print(f"Mock MeshManipulationWindow initialized with: {helmet_mesh_file}, {head_mesh_file}, {animal_name}")
        if helmet_type:
            print(f"Helmet type: {helmet_type}")
    
    def run(self):
        print("Mock MeshManipulationWindow running")
        return True


class TestSegmentationScreen(unittest.TestCase):
    """Test cases for SegmentationScreen class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create a test image
        cls.test_image = cls._create_test_image()
        
        # Store the original MeshManipulationWindow class
        cls.original_mesh_window = None
        
        # Create a temporary directory for test outputs
        cls.temp_dir = os.path.join(project_root, 'test_output')
        if not os.path.exists(cls.temp_dir):
            os.makedirs(cls.temp_dir)
        
        # Create head_stls directory if it doesn't exist
        cls.head_stls_dir = os.path.join(project_root, 'head_stls')
        if not os.path.exists(cls.head_stls_dir):
            os.makedirs(cls.head_stls_dir)
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done."""
        # Clean up temporary files if needed
        pass
    
    @staticmethod
    def _create_test_image():
        """
        Create a simple test image with a sphere.
        
        Returns
        -------
        SimpleITK.Image
            A test image for segmentation
        """
        # Create a 3D image (100x100x100)
        size = [100, 100, 100]
        image = sitk.Image(size[0], size[1], size[2], sitk.sitkInt16)
        
        # Set background to -1000 (air in HU)
        image = image - 1000
        
        # Add a sphere for bone (1000 HU)
        for z in range(size[2]):
            for y in range(size[1]):
                for x in range(size[0]):
                    # Distance from center
                    dist1 = np.sqrt((x - 50)**2 + (y - 50)**2 + (z - 50)**2)
                    # Create a sphere
                    if dist1 < 40:
                        # Soft tissue (~0 HU)
                        image[x, y, z] = 0
                    # Add another sphere for bone
                    dist2 = np.sqrt((x - 50)**2 + (y - 50)**2 + (z - 70)**2)
                    if dist2 < 20:
                        # Bone (~1000 HU)
                        image[x, y, z] = 1000
        
        return image
    
    def setUp(self):
        """Set up for each test."""
        # Patch the _setup_ui method to avoid actual UI creation
        self.setup_ui_patch = patch.object(SegmentationScreen, '_setup_ui')
        self.mock_setup_ui = self.setup_ui_patch.start()
        
        # Mock the resource utilities
        self.resource_patch = patch('amihgosapp.core.segmentation.get_image_path')
        self.mock_get_image = self.resource_patch.start()
        self.mock_get_image.return_value = 'tests/mocklogo.png'
        
        # Mock sitk2vtk and vtkutils
        self.sitk_utils_patch = patch('amihgosapp.core.segmentation.sitk_utils')
        self.mock_sitk_utils = self.sitk_utils_patch.start()
        
        self.vtk_utils_patch = patch('amihgosapp.core.segmentation.vtk_utils')
        self.mock_vtk_utils = self.vtk_utils_patch.start()
        
        # Mock MeshManipulationWindow
        import amihgosapp.core.segmentation as seg_module
        self.__class__.original_mesh_window = seg_module.MeshManipulationWindow
        seg_module.MeshManipulationWindow = MockMeshManipulationWindow
        
        # Mock QtWidgets.QApplication
        self.qapp_patch = patch('PyQt5.QtWidgets.QApplication')
        self.mock_qapp = self.qapp_patch.start()
        self.mock_qapp_instance = MagicMock()
        self.mock_qapp.instance.return_value = self.mock_qapp_instance
        
        # Mock sys.exit to prevent test from exiting
        self.sys_exit_patch = patch('sys.exit')
        self.mock_sys_exit = self.sys_exit_patch.start()
        
        # Mock os.listdir for template listing
        self.os_listdir_patch = patch('os.listdir')
        self.mock_listdir = self.os_listdir_patch.start()
        self.mock_listdir.return_value = ['Flat_helmet.STL', 'winged_helmet.stl']
    
    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        self.setup_ui_patch.stop()
        self.resource_patch.stop()
        self.sitk_utils_patch.stop()
        self.vtk_utils_patch.stop()
        self.qapp_patch.stop()
        self.sys_exit_patch.stop()
        self.os_listdir_patch.stop()
        
        # Restore original MeshManipulationWindow
        if self.__class__.original_mesh_window:
            import amihgosapp.core.segmentation as seg_module
            seg_module.MeshManipulationWindow = self.__class__.original_mesh_window
    
    def test_initialization(self):
        """Test that the class initializes properly."""
        # Initialize segmentation screen
        seg_screen = SegmentationScreen(self.test_image, 'TEST_ANIMAL')
        
        # Check key attributes
        self.assertIsNotNone(seg_screen.img)
        self.assertEqual(seg_screen.animal_name, 'TEST_ANIMAL')
        self.assertEqual(seg_screen.output_dir, 'head_stls/TEST_ANIMAL.stl')
        
        # Verify _setup_ui was called
        self.mock_setup_ui.assert_called_once()
    
    def test_segment_to_stl(self):
        """Test the segmentation and mesh creation process."""
        # Initialize segmentation screen
        seg_screen = SegmentationScreen(self.test_image, 'TEST_ANIMAL')
        
        # Mock the _show_helmet_selection method
        with patch.object(seg_screen, '_show_helmet_selection') as mock_show_helmet:
            # Setup mocks for mesh processing
            mock_vtkimg = MagicMock()
            mock_mesh = MagicMock()
            mock_mesh2 = MagicMock()
            mock_mesh_cleaned = MagicMock()
            mock_mesh3 = MagicMock()
            
            self.mock_sitk_utils.sitk2vtk.return_value = mock_vtkimg
            self.mock_vtk_utils.extractSurface.return_value = mock_mesh
            self.mock_vtk_utils.cleanMesh.return_value = mock_mesh2
            self.mock_vtk_utils.removeSmallObjects.return_value = mock_mesh_cleaned
            self.mock_vtk_utils.smoothMesh.return_value = mock_mesh3
            
            # Create a mock root for UI updates
            seg_screen.root = MagicMock()
            
            # Run the segmentation
            seg_screen.segment_to_stl()
            
            # Verify that the segmentation pipeline was called
            self.mock_sitk_utils.sitk2vtk.assert_called_once()
            self.mock_vtk_utils.extractSurface.assert_called_once()
            self.mock_vtk_utils.cleanMesh.assert_called_once()
            self.mock_vtk_utils.removeSmallObjects.assert_called_once()
            self.mock_vtk_utils.smoothMesh.assert_called_once()
            self.mock_vtk_utils.writeMesh.assert_called_once()
            
            # Verify helmet selection was shown
            mock_show_helmet.assert_called_once()
    
    def test_run_mesh_manipulation_window(self):
        """Test launching the mesh manipulation window."""
        # Initialize segmentation screen
        seg_screen = SegmentationScreen(self.test_image, 'TEST_ANIMAL')
        
        # Setup for mesh manipulation
        seg_screen.output_dir = 'head_stls/TEST_ANIMAL.stl'
        seg_screen.root = MagicMock()
        
        # Test with regular helmet
        helmet_var = MagicMock()
        helmet_var.get.return_value = 'Flat_helmet.STL'
        seg_screen.helmet_selection = helmet_var
        
        # Run mesh manipulation
        seg_screen.run_mesh_manipulation_window()
        
        # Verify that the root window was destroyed
        seg_screen.root.destroy.assert_called_once()
        
        # Verify that QApplication was accessed
        self.mock_qapp.instance.assert_called()
        
        # Verify that sys.exit was called
        self.mock_sys_exit.assert_called_once()
        
        # Reset mocks for testing winged helmet
        seg_screen.root.destroy.reset_mock()
        self.mock_sys_exit.reset_mock()
        
        # Test with winged helmet
        helmet_var.get.return_value = 'winged_helmet.stl'
        seg_screen.run_mesh_manipulation_window()
        
        # Verify again that methods were called
        seg_screen.root.destroy.assert_called_once()
        self.mock_sys_exit.assert_called_once()
    
    def test_show_helmet_selection(self):
        """Test showing the helmet selection UI."""
        # Initialize segmentation screen
        seg_screen = SegmentationScreen(self.test_image, 'TEST_ANIMAL')
        
        # Create a mock for the root window
        seg_screen.root = MagicMock()
        
        # Create mocks for the UI elements
        with patch('tkinter.Label', return_value=MagicMock()) as mock_label:
            with patch('tkinter.StringVar', return_value=MagicMock()) as mock_stringvar:
                with patch('tkinter.OptionMenu', return_value=MagicMock()) as mock_option_menu:
                    with patch('tkinter.Button', return_value=MagicMock()) as mock_button:
                        # Call the method
                        seg_screen._show_helmet_selection()
        
        # Verify the UI elements were created
        mock_label.assert_called()
        mock_stringvar.assert_called_once()
        mock_option_menu.assert_called_once()
        mock_button.assert_called_once()


if __name__ == "__main__":
    # Configure unittest to output more detailed information
    unittest.main(verbosity=2)