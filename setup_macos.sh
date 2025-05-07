#!/bin/bash

# Stop on first error
set -e

echo "Starting setup of the Context Builder tool for macOS..."

# --- Configuration ---
PYTHON_SCRIPT_NAME="context_builder.py"
APP_NAME="ContextBuilder" # This will be the name of your .app bundle
REQUIREMENTS_FILE_NAME="requirements.txt"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PYTHON_SCRIPT_PATH="$SCRIPT_DIR/$PYTHON_SCRIPT_NAME"
REQUIREMENTS_FILE_PATH="$SCRIPT_DIR/$REQUIREMENTS_FILE_NAME"

# Build artifacts directory (will be created inside SCRIPT_DIR)
BUILD_ARTIFACTS_DIR_NAME="ContextBuilder_MacOSBuild"
BUILD_ARTIFACTS_PATH="$SCRIPT_DIR/$BUILD_ARTIFACTS_DIR_NAME"

# --- Sanity Checks ---
if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
    echo "ERROR: Python script '$PYTHON_SCRIPT_NAME' not found in '$SCRIPT_DIR'."
    echo "Please ensure '$PYTHON_SCRIPT_NAME' is in the same directory as this setup script."
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not on PATH. Please install Python 3 and rerun."
    exit 1
fi
echo "Python 3 version: $(python3 --version)"

# --- Prepare Build Directory ---
if [ -d "$BUILD_ARTIFACTS_PATH" ]; then
    echo "Removing existing $BUILD_ARTIFACTS_DIR_NAME directory: '$BUILD_ARTIFACTS_PATH'..."
    rm -rf "$BUILD_ARTIFACTS_PATH"
fi
echo "Creating $BUILD_ARTIFACTS_DIR_NAME directory at '$BUILD_ARTIFACTS_PATH'..."
mkdir -p "$BUILD_ARTIFACTS_PATH"

# --- Create requirements.txt ---
# windnd is Windows-specific, pip will ignore it on macOS due to the platform marker.
echo "Creating/Updating $REQUIREMENTS_FILE_NAME..."
cat << EOF > "$REQUIREMENTS_FILE_PATH"
requests
pyperclip
pyinstaller
windnd; sys_platform == 'win32'
EOF
echo "Wrote $REQUIREMENTS_FILE_NAME to '$REQUIREMENTS_FILE_PATH'"

# --- Create Virtual Environment ---
VENV_PATH="$BUILD_ARTIFACTS_PATH/venv"
echo "Creating Python virtual environment in '$VENV_PATH'..."
python3 -m venv "$VENV_PATH"

# --- Install Requirements ---
# Using direct paths to pip and python in the venv is safer for scripts
PIP_IN_VENV="$VENV_PATH/bin/pip"
PYTHON_IN_VENV="$VENV_PATH/bin/python"

echo "Upgrading pip in virtual environment..."
"$PIP_IN_VENV" install --upgrade pip

echo "Installing requirements from '$REQUIREMENTS_FILE_PATH' into virtual environment..."
"$PIP_IN_VENV" install -r "$REQUIREMENTS_FILE_PATH"

PYINSTALLER_IN_VENV="$VENV_PATH/bin/pyinstaller"
echo "Requirements installed."

# --- Build Application with PyInstaller ---
DIST_PATH="$BUILD_ARTIFACTS_PATH/dist"
WORK_PATH_INTERNAL="$BUILD_ARTIFACTS_PATH/build" # PyInstaller's working directory

echo "Building .app bundle with PyInstaller..."
echo "Output will be in: $DIST_PATH"

# For macOS, --windowed creates an .app bundle.
# Add --icon="path/to/your/icon.icns" if you have an icon file.
# Example: --icon="$SCRIPT_DIR/assets/app_icon.icns"
"$PYINSTALLER_IN_VENV" \
    --name "$APP_NAME" \
    --onefile \
    --windowed \
    --distpath "$DIST_PATH" \
    --workpath "$WORK_PATH_INTERNAL" \
    "$PYTHON_SCRIPT_PATH"
    # Add icon line here if you have one:
    # --icon="your_icon_name.icns" \


APP_BUNDLE_PATH="$DIST_PATH/$APP_NAME.app"

if [ -d "$APP_BUNDLE_PATH" ]; then
    echo ""
    echo "--------------------------------------------------------------------"
    echo "BUILD SUCCESSFUL!"
    echo "Setup complete for macOS."
    echo ""
    echo "Application Bundle: '$APP_BUNDLE_PATH'"
    echo ""
    echo "To run:"
    echo "1. Open Finder and navigate to: $DIST_PATH"
    echo "2. Double-click '$APP_NAME.app'."
    echo "3. You can also drag '$APP_NAME.app' to your /Applications folder."
    echo ""
    echo "The '$BUILD_ARTIFACTS_DIR_NAME' directory contains the virtual environment and build files."
    echo "You only need the '$APP_NAME.app' from the 'dist' subfolder to run the application."
    echo "--------------------------------------------------------------------"
else
    echo "ERROR: Build failed. Application bundle not found at '$APP_BUNDLE_PATH'."
    echo "Check PyInstaller output above for errors."
    exit 1
fi

exit 0