# About
AMIHGOS (Automated Marmoset Imaging Helmet Generator - Open Source) Is a tool developed in Python for extracting head topology from CT images to generate custom 3D printable helmets to non-invasively reduce movement noise in neuroimaging. 

This tool was developed by adapting code from the [SimpleITK tutorial notebooks](https://insightsoftwareconsortium.github.io/SimpleITK-Notebooks/), David T. Chen's [dicom2stl](https://github.com/dave3d/dicom2stl/tree/main) script, and examples from the [Pyvista project](https://pyvista.org/).
Modifications to these tools were made to optimize functionality with the model organism and to establish compatibility with the [tkinter](https://docs.python.org/3/library/tkinter.html) and [PyQt](https://riverbankcomputing.com/software/pyqt/) GUI development libraries.

ChatGPT 3.5 was also used to develop the GUI portions of this program. 

# Getting started

## Installation
We ensure AMIHGOS has all the correct Python tools to run using [conda environments](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html#managing-python). 

1. Download and install the latest version of [conda](https://docs.anaconda.com/free/miniconda/) for your OS - we suggest miniconda for a minimal install experience. Restart your terminal/cmd window after install to get it running. 

2. Git clone this repository to your desired directory. For windows users, download and install [Git for Windows](https://git-scm.com/download/win).
   ```
   git clone https://github.com/Mitchellb16/AMIHGOS
   ```

3. Change directories into the AMIHGOS directory you just cloned.
   ```
   cd AMIHGOS
   ```
4. Create a conda environment from the amihgos-env.yml file in the AMIHGOS folder. This will take maybe 2 minutes at most and is the usual source of errors, add an issue to this repo if issues arise. 
   ```
   conda env create -f amihgos-env.yml -n AMIHGOS
   ```
5. Activate the conda environment you just created
   ```
   conda activate AMIHGOS
   ```
6. Run the AMIHGOS_v3.py file
   ```
   python AMIHGOS_v3.py
   ```
# Application Tutorial
Youtube video link to come in future commits. 


   
