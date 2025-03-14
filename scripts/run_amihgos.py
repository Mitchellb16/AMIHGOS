# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for AMIHGOS application
"""
import os
import sys

def main():
    """Main entry point for the application"""
    # During transition, we'll continue to use the old code structure
    # Later, this will be updated to use the new module structure
    from utils.HomeWindow import HomeWindow
    home = HomeWindow()
    home.run()

if __name__ == "__main__":
    # Add project root to path for development mode
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    main()
