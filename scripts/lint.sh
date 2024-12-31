#!/bin/bash

# This script ensures pre-commit is installed and runs only linting hooks on the codebase.

set -e  # Exit immediately if a command exits with a non-zero status.

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null
then
    echo "pre-commit is not installed. Installing it now..."
    pip install pre-commit
fi

# Run pre-commit linting hooks against all files
echo "Running pre-commit linting hooks on all files..."
pre-commit run --all-files --hook-stage commit-msg --hook-stage pre-commit

# Success message
echo "Linting completed successfully!"
