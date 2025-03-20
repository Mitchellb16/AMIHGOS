# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for AMIHGOS application
"""

import os
import sys

def main():
    # Add project root to path for imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Set working directory to project root for consistent file access
    os.chdir(project_root)
    
    # Now launch the app
    from amihgosapp.gui.home_window import HomeWindow
    home = HomeWindow()
    home.run()

if __name__ == "__main__":
    main()