#!/bin/bash

# This script ensures pre-commit is installed and runs all hooks to format the codebase.

set -e  # Exit immediately if a command exits with a non-zero status.

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null
then
    echo "pre-commit is not installed. Installing it now..."
    pip install pre-commit
fi

# Install the hooks defined in .pre-commit-config.yaml
echo "Installing pre-commit hooks..."
pre-commit install

# Run pre-commit hooks against all files
echo "Running pre-commit hooks on all files..."
pre-commit run --all-files

# Success message
echo "Codebase formatted successfully!"
