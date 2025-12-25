#!/bin/bash
# Activation helper script for the virtual environment

source .venv/bin/activate
echo "✓ Virtual environment activated"
echo "Python: $(python --version)"
echo "Location: $(which python)"
