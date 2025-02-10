#!/bin/bash

HOME="/Users/rajkumar"
# Path to your virtual environment
VENV_PATH="$HOME/sandbox/myenv"

# Path to your Python script
SCRIPT_PATH="$HOME/sandbox/stats.py"

# Activate the virtual environment
source "$VENV_PATH/bin/activate"


# Authenticate with Google Cloud (assuming you've already set up authentication)
/opt/homebrew/bin/gcloud auth activate-service-account --key-file="$HOME/sandbox/ferrous-ranger-448206-v2-633ad35b299d.json"

export GOOGLE_APPLICATION_CREDENTIALS="$HOME/sandbox/ferrous-ranger-448206-v2-633ad35b299d.json"
# Run the Python script
python3 "$SCRIPT_PATH"

