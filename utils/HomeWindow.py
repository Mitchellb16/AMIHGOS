#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 13 15:06:21 2023

@author: mitchell
"""
import SimpleITK as sitk
import webbrowser
from .ImageLabel import ImageLabel
from tkinter import *
from tkinter import filedialog
from utils.mesh_manipulationv2 import MeshManipulationWindow 
import pyvista as pv
import sys
from PyQt5 import QtWidgets
from .sitk2vtk import *
from .vtkutils import *
from utils.ROIDataAquisition import ROIDataAquisition
  

class HomeWindow(object):
    """
    Instantiates home window containing buttons for .nii file browser, github link,
    and next step ROI selection.
    """
    def __init__(self):
        # make main window that is 800x600 px     
        self.root = Tk()
# =============================================================================
#         self.root.resizable(True, True)
# =============================================================================
    
# =============================================================================
#         self.root.geometry('550x700')
# =============================================================================
        self.root.title('AMIHGOS')
    
        
        # make frames for each step
        # wait to pack them until the step is reached
        self.intro_frame = Frame(self.root)
        self.intro_frame.pack()
        self.ROI_frame = Frame(self.root)
        self.registration_frame = Frame(self.root)
        self.final_frame = Frame(self.root)
        
        self.frames_list = [self.intro_frame, self.ROI_frame, 
                            self.registration_frame, self.final_frame]
        
        # Add logo image
        self.logo = PhotoImage(file='images/logo3.png')
        self.logo = self.logo.subsample(7,7)
        self.logo_label = Label(master=self.intro_frame, image = self.logo)
        self.logo_label.image = self.logo
        self.logo_label.grid(column = 1, row = 0, rowspan=2)
        
        # add gif of example helmet
        helm_gif = ImageLabel(self.intro_frame)
        helm_gif.grid(column=1, row=4, rowspan=2, sticky = 'nsew')
        helm_gif.load('images/helm_gif_earbars.gif')
        
        # button for selecting CT image directory
        self.load_file_button = Button(self.intro_frame, text='Load file', 
                                     command=self.browseFiles)
        self.load_file_button.grid(column=1, row=1)
        self.file_label = Label(self.intro_frame, text = 'No file chosen')
        self.file_label.grid(column = 1, row = 1, sticky = 's')
        # button for ROI selection, also unpacks the intro frame
        # also add a variable to track whether user has opened a file
        self.filevar = StringVar()
        self.filevar.trace_add('write', self.validate)
        
        # buttons for about info, youtube, and github links 
# =============================================================================
#         self.about_button = Button(self.intro_frame, text = 'About')
#         self.about_button.grid(column = 1, row = 2)
# =============================================================================
# =============================================================================
#         self.tutorial_button = Button(self.intro_frame, text = 'YouTube Tutorial')
#         self.tutorial_button.grid(column = 1, row = 3)
# =============================================================================
        self.github_button = Button(self.intro_frame, text = 'Github', command = self.open_github)
        self.github_button.grid(column = 1, row = 6)
        
        # button for selecting STL image directory
        self.load_stl_button = Button(self.intro_frame, text='Subtract .STL', 
                                     command=lambda:self.browseFiles(filetype='.stl'))
        self.load_stl_button.grid(column=1, row=7)
        
        # track change in stl file variable
        self.stl_filevar = StringVar()
        self.stl_filevar.trace_add('write', self.run_mesh_manipulation_window)
        
        self.stl_file_label = Label(self.intro_frame, text = 'No file chosen')
        self.stl_file_label.grid(column = 1, row = 9, sticky = 's')
        
        # define helmet options for dropdown
        helmet_options = ['templates/Flat_helmet.STL', 'templates/winged_helmet.stl']
        
        # default is flat helmet
        self.helmet_selection = StringVar()
        self.helmet_selection.set('templates/Flat_helmet.STL')
        
        self.dropdown = OptionMenu(self.intro_frame, self.helmet_selection, *helmet_options)
        self.dropdown.grid(column = 1, row = 8)
        
        # ROI button launches ROI class, unpacks the home frame, and resizes window
        self.ROI_button = Button(master = self.intro_frame, state=DISABLED, 
                            command = lambda:[self.intro_frame.pack_forget(), 
                                              ROIDataAquisition(self.moving_image, 
                                                                self.ROI_frame, 
                                                                self.root, 
                                                                self.frames_list)], 
                                text = 'Next: ROI Selection')
            
        self.ROI_button.grid(column=1, row=1, sticky='e')
        
    def run(self):
        # Start the Tkinter main loop
        mainloop()
    
    # file explorer window
    def browseFiles(self, filetype = '.nii'):
        if filetype == '.nii':
            FILENAME = filedialog.askopenfilename(initialdir = './nifti_files/',
                                                  filetypes=[
                            ("image", ".dcm"),
                            ("image", ".nii"),
                            ("image", ".nii.gz"),
                        ])
            print('loaded file:', FILENAME)
            self.filevar.set(FILENAME)
            self.moving_image = sitk.DICOMOrient(sitk.ReadImage(FILENAME), 'LPS')
        
        elif filetype == '.stl':
            self.stl_file = filedialog.askopenfilename(initialdir = './head_stls/',
                                                  filetypes=[
                            ("model", ".stl"),
                        ])
            self.stl_filevar.set(str(self.stl_file))

    # var, index, and mode parameters need to be fed because of the stringvar trace        
    def run_mesh_manipulation_window(self, var, index, mode):
        #close home window
        self.root.destroy()
        
        # load files
        helmet_mesh_file = self.helmet_selection.get()
        helmet_mesh = pv.read(helmet_mesh_file).triangulate(inplace = True)
        head_mesh = pv.read(self.stl_file)
        
        # run mesh manipulation window
        # setting up Qt application stuff
        if not QtWidgets.QApplication.instance():
            app = QtWidgets.QApplication(sys.argv)
        else:
            app = QtWidgets.QApplication.instance()
        app.setQuitOnLastWindowClosed(True)
        
        # get animal name from file string
        animal_name = self.stl_file.split('/')[-1][:-4]
        if 'winged' in helmet_mesh_file:
            window = MeshManipulationWindow(helmet_mesh, head_mesh, 
                                            animal_name, helmet_type = 'PET')
            window.run()
            sys.exit(app.exec_())
        else:
            window = MeshManipulationWindow(helmet_mesh, head_mesh, 
                                            animal_name)
            window.run()
            sys.exit(app.exec_())
        
    def open_github(self):
        webbrowser.open('https://github.com/Mitchellb16/AMIHGOS', new = 1)
    
    def validate(self, var, index, mode):
        """
        Validates existence of directory selected by user
        """
        if self.filevar.get():
            self.ROI_button.config(state='normal')
            self.file_label['text'] = '...' + self.filevar.get()[-12:]
            
        else:
            self.ROI_button.config(state='disabled')
            print('no file')
            
