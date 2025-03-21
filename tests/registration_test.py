#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for RegistrationPointDataAcquisition class.

This script creates a simple test environment to verify the functionality
of the RegistrationPointDataAcquisition class without running the full application.

Written by Mitchell Bishop with Claude AI
"""
import os
import sys
import unittest
import numpy as np
import SimpleITK as sitk
import tkinter as tk
from matplotlib import pyplot as plt
from matplotlib.backend_bases import MouseEvent

# Ensure we can find our modules
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the class to test
# Adjust the import based on where you place the optimized class
from amihgosapp.core.registration_acquisition import RegistrationPointDataAcquisition


class MockVisualization:
    """Mock class to replace visualize_registration for testing."""
    
    def __init__(self, fixed_image, moving_resampled, root=None):
        self.fixed_image = fixed_image
        self.moving_resampled = moving_resampled
        self.root = root
        print("Mock Visualization initialized")
        
        
class MockSegmentationScreen:
    """Mock class to replace SegmentationScreen for testing."""
    
    def __init__(self, img, animal_name):
        self.img = img
        self.animal_name = animal_name
        print(f"Mock SegmentationScreen initialized with animal name: {animal_name}")
    
    def run(self):
        print("Mock SegmentationScreen running")
        
    def run_mesh_manipulation_window(self):
        print("Mock mesh manipulation window running")


class TestRegistrationPointDataAcquisition(unittest.TestCase):
    """Test cases for RegistrationPointDataAcquisition class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create test images
        cls.fixed_image = cls._create_test_image((100, 100, 100), center=(50, 50, 50), radius=30)
        cls.moving_image = cls._create_test_image((100, 100, 100), center=(40, 45, 55), radius=25)
        
        # Create a test transform
        translation = sitk.TranslationTransform(3, (-10, -5, 5))
        cls.test_transform = translation
        
        # Store original imports for restoration later
        cls.original_visualize = None
        cls.original_segmentation = None
        
    @staticmethod
    def _create_test_image(size, center, radius):
        """
        Create a simple test image with a sphere.
        
        Parameters
        ----------
        size : tuple
            Image dimensions (x, y, z)
        center : tuple
            Sphere center coordinates (x, y, z)
        radius : float
            Sphere radius
            
        Returns
        -------
        SimpleITK.Image
            The created test image
        """
        # Create a 3D image
        image = sitk.Image(size[0], size[1], size[2], sitk.sitkFloat32)
        
        # Set background to 100
        image = image + 100
        
        # Create a sphere source
        sphere = sitk.Image(size[0], size[1], size[2], sitk.sitkFloat32)
        for z in range(size[2]):
            for y in range(size[1]):
                for x in range(size[0]):
                    # Distance from center
                    dist = np.sqrt((x - center[0])**2 + (y - center[1])**2 + (z - center[2])**2)
                    if dist < radius:
                        sphere[x, y, z] = 1
        
        # Add the sphere to the image with higher intensity
        image = image + sphere * 900
        
        return image
    
    def setUp(self):
        """Set up for each test."""
        # Create a new Tkinter root for each test
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window
        
        # Create a frame for the registration UI
        self.registration_frame = tk.Frame(self.root)
        
        # Mock the dependencies
        import amihgosapp.core.registration_acquisition as reg_module
        self.__class__.original_visualize = reg_module.visualize_registration
        self.__class__.original_segmentation = reg_module.SegmentationScreen
        
        reg_module.visualize_registration = MockVisualization
        reg_module.SegmentationScreen = MockSegmentationScreen
    
    def tearDown(self):
        """Clean up after each test."""
        # Restore original dependencies
        if self.__class__.original_visualize:
            import amihgosapp.core.registration_acquisition as reg_module
            reg_module.visualize_registration = self.__class__.original_visualize
            reg_module.SegmentationScreen = self.__class__.original_segmentation
        
        # Close all matplotlib figures
        plt.close('all')
        
        # Destroy Tkinter root
        self.root.destroy()
    
    def test_initialization(self):
        """Test that the class initializes properly."""
        # Initialize registration class
        reg_acquisition = RegistrationPointDataAcquisition(
            self.moving_image, 
            self.registration_frame, 
            self.root
        )
        
        # Check key attributes
        self.assertIsNotNone(reg_acquisition.fixed_image)
        self.assertIsNotNone(reg_acquisition.moving_image)
        self.assertIsNotNone(reg_acquisition.fixed_npa)
        self.assertIsNotNone(reg_acquisition.moving_npa)
        self.assertIsNotNone(reg_acquisition.fixed_slider)
        self.assertIsNotNone(reg_acquisition.moving_slider)
        
        # Check that figures were created
        self.assertIsNotNone(reg_acquisition.fixed_fig)
        self.assertIsNotNone(reg_acquisition.moving_fig)
        self.assertIsNotNone(reg_acquisition.fixed_axes)
        self.assertIsNotNone(reg_acquisition.moving_axes)
        
        # Check initial state
        self.assertEqual(len(reg_acquisition.fixed_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.moving_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.click_history), 0)
    
    def test_window_level_calculations(self):
        """Test window/level calculations for display."""
        # Initialize with default window/level
        reg_acquisition = RegistrationPointDataAcquisition(
            self.moving_image, 
            self.registration_frame, 
            self.root
        )
        
        # Test with custom window/level
        custom_fixed_level = [500, 700]
        custom_moving_level = [300, 500]
        
        npa, min_val, max_val = reg_acquisition._get_window_level_numpy_array(
            self.fixed_image, custom_fixed_level
        )
        
        self.assertIsNotNone(npa)
        self.assertEqual(min_val, 700 - 500/2.0)
        self.assertEqual(max_val, 700 + 500/2.0)
    
    def test_point_manipulation(self):
        """Test adding and clearing points."""
        # Initialize registration class
        reg_acquisition = RegistrationPointDataAcquisition(
            self.moving_image, 
            self.registration_frame, 
            self.root
        )
        
        # Mock click in fixed image
        fixed_click_event = type('obj', (object,), {
            'inaxes': reg_acquisition.fixed_axes,
            'xdata': 50,
            'ydata': 50
        })
        reg_acquisition.__call__(fixed_click_event)
        
        # Check that point was added
        self.assertEqual(len(reg_acquisition.fixed_point_indexes), 1)
        self.assertEqual(len(reg_acquisition.click_history), 1)
        
        # Mock click in moving image
        moving_click_event = type('obj', (object,), {
            'inaxes': reg_acquisition.moving_axes,
            'xdata': 40,
            'ydata': 45
        })
        reg_acquisition.__call__(moving_click_event)
        
        # Check that point was added
        self.assertEqual(len(reg_acquisition.moving_point_indexes), 1)
        self.assertEqual(len(reg_acquisition.click_history), 2)
        
        # Test clear last
        reg_acquisition.clear_last()
        self.assertEqual(len(reg_acquisition.moving_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.fixed_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.click_history), 0)
        
        # Add points again
        reg_acquisition.__call__(fixed_click_event)
        reg_acquisition.__call__(moving_click_event)
        
        # Test clear all
        reg_acquisition.clear_all()
        self.assertEqual(len(reg_acquisition.moving_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.fixed_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.click_history), 0)
    
    def test_get_points(self):
        """Test conversion of points to physical coordinates."""
        # Initialize registration class
        reg_acquisition = RegistrationPointDataAcquisition(
            self.moving_image, 
            self.registration_frame, 
            self.root
        )
        
        # Add points
        reg_acquisition.fixed_point_indexes.append((50, 50, 50))
        reg_acquisition.moving_point_indexes.append((40, 45, 55))
        
        # Get points in physical space
        fixed_points, moving_points = reg_acquisition.get_points()
        
        # Check that we got the right number of points
        self.assertEqual(len(fixed_points), 1)
        self.assertEqual(len(moving_points), 1)
        
        # Each point should have 3 coordinates
        self.assertEqual(len(fixed_points[0]), 3)
        self.assertEqual(len(moving_points[0]), 3)
        
        # Test with mismatched points (should raise an exception)
        reg_acquisition.fixed_point_indexes.append((60, 60, 60))
        with self.assertRaises(Exception):
            reg_acquisition.get_points()
    
    def test_registration(self):
        """Test the registration process."""
        # Initialize registration class
        reg_acquisition = RegistrationPointDataAcquisition(
            self.moving_image, 
            self.registration_frame, 
            self.root
        )
        
        # Add corresponding points
        reg_acquisition.fixed_point_indexes.append((30, 40, 50))
        reg_acquisition.fixed_point_indexes.append((70, 40, 50))
        reg_acquisition.fixed_point_indexes.append((50, 30, 50))
        reg_acquisition.fixed_point_indexes.append((50, 50, 30))
        
        reg_acquisition.moving_point_indexes.append((20, 35, 55))
        reg_acquisition.moving_point_indexes.append((60, 35, 55))
        reg_acquisition.moving_point_indexes.append((40, 25, 55))
        reg_acquisition.moving_point_indexes.append((40, 45, 35))
        
        # Mock the popup creation to avoid UI interaction
        original_show_popup = reg_acquisition._show_success_popup
        reg_acquisition._show_success_popup = lambda: None
        
        # Run registration
        try:
            reg_acquisition.save_points()
            
            # Check that transform was created
            self.assertIsNotNone(reg_acquisition.init_transform)
            self.assertIsNotNone(reg_acquisition.final_transform)
            self.assertIsNotNone(reg_acquisition.moving_resampled)
            
        finally:
            # Restore original method
            reg_acquisition._show_success_popup = original_show_popup
    
    def test_registration_with_known_transform(self):
        """Test registration with a known transformation."""
        # Initialize registration class with known transform
        reg_acquisition = RegistrationPointDataAcquisition(
            self.moving_image, 
            self.registration_frame, 
            self.root,
            known_transformation=self.test_transform
        )
        
        # Mock click in fixed image (with known transform, this should add points to both images)
        fixed_click_event = type('obj', (object,), {
            'inaxes': reg_acquisition.fixed_axes,
            'xdata': 50,
            'ydata': 50
        })
        reg_acquisition.__call__(fixed_click_event)
        
        # Check that points were added to both images
        self.assertEqual(len(reg_acquisition.fixed_point_indexes), 1)
        self.assertEqual(len(reg_acquisition.moving_point_indexes), 1)
        self.assertEqual(len(reg_acquisition.click_history), 2)
        
        # Test clear last with known transform
        reg_acquisition.clear_last()
        self.assertEqual(len(reg_acquisition.moving_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.fixed_point_indexes), 0)
        self.assertEqual(len(reg_acquisition.click_history), 0)


if __name__ == "__main__":
    # Configure unittest to output more detailed information
    unittest.main(verbosity=2)