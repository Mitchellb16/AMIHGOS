#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HomeWindow module - Main entry point for the AMIHGOS application
Mitchell Bishop, developed with help from Claude AI
"""
import os
import sys
import webbrowser
import SimpleITK as sitk
from tkinter import Tk, Frame, Label, Button, StringVar, PhotoImage, DISABLED, OptionMenu, mainloop
from tkinter import filedialog

from PyQt5 import QtWidgets

# Import from new locations when available
from amihgosapp.utils.ImageLabel import ImageLabel
from amihgosapp.utils.resource_utils import get_image_path, get_template_path

# Import from old locations for modules not yet migrated
from utils.mesh_manipulationv2 import MeshManipulationWindow 
from utils.ROIDataAquisition import ROIDataAquisition

class HomeWindow:
    """
    Main application window for AMIHGOS featuring:
    - File selection for NIFTI/DICOM images
    - STL file loading for helmet subtraction
    - ROI selection workflow
    - Links to documentation
    """
    def __init__(self):
        self.setup_root_window()
        self.create_frames()
        self.setup_ui_elements()
        self.setup_file_tracking()
        
    def setup_root_window(self):
        """Initialize the main Tkinter window with appropriate settings"""
        self.root = Tk()
        self.root.title('AMIHGOS')
        
    def create_frames(self):
        """Create the main application frames for each workflow step"""
        self.intro_frame = Frame(self.root)
        self.intro_frame.pack()
        
        # Create but don't pack these frames until needed
        self.ROI_frame = Frame(self.root)
        self.registration_frame = Frame(self.root)
        self.final_frame = Frame(self.root)
        
        self.frames_list = [
            self.intro_frame, 
            self.ROI_frame, 
            self.registration_frame, 
            self.final_frame
        ]
        
    def setup_ui_elements(self):
        """Set up all UI elements for the home screen"""
        self.setup_logo()
        self.setup_helmet_preview()
        self.setup_file_controls()
        self.setup_action_buttons()
        self.setup_helmet_selection()
        
    def setup_logo(self):
        """Add the application logo to the intro frame"""
        self.logo = PhotoImage(file=get_image_path('logo3.png'))
        self.logo = self.logo.subsample(7,7)
        self.logo_label = Label(master=self.intro_frame, image=self.logo)
        self.logo_label.image = self.logo
        self.logo_label.grid(column=1, row=0, rowspan=2)
        
    def setup_helmet_preview(self):
        """Add the animated helmet preview gif"""
        helm_gif = ImageLabel(self.intro_frame)
        helm_gif.grid(column=1, row=4, rowspan=2, sticky='nsew')
        helm_gif.load(get_image_path('helm_gif_earbars.gif'))
        
    def setup_file_controls(self):
        """Set up file selection buttons and labels"""
        # CT/NIFTI file selection
        self.load_file_button = Button(
            self.intro_frame, 
            text='Load file', 
            command=self.browse_nifti_files
        )
        self.load_file_button.grid(column=1, row=1)
        
        self.file_label = Label(self.intro_frame, text='No file chosen')
        self.file_label.grid(column=1, row=1, sticky='s')
        
        # STL file selection
        self.load_stl_button = Button(
            self.intro_frame, 
            text='Subtract .STL', 
            command=self.browse_stl_files
        )
        self.load_stl_button.grid(column=1, row=7)
        
        self.stl_file_label = Label(self.intro_frame, text='No file chosen')
        self.stl_file_label.grid(column=1, row=9, sticky='s')
        
    def setup_action_buttons(self):
        """Set up action buttons including github link and ROI selection"""
        # Github button
        self.github_button = Button(
            self.intro_frame, 
            text='Github', 
            command=self.open_github
        )
        self.github_button.grid(column=1, row=6)
        
        # ROI selection button (initially disabled)
        self.ROI_button = Button(
            master=self.intro_frame, 
            state=DISABLED, 
            text='Next: ROI Selection',
            command=self.start_roi_selection
        )
        self.ROI_button.grid(column=1, row=1, sticky='e')
        
    def setup_helmet_selection(self):
        """Set up helmet template selection dropdown"""
        # Get available helmet templates
        template_dir = 'templates/'  # Consider moving to resource_utils
        helmet_options = os.listdir(template_dir)
        
        # Create selection dropdown
        self.helmet_selection = StringVar()
        self.helmet_selection.set('Flat_helmet.STL')
        
        self.dropdown = OptionMenu(
            self.intro_frame, 
            self.helmet_selection, 
            *helmet_options
        )
        self.dropdown.grid(column=1, row=8)
        
    def setup_file_tracking(self):
        """Set up variables to track file selection"""
        # Track NIFTI file selection
        self.filevar = StringVar()
        self.filevar.trace_add('write', self.validate_nifti_selection)
        
        # Track STL file selection
        self.stl_filevar = StringVar()
        self.stl_filevar.trace_add('write', self.handle_stl_selection)
        
        # Initialize file paths
        self.moving_image = None
        self.stl_file = None
        
    def browse_nifti_files(self):
        """Open file dialog for selecting NIFTI/DICOM files"""
        filename = filedialog.askopenfilename(
            initialdir='./nifti_files/Example',
            filetypes=[
                ("DICOM", ".dcm"),
                ("NIFTI", ".nii"),
                ("NIFTI compressed", ".nii.gz"),
            ]
        )

        if not filename:
            print("No file selected.")
            return
            
        print('Loaded file:', filename)
        self.filevar.set(filename)
        self.moving_image = sitk.DICOMOrient(sitk.ReadImage(filename), 'LPS')
    
    def browse_stl_files(self):
        """Open file dialog for selecting STL files"""
        stl_filename = filedialog.askopenfilename(
            initialdir='./head_stls/',
            filetypes=[("STL model", ".stl")]
        )
        
        if not stl_filename:
            print("No STL file selected.")
            return
        
        self.stl_file = stl_filename
        self.stl_filevar.set(stl_filename)
    
    def validate_nifti_selection(self, var, index, mode):
        """
        Validate NIFTI file selection and update UI accordingly
        """
        if self.filevar.get():
            self.ROI_button.config(state='normal')
            # Show truncated filename
            self.file_label['text'] = '...' + self.filevar.get()[-12:]
        else:
            self.ROI_button.config(state='disabled')
            print('No file selected')
    
    def handle_stl_selection(self, var, index, mode):
        """Handle STL file selection and launch mesh manipulation"""
        # Only proceed if an STL file was selected
        if not self.stl_filevar.get():
            return
            
        # Close the current window
        self.root.destroy()
        
        # Prepare file paths
        helmet_template = get_template_path(self.helmet_selection.get())
        head_mesh_file = self.stl_file
        
        # Get animal name from file string
        animal_name = os.path.splitext(os.path.basename(self.stl_file))[0]
        
        # Set up QT application
        if not QtWidgets.QApplication.instance():
            app = QtWidgets.QApplication(sys.argv)
        else:
            app = QtWidgets.QApplication.instance()
        app.setQuitOnLastWindowClosed(True)
        
        # Launch mesh manipulation with appropriate settings
        if 'winged' in helmet_template:
            window = MeshManipulationWindow(
                helmet_template, 
                head_mesh_file, 
                animal_name, 
                helmet_type='PET'
            )
        else:
            window = MeshManipulationWindow(
                helmet_template, 
                head_mesh_file, 
                animal_name
            )
            
        window.run()
        sys.exit(app.exec_())
        
    def start_roi_selection(self):
        """Start the ROI selection workflow"""
        self.intro_frame.pack_forget()
        ROIDataAquisition(
            self.moving_image, 
            self.ROI_frame, 
            self.root, 
            self.frames_list
        )
            
    def open_github(self):
        """Open the GitHub repository in a web browser"""
        webbrowser.open('https://github.com/Mitchellb16/AMIHGOS', new=1)
    
    def run(self):
        """Start the Tkinter main loop"""
        mainloop()