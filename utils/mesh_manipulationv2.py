#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 19 11:06:40 2023

@author: mitchell
"""

import sys
from datetime import date
import pyvista as pv
from pyvistaqt import BackgroundPlotter
from PyQt5 import QtWidgets

class TranslationButton():
    # Creating a translation button object that uses the main window functions
    # because all the axes have similar functionality
    def __init__(self, axis, window, layout):
        self.axis = axis
        self.window = window
        self.magnitude = 0
        self.layout = layout
        # add minus button
        self.minus_button = QtWidgets.QPushButton("-", self.window)
        
        # when clicked, modify magnitude and call translation function
        self.minus_button.clicked.connect(lambda: 
                                             (self.subtract_magnitude(), window.translate_mesh()))

        self.layout.addWidget(self.minus_button)
        
        
        # add a label to track translation
        self.translation_label = QtWidgets.QLabel(
            self.axis +':' + str(self.magnitude), self.window)
        self.layout.addWidget(self.translation_label)
        
        # add plus button
        self.plus_button = QtWidgets.QPushButton("+", self.window)
        
        # when clicked, modify magnitude and call translation function
        self.plus_button.clicked.connect(lambda: 
                                             (self.add_magnitude(), window.translate_mesh()))

        self.layout.addWidget(self.plus_button)
        
    def subtract_magnitude(self):
        self.magnitude -= 1
    def add_magnitude(self):
        self.magnitude += 1

class MeshManipulationWindow(QtWidgets.QWidget):
    def __init__(self, helmet_mesh, head_mesh, animal_name = 'Example', helmet_type = 'Flat'):
        super().__init__()
        self.helmet_type = helmet_type
        self.animal_name = animal_name
        self.og_head_mesh, self.helmet_mesh = self.mesh_preprocess(head_mesh, helmet_mesh, name = self.animal_name)
        
        # Connect the destroyed signal of the window to the quit slot of the application
        self.destroyed.connect(QtWidgets.qApp.quit)
        # Connect the destroyed signal to the close_plotter method
        self.destroyed.connect(self.close_plotter)
        
        # set default transformations
        self.offset = [0,0,0]
        self.scaling_factor = 1.0
        
        # head mesh will catch all the transformations
        self.head_mesh = self.og_head_mesh.copy(deep=True)
        self.setup_ui()

    def setup_ui(self):
        # Create a layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Plot button
        plot_button = QtWidgets.QPushButton("Plot meshes", self)
        plot_button.clicked.connect(self.create_pvplotter)
        self.layout.addWidget(plot_button)

        # Rotation button
# =============================================================================
#         rotate_button = QtWidgets.QPushButton("Rotate", self)
#         rotate_button.clicked.connect(self.rotate_mesh)
#         self.layout.addWidget(rotate_button)
# =============================================================================

        # Expansion buttons
        expand_frame = QtWidgets.QFrame(self)
        expand_layout = QtWidgets.QHBoxLayout(expand_frame)
        self.layout.addWidget(expand_frame)

        minus_button = QtWidgets.QPushButton("-", self)
        minus_button.clicked.connect(self.expand_mesh_minus)
        expand_layout.addWidget(minus_button)

        self.scaling_label = QtWidgets.QLabel(f"Expansion: {self.scaling_factor+.15:.2f}", self)
        expand_layout.addWidget(self.scaling_label)

        plus_button = QtWidgets.QPushButton("+", self)
        plus_button.clicked.connect(self.expand_mesh_plus)
        expand_layout.addWidget(plus_button)

        # Translation buttons
        translation_frame = QtWidgets.QFrame(self)
        translation_layout = QtWidgets.QHBoxLayout(translation_frame)
        self.layout.addWidget(translation_frame)
        
        # make dictionaries for each axis
        self.LR_translation = TranslationButton('LR', self, translation_layout)
        self.PA_translation = TranslationButton('PA', self, translation_layout)
        self.DV_translation = TranslationButton('DV', self, translation_layout)
        self.translation_list = [self.LR_translation, self.PA_translation, self.DV_translation]
 
        # Send for subtraction button (green)
        send_button = QtWidgets.QPushButton("Send for subtraction", self)
        send_button.clicked.connect(self.send_for_subtraction)
        send_button.setStyleSheet("background-color: green")
        self.layout.addWidget(send_button)

        # Save button (greyed out initially)
        self.save_button = QtWidgets.QPushButton("Save", self)
        self.save_button.clicked.connect(self.save_mesh)
        self.save_button.setDisabled(True)
        self.save_button.setStyleSheet("background-color: grey")
        self.layout.addWidget(self.save_button)

        # Close button
        close_button = QtWidgets.QPushButton("Close", self)
        close_button.clicked.connect(self.close_window)
        self.layout.addWidget(close_button)

        # Set the layout to the main window
        self.setLayout(self.layout)

    def create_pvplotter(self):
        self.plotter = BackgroundPlotter(off_screen=False, notebook=False)
        self.plotter.add_mesh(self.helmet_mesh)
        self.head_actor = self.plotter.add_mesh(self.head_mesh, color = 'magenta')
        self.plotter.show_bounds(grid='front', location='outer', all_edges=True)
        self.plotter.show()
    
    def close_plotter(self):
        # Close the PyVista plotter if it is initialized
        if self.plotter:
            self.plotter.close()

    def rotate_mesh(self):
        # Implement your rotation logic here
        print('This will be implemented in a later update')
        self.update_plotter()

    def expand_mesh_plus(self):
        self.scaling_factor += 0.01
        self.scaling_label.setText(f"{self.scaling_factor+.15:.2f}")
        self.update_plotter()

    def expand_mesh_minus(self):
        self.scaling_factor -= 0.01
        self.scaling_label.setText(f"{self.scaling_factor+.15:.2f}")
        self.update_plotter()

    def translate_mesh(self):
        self.update_plotter()

    def send_for_subtraction(self):
        bool_mesh = self.helmet_mesh.boolean_difference(self.head_mesh)
        
        # here we slice out the portion of the helmet with sharp edges, 
        # smooth it out, then plug it back in
        bounds = [-21, 20, -20, 20, -18, -3]
        clipped = bool_mesh.clip_box(bounds)
        clipping = bool_mesh.clip_box(bounds, invert=False)
        surface = clipping.extract_geometry()
        smooth = surface.smooth_taubin(n_iter=70, pass_band=0.04, 
                                       non_manifold_smoothing=True, 
                                       normalize_coordinates=True)
        smooth.fill_holes(hole_size=20, inplace=True)
        self.final_mesh = clipped + smooth
        self.save_button.setDisabled(False)
        self.update_plotter(final_plot = True)

    def save_mesh(self):
        self.save_file = 'helmets/'+str(date.today())+self.animal_name+str(self.scaling_factor+.15)[2:]+'.stl'
        self.final_mesh.extract_geometry().save(self.save_file)
        message = QtWidgets.QLabel(f'{self.save_file} successfully saved!')
        self.layout.addWidget(message)

    def update_plotter(self, final_plot = False):
        # remove the previous head actor
        _ = self.plotter.remove_actor(self.head_actor, render = False)
        
        if final_plot:
            self.plotter.clear()
            self.plotter.add_mesh(self.final_mesh)
        
        else:
            # gather and apply transformations
            # scaling only in the LR direction
            self.head_mesh = self.og_head_mesh.scale([self.scaling_factor, 
                                  1, 
                                  1])
            self.head_mesh.points = self.head_mesh.points + [self.LR_translation.magnitude, 
                                                  self.PA_translation.magnitude, 
                                                  self.DV_translation.magnitude]
            self.head_actor = self.plotter.add_mesh(self.head_mesh, color = 'magenta')
            self.plotter.update()
    

    def close_window(self):
        self.close()

    def run(self):
        self.show()


        
    def mesh_preprocess(self, head_mesh, helmet_mesh, name='Example',
                        separate = False, 
                        scaling = 1.15):
        """
        Given pyvista mesh of head stl, return a subtraction of the head from 
        the helmet template
    
        Returns
        -------
        helmet_mesh: pyvista mesh
    
        """
    
        animal_name = name
        
    
        # scale up and rotate head mesh
        # LR, PA, DV
        head_mesh.scale([1.20,scaling,scaling], inplace=True)
        head_mesh.rotate_x(290, inplace=True)
        head_mesh = head_mesh.decimate(.5)
    
        
        # align the centers of both meshes at 0 then translate 
        helmet_mesh.points -= helmet_mesh.center
        head_mesh.points -= head_mesh.center
        
        # format [LR, PA, DV] or [X, Y, Z]
        # therefor bounds[2] is the back of the head, which we are aligning to the
        # back of the helmet, then nudging it forward a little
        LR_offset = .7
        PA_offset = 3
        DV_offset = -3.5
        
        offset = [LR_offset,
                  helmet_mesh.bounds[2]-head_mesh.bounds[2]+PA_offset, # 3
                  helmet_mesh.bounds[-1]-head_mesh.bounds[-1] + DV_offset] #3.5
        
        head_mesh.points += offset
        
        # create text object for embossing
        text = pv.Text3D(animal_name, depth=.9)
        text.scale([2.5,2.5,2.5], inplace = True)
        text.rotate_z(90, inplace=True)
        if self.helmet_type == 'PET':
            text_offset = [28,-3,-12.5] #12.5
        else:
            text_offset = [31,5,-14.5]
        text.points += text_offset
        
        # add text to helmet and chin to emboss
        helmet_mesh = helmet_mesh + text
        
        return head_mesh, helmet_mesh

# Example usage
if __name__ == '__main__':
    # setting up Qt application stuff
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    app.setQuitOnLastWindowClosed(True) 
    
    # Add your helmet_mesh and head_mesh here
    head_file = '../head_stls/JORAH.stl'
    head_mesh = pv.read(head_file)
    
    helmet_mesh_file = '../templates/Flat_helmet.STL'
    helmet_mesh = pv.read(helmet_mesh_file).triangulate(inplace = True)
    
    window = MeshManipulationWindow(helmet_mesh, head_mesh)
    window.run()
    sys.exit(app.exec_())
