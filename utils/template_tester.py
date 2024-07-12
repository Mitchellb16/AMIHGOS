#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  9 12:07:43 2024

@author: mitchell
"""



import pyvista as pv


# add chin piece mesh for custom chin piece
chin_dir = '../templates/SubstractedChinPiece.stl'
helmet_dir = '../templates/Flat_helmet.STL'

chin_mesh = pv.read(chin_dir).triangulate(inplace = True)
helmet_mesh = pv.read(helmet_dir).triangulate(inplace = True)

print("Chin mesh manifold?: " + str(chin_mesh.is_manifold))
print("Helmet mesh manifold?: " + str(helmet_mesh.is_manifold))

chin_mesh.plot_normals(mag = 3, faces=True, show_edges=True)
helmet_mesh.plot_normals(mag = 3, faces=True, show_edges=True)

