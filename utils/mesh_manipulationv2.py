#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 12:51:37 2024

@author: mitchell
"""
import sys
from datetime import date
import pyvista as pv
from pyvistaqt import BackgroundPlotter
from PyQt5 import QtWidgets
import os


class ManipulationButton:
    def __init__(self, label, window, layout):
        self.label = label
        self.window = window
        self.value = 0
        self.layout = layout
        self.create_widgets()

    def create_widgets(self):
        # Add minus button
        self.minus_button = QtWidgets.QPushButton("-", self.window)
        self.minus_button.clicked.connect(self.on_minus_click)
        self.layout.addWidget(self.minus_button)

        # Add a label to track the value
        self.value_label = QtWidgets.QLabel(self.label + ':' + str(self.value), self.window)
        self.layout.addWidget(self.value_label)

        # Add plus button
        self.plus_button = QtWidgets.QPushButton("+", self.window)
        self.plus_button.clicked.connect(self.on_plus_click)
        self.layout.addWidget(self.plus_button)

    def on_minus_click(self):
        self.decrease_value()
        self.update_value()

    def on_plus_click(self):
        self.increase_value()
        self.update_value()

    def update_value(self):
        self.value_label.setText(self.label + ':' + str(self.value))
        self.perform_action()

    def decrease_value(self):
        raise NotImplementedError("Subclasses should implement this!")

    def increase_value(self):
        raise NotImplementedError("Subclasses should implement this!")

    def perform_action(self):
        raise NotImplementedError("Subclasses should implement this!")

class TranslationButton(ManipulationButton):
    def __init__(self, axis, window, layout):
        super().__init__(axis, window, layout)

    def decrease_value(self):
        self.value -= 0.5

    def increase_value(self):
        self.value += 0.5

    def perform_action(self):
        self.window.translate_mesh()

class RotationButton(ManipulationButton):
    def __init__(self, axis, window, layout, step_size=2):
        self.step_size = step_size
        super().__init__(axis, window, layout)

    def decrease_value(self):
        self.value -= self.step_size

    def increase_value(self):
        self.value += self.step_size

    def perform_action(self):
        self.window.rotate_mesh()

class MeshManipulationWindow(QtWidgets.QWidget):
    def __init__(self, helmet_mesh, head_mesh, animal_name='Example', helmet_type='Flat'):
        super().__init__()
        self.helmet_type = helmet_type
        self.animal_name = animal_name
        self.og_head_mesh, self.helmet_mesh = self.mesh_preprocess(head_mesh, helmet_mesh, name=self.animal_name)
        
# =============================================================================
#         # flip normals on helmet mesh
#         self.helmet_mesh.flip_normals()
# =============================================================================

        # Connect the destroyed signal of the window to the quit slot of the application
        self.destroyed.connect(QtWidgets.qApp.quit)
        # Connect the destroyed signal to the close_plotter method
        self.destroyed.connect(self.close_plotter)

        # Set default transformations
        self.offset = [0, 0, 0]
        self.scaling_factor = 1.0

        # Head mesh will catch all the transformations
        self.head_mesh = self.og_head_mesh.copy(deep=True)
        self.setup_ui()

    def setup_ui(self):
        # Create a layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Plot button
        plot_button = QtWidgets.QPushButton("Plot meshes", self)
        plot_button.clicked.connect(self.create_pvplotter)
        self.layout.addWidget(plot_button)

        # Rotation frame and layout
        rotation_frame = QtWidgets.QFrame(self)
        rotation_layout = QtWidgets.QHBoxLayout(rotation_frame)
        self.layout.addWidget(rotation_frame)

        # Add Rotation buttons
        self.rotation_button_X = RotationButton('Rotation X: ', self, rotation_layout)
        self.rotation_button_Y = RotationButton('Rotation Y: ', self, rotation_layout)
        self.rotation_button_Z = RotationButton('Rotation Z: ', self, rotation_layout)
        
        # Expansion buttons
        expand_frame = QtWidgets.QFrame(self)
        expand_layout = QtWidgets.QHBoxLayout(expand_frame)
        self.layout.addWidget(expand_frame)

        minus_button = QtWidgets.QPushButton("-", self)
        minus_button.clicked.connect(self.expand_mesh_minus)
        expand_layout.addWidget(minus_button)

        self.scaling_label = QtWidgets.QLabel(f"Expansion: {self.scaling_factor:.2f}", self)
        expand_layout.addWidget(self.scaling_label)

        plus_button = QtWidgets.QPushButton("+", self)
        plus_button.clicked.connect(self.expand_mesh_plus)
        expand_layout.addWidget(plus_button)

        # Translation buttons
        translation_frame = QtWidgets.QFrame(self)
        translation_layout = QtWidgets.QHBoxLayout(translation_frame)
        self.layout.addWidget(translation_frame)

        # Make dictionaries for each axis
        self.LR_translation = TranslationButton('LR', self, translation_layout)
        self.PA_translation = TranslationButton('PA', self, translation_layout)
        self.DV_translation = TranslationButton('DV', self, translation_layout)
        self.translation_list = [self.LR_translation, self.PA_translation, self.DV_translation]

        # toggle for chinpiece subtraction
        self.chin_toggle = QtWidgets.QCheckBox("Subtract chin piece?", self)
        self.chin_toggle.clicked.connect(self.ignore_chin)
        # variable for whether we ignore chinpiece or not
        self.chin_subtract_bool = False
        self.layout.addWidget(self.chin_toggle)

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
        self.plotter.add_mesh(self.chin_mesh)
        self.head_actor = self.plotter.add_mesh(self.head_mesh, color='magenta')
        self.plotter.show_bounds(grid='front', location='outer', all_edges=True)
        self.plotter.show()

    def close_plotter(self):
        # Close the PyVista plotter if it is initialized
        if self.plotter:
            self.plotter.close()

    def rotate_mesh(self):
        self.update_plotter()

    def expand_mesh_plus(self):
        self.scaling_factor += 0.01
        self.scaling_label.setText(f"{self.scaling_factor:.2f}")
        self.update_plotter()

    def expand_mesh_minus(self):
        self.scaling_factor -= 0.01
        self.scaling_label.setText(f"{self.scaling_factor:.2f}")
        self.update_plotter()

    def translate_mesh(self):
        self.update_plotter()
    
    def ignore_chin(self):
        
        if self.chin_toggle.isChecked():
            
            # make chin subtraction variable true
            self.chin_subtract_bool = True
            
        else:
            self.chin_subtract_bool = False
    

    def send_for_subtraction(self):
        if not self.head_mesh.is_manifold:
            print("Warning, non-manifold head segmentation, may cause crashing during subtraction")
        
# =============================================================================
#         self.chin_mesh.flip_normals()
# =============================================================================
        if self.chin_subtract_bool:
            self.chin_bool_mesh = self.chin_mesh.boolean_difference(self.head_mesh)
        
            # get rid of small residues resulting from chin topology
            self.chin_bool_mesh.extract_largest(inplace=True)
        
        bool_mesh = self.helmet_mesh.boolean_difference(self.head_mesh)
        
        # Here we slice out the portion of the helmet with sharp edges, 
        # smooth it out, then plug it back in
        bounds = [-21, 20, -20, 20, -20, -3]
        clipped = bool_mesh.clip_box(bounds)
        clipping = bool_mesh.clip_box(bounds, invert=False)
        surface = clipping.extract_geometry()
        smooth = surface.smooth_taubin(n_iter=70, pass_band=0.04, 
                                       non_manifold_smoothing=True, 
                                       normalize_coordinates=True)
        smooth.fill_holes(hole_size=20, inplace=True)
        self.final_mesh = clipped + smooth
        self.save_button.setDisabled(False)
        self.update_plotter(final_plot=True)

        
    def save_mesh(self):
        self.save_file = ('helmets/' + 
                      str(date.today()) + 
                      self.animal_name + 
                      str(self.scaling_factor)[2:] + 
                      'DV_' + 
                      str(self.DV_translation.value) + 
                      '.stl')
        chin_save_file = ('helmets/' + 
                          str(date.today()) + 
                          self.animal_name + 
                          'chinpiece.stl')
        self.final_mesh.extract_geometry().save(self.save_file)
        if self.chin_subtract_bool: 
            self.chin_bool_mesh.extract_geometry().save(chin_save_file)
            
        message = QtWidgets.QLabel(f'{self.save_file} and chinpiece successfully saved!')
        self.layout.addWidget(message)


    def update_plotter(self, final_plot=False):
        # Remove the previous head actor
        _ = self.plotter.remove_actor(self.head_actor, render=False)
        
        if final_plot:
            self.plotter.clear()
            self.plotter.add_mesh(self.final_mesh)
            if self.chin_subtract_bool:
                self.plotter.add_mesh(self.chin_bool_mesh)
        else:
            # Gather and apply transformations
            # scaling
            self.head_mesh = self.og_head_mesh.scale([self.scaling_factor, 1, 1])
            # translation
            self.head_mesh.points = self.head_mesh.points + [self.LR_translation.value, 
                                                             self.PA_translation.value, 
                                                             self.DV_translation.value]
            # rotation
            self.head_mesh.rotate_x(self.rotation_button_X.value, inplace=True)
            self.head_mesh.rotate_y(self.rotation_button_Y.value, inplace=True)
            self.head_mesh.rotate_z(self.rotation_button_Z.value, inplace=True)
            self.head_actor = self.plotter.add_mesh(self.head_mesh, color='magenta')
            self.plotter.update()

    def close_window(self):
        self.close()

    def run(self):
        self.show()

    def mesh_preprocess(self, head_mesh, helmet_mesh, name='Example', separate=False, scaling=1.00):
        """
        Given pyvista mesh of head stl, prepare proper positioning of head in helmet
    
        Returns
        -------
        helmet_mesh: pyvista mesh
        """
        # add chin piece mesh for custom chin piece
        chin_dir = 'templates/SubstractedChinPiece.stl'
        self.chin_mesh = pv.read(chin_dir).triangulate(inplace = True)
        
        # Zero the center of chin mesh
        self.chin_mesh.points -= self.chin_mesh.center
        
        # position chin piece mesh
        # Format [LR, PA, DV] or [X, Y, Z]
        chin_offset = [0,8,-27.5]
        self.chin_mesh.translate(chin_offset,inplace =True)
        
        # add text label for chin piece
        chin_text = pv.Text3D(self.animal_name, depth=.9)
        chin_text.scale([2.5,2.5,2.5], inplace = True)
        chin_text.rotate_z(-90, inplace=True)
        chin_text.rotate_x(180, inplace=True)
        chin_text_offset = [28,5,-19.5]
        chin_text.translate(chin_text_offset, inplace=True)
        self.chin_mesh = self.chin_mesh + chin_text
        
        
        # Scale up and rotate head mesh
        head_mesh.scale([scaling, scaling, scaling], inplace=True)
        head_mesh.rotate_x(270, inplace=True)
        head_mesh = head_mesh.decimate(.5)
    
        # Align the centers of both meshes at 0 then translate 
        helmet_mesh.points -= helmet_mesh.center
        head_mesh.points -= head_mesh.center
        
        # Format [LR, PA, DV] or [X, Y, Z]
        LR_offset = .7
        PA_offset = -9
        DV_offset = -3.5
        
        offset = [LR_offset,
                  helmet_mesh.bounds[2] - head_mesh.bounds[2] + PA_offset,
                  helmet_mesh.bounds[-1] - head_mesh.bounds[-1] + DV_offset]
    
        # Now translate the head mesh to match the helmet mesh
        head_mesh.translate(offset, inplace=True)
        
        # create text object for embossing
        text = pv.Text3D(self.animal_name, depth=.9)
        text.scale([2.5,2.5,2.5], inplace = True)
        text.rotate_z(90, inplace=True)
        if self.helmet_type == 'PET':
            text_offset = [27,5,-11.8] #12.5
        else:
            text_offset = [31,5,-14.5]
        text.points += text_offset
        
        # add text to helmet and chin to emboss
        helmet_mesh = helmet_mesh + text
    
        return head_mesh, helmet_mesh

# Example usage
if __name__ == '__main__':
    
    os.chdir('../')
    # setting up Qt application stuff
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    app.setQuitOnLastWindowClosed(True) 
    
    # Add your helmet_mesh and head_mesh here
    head_file = 'head_stls/TEST.stl'
    head_mesh = pv.read(head_file)
    
    helmet_mesh_file = 'templates/Flat_helmet.STL'
    helmet_mesh = pv.read(helmet_mesh_file).triangulate(inplace = True)
    
    window = MeshManipulationWindow(helmet_mesh, head_mesh, helmet_type = 'Flat')
    window.run()
    sys.exit(app.exec_())
