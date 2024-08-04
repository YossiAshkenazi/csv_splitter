#!/bin/bash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

echo "Setup complete. Run 'source venv/bin/activate' to activate the virtual environment, then 'python csv_splitter_webapp.py' to start the application."
