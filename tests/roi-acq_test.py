#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 21 11:31:38 2025

@author: mitchell
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for ROIDataAcquisition class.

This script creates a simple test environment to verify the functionality
of the ROIDataAcquisition class without running the full application.
"""
import os
import sys
import unittest
import numpy as np
import SimpleITK as sitk
import tkinter as tk
from matplotlib import pyplot as plt

# Ensure we can find our modules
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the ROIDataAcquisition class
# Adjust the import based on where you place the optimized class
from amihgosapp.core.roi_acquisition import ROIDataAcquisition

class MockRegistrationPointDataAcquisition:
    """
    Mock class to replace RegistrationPointDataAcquisition for testing.
    """
    def __init__(self, image, frame, root, fixed_window_level=None, moving_window_level=None):
        self.image = image
        self.frame = frame
        self.root = root
        self.fixed_window_level = fixed_window_level
        self.moving_window_level = moving_window_level
        print("MockRegistrationPointDataAcquisition initialized")
        print(f"Image shape: {image.GetSize()}")

class TestROIDataAcquisition(unittest.TestCase):
    """Test cases for ROIDataAcquisition class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create a test image
        cls.test_image = cls._create_test_image()
        
        # Store the original registration class
        cls.original_registration_class = None
        
    @staticmethod
    def _create_test_image():
        """Create a simple test image."""
        # Create a 3D image with a simple pattern
        size = [100, 100, 100]
        image = sitk.Image(size[0], size[1], size[2], sitk.sitkInt16)
        
        # Fill with a sphere pattern
        for z in range(size[2]):
            for y in range(size[1]):
                for x in range(size[0]):
                    # Distance from center
                    dx = x - size[0]//2
                    dy = y - size[1]//2
                    dz = z - size[2]//2
                    distance = np.sqrt(dx*dx + dy*dy + dz*dz)
                    
                    # Set value based on distance (sphere pattern)
                    if distance < 30:
                        image[x, y, z] = 1000
                    else:
                        image[x, y, z] = 100
        
        return image
    
    def setUp(self):
        """Set up for each test."""
        # Create a new Tkinter root for each test
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window
        
        # Create frames
        self.roi_frame = tk.Frame(self.root)
        self.registration_frame = tk.Frame(self.root)
        self.final_frame = tk.Frame(self.root)
        
        self.frames_list = [None, self.roi_frame, self.registration_frame, self.final_frame]
        
        # Replace RegistrationPointDataAcquisition with mock
        import amihgosapp.core.roi_acquisition as roi_module
        self.__class__.original_registration_class = roi_module.RegistrationPointDataAquisition
        roi_module.RegistrationPointDataAquisition = MockRegistrationPointDataAcquisition
    
    def tearDown(self):
        """Clean up after each test."""
        # Restore original RegistrationPointDataAcquisition
        if self.__class__.original_registration_class:
            import amihgosapp.core.roi_acquisition as roi_module
            roi_module.RegistrationPointDataAquisition = self.__class__.original_registration_class
        
        # Close all matplotlib figures
        plt.close('all')
        
        # Destroy Tkinter root
        self.root.destroy()
    
    def test_initialization(self):
        """Test that the ROIDataAcquisition class initializes properly."""
        # Initialize ROIDataAcquisition
        roi_acquisition = ROIDataAcquisition(
            self.test_image, 
            self.roi_frame, 
            self.root, 
            self.frames_list
        )
        
        # Check that key attributes are set
        self.assertIsNotNone(roi_acquisition.image)
        self.assertIsNotNone(roi_acquisition.npa)
        self.assertIsNotNone(roi_acquisition.sliders)
        self.assertEqual(len(roi_acquisition.sliders), 2)
        self.assertEqual(len(roi_acquisition.rois), 0)
        
        # These tests will fail if matplotlib figures aren't created properly
        self.assertIsNotNone(roi_acquisition.back_fig)
        self.assertIsNotNone(roi_acquisition.front_fig)
        self.assertIsNotNone(roi_acquisition.middle_fig)
    
    def test_roi_manipulation(self):
        """Test ROI manipulation methods."""
        # Initialize ROIDataAcquisition
        roi_acquisition = ROIDataAcquisition(
            self.test_image, 
            self.roi_frame, 
            self.root, 
            self.frames_list
        )
        
        # Add a test ROI
        test_roi = [((10, 20), (30, 40), (50, 60))]
        roi_acquisition.add_roi_data(test_roi)
        
        # Check that ROI was added
        self.assertEqual(len(roi_acquisition.rois), 1)
        
        # Get ROIs
        rois = roi_acquisition.get_rois()
        self.assertEqual(len(rois), 1)
        self.assertEqual(rois[0][0], (10, 20))
        self.assertEqual(rois[0][1], (30, 40))
        self.assertEqual(rois[0][2], (50, 60))
        
        # Clear ROIs
        roi_acquisition._clear_all_data()
        self.assertEqual(len(roi_acquisition.rois), 0)
    
    def test_roi_validation(self):
        """Test ROI validation."""
        # Initialize ROIDataAcquisition
        roi_acquisition = ROIDataAcquisition(
            self.test_image, 
            self.roi_frame, 
            self.root, 
            self.frames_list
        )
        
        # Valid ROI
        valid_roi = [((10, 20), (30, 40), (50, 60))]
        roi_acquisition._validate_rois(valid_roi)  # Should not raise an exception
        
        # Invalid ROI - min > max
        invalid_roi = [((20, 10), (30, 40), (50, 60))]
        with self.assertRaises(ValueError):
            roi_acquisition._validate_rois(invalid_roi)
        
        # Invalid ROI - out of bounds
        out_of_bounds_roi = [((10, 20), (30, 40), (50, 200))]
        with self.assertRaises(ValueError):
            roi_acquisition._validate_rois(out_of_bounds_roi)
    
    def test_crop_moving(self):
        """Test image cropping functionality."""
        # Initialize ROIDataAcquisition
        roi_acquisition = ROIDataAcquisition(
            self.test_image, 
            self.roi_frame, 
            self.root, 
            self.frames_list
        )
        
        # Create a rectangular ROI selection programmatically
        roi_acquisition.roi_selector.extents = (10, 20, 30, 40)
        roi_acquisition.roi_selector.set_visible(True)
        
        # Add a test ROI directly
        test_roi = [((10, 20), (30, 40), (50, 60))]
        roi_acquisition.add_roi_data(test_roi)
        
        # Mock the add_roi method to use our test ROI
        original_add_roi = roi_acquisition.add_roi
        roi_acquisition.add_roi = lambda: None
        
        # Call crop_moving
        roi_acquisition.crop_moving()
        
        # Check that the image was cropped
        cropped_size = roi_acquisition.image.GetSize()
        self.assertEqual(cropped_size[0], 11)  # 20 - 10 + 1
        self.assertEqual(cropped_size[1], 11)  # 40 - 30 + 1
        self.assertEqual(cropped_size[2], 11)  # 60 - 50 + 1
        
        # Restore original method
        roi_acquisition.add_roi = original_add_roi
        
        # Close the popup if it exists
        if hasattr(roi_acquisition, 'popup') and roi_acquisition.popup.winfo_exists():
            roi_acquisition.popup.destroy()
    
    def test_window_level_calculation(self):
        """Test window level calculation."""
        # Initialize ROIDataAcquisition
        roi_acquisition = ROIDataAcquisition(
            self.test_image, 
            self.roi_frame, 
            self.root, 
            self.frames_list
        )
        
        # Test with default window level
        npa, min_val, max_val = roi_acquisition._get_window_level_numpy_array(self.test_image, None)
        self.assertIsNotNone(npa)
        self.assertIsNotNone(min_val)
        self.assertIsNotNone(max_val)
        
        # Test with custom window level
        custom_window_level = [500, 700]
        npa, min_val, max_val = roi_acquisition._get_window_level_numpy_array(self.test_image, custom_window_level)
        self.assertIsNotNone(npa)
        self.assertEqual(min_val, 700 - 500/2.0)
        self.assertEqual(max_val, 700 + 500/2.0)

if __name__ == "__main__":
    # Configure unittest to output more detailed information
    unittest.main(verbosity=2)