#!/bin/bash
# Script to install AMIGHOS in development mode

# Navigate to the project directory (change this if needed)
cd "$(dirname "$0")"

# Install in development mode
pip install -e .

echo "AMIGHOS installed in development mode."
echo "You can now import modules from anywhere using 'from amighosapp import ...'"
