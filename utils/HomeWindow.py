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
        width= self.root.winfo_screenwidth()               
        height= self.root.winfo_screenheight()               
    
        self.root.geometry('800x600')
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
        self.logo = self.logo.subsample(10,10)
        self.logo_label = Label(master=self.intro_frame, image = self.logo)
        self.logo_label.image = self.logo
        self.logo_label.grid(column = 3, row = 0)
        
        # add gif of example helmet
        helm_gif = ImageLabel(self.intro_frame)
        helm_gif.grid(column=0, row=3, rowspan=4, sticky = 'nsew')
        helm_gif.load('images/helm_gif_earbars.gif')
        
        # button for selecting CT image directory
        self.load_file_button = Button(self.intro_frame, text='Load file', 
                                     command=self.browseFiles)
        self.load_file_button.grid(column=1, row=1)
        self.file_label = Label(self.intro_frame, text = 'No file chosen')
        self.file_label.grid(column = 2, row = 1)
        
        # buttons for about info, youtube, and github links 
        self.about_button = Button(self.intro_frame, text = 'About')
        self.about_button.grid(column = 1, row = 2)
        self.tutorial_button = Button(self.intro_frame, text = 'YouTube Tutorial')
        self.tutorial_button.grid(column = 1, row = 3)
        self.github_button = Button(self.intro_frame, text = 'Github', command = self.open_github)
        self.github_button.grid(column = 1, row = 4)
        
        # button for ROI selection, also unpacks the intro frame
        # also add a variable to track whether user has opened a file
        self.filevar = StringVar()
        self.filevar.trace_add('write', self.validate)
        # ROI button launches ROI class, unpacks the home frame, and resizes window
        self.ROI_button = Button(master = self.intro_frame, state=DISABLED, 
                            command = lambda:[self.intro_frame.pack_forget(), 
                                              self.root.geometry('1000x300'),
                                              ROIDataAquisition(self.moving_image, 
                                                                self.ROI_frame, 
                                                                self.root, 
                                                                self.frames_list)], 
                                text = 'Next: ROI Selection')
            
        self.ROI_button.grid(column=3, row=1)
        
    def run(self):
        # Start the Tkinter main loop
        mainloop()
    
    # file explorer window
    def browseFiles(self):
        global FILENAME
        FILENAME = filedialog.askopenfilename(initialdir = './nifti_files/',
                                              filetypes=[
                        ("image", ".dcm"),
                        ("image", ".nii"),
                        ("image", ".nii.gz"),
                    ])
        print('loaded file:', FILENAME)
        self.filevar.set(FILENAME)
        self.moving_image = sitk.DICOMOrient(sitk.ReadImage(FILENAME), 'LPS')
    
    def open_github(self):
        webbrowser.open('https://github.com/Mitchellb16/AMIHGOS', new = 1)
    
    def validate(self, var, index, mode):
        """
        Validates existence of directory selected by user
        """
        if self.filevar.get():
            self.ROI_button.config(state='normal')
            self.file_label['text'] = '...' + self.filevar.get()[-8:]
            
        else:
            self.ROI_button.config(state='disabled')
            print('no file')
            
# Example usage
# =============================================================================
# if __name__ == '__main__':
# =============================================================================
    