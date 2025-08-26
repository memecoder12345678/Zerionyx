#!/bin/bash
set -e

PYTHON_FILE="zerionyx.py"
OUTPUT_DIR="output"
EXE_NAME="zerionyx"
INSTALL_DIR="$(pwd)/$OUTPUT_DIR"
EXIT_code=0

if [ -n "$BASH_VERSION" ]; then
    SHELL_CONFIG_FILE="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG_FILE="$HOME/.zshrc"
else
    SHELL_CONFIG_FILE="$HOME/.profile"
fi

if [ "$1" == "--clean" ]; then
    echo "Cleaning output directory..."
    if [ -d "$OUTPUT_DIR" ]; then
        rm -rf "$OUTPUT_DIR"
    fi
    echo "Clean complete."
elif [ "$1" == "--help" ]; then
    echo "Usage: ./build.sh [option]"
    echo "Options:"
    echo "  --clean      Clean the build directory."
    echo "  --install    Build the executable and add it to the shell's PATH."
    echo "  --uninstall  Remove the executable from the shell's PATH."
    echo "  --help       Show this help message."
    echo
    echo "If no option is provided, the script will only build the executable."
elif [ "$1" == "--install" ]; then
    echo "Building Zerionyx executable..."
    if [ ! -d "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR"
    fi
    nuitka --standalone --onefile --lto=yes --remove-output --output-dir="$OUTPUT_DIR" --output-filename="$EXE_NAME" "$PYTHON_FILE"
    if [ $? -ne 0 ]; then
        echo "Build failed. Installation aborted."
        exit 1
    fi
    echo "Build successful."
    echo
    echo "Adding '$INSTALL_DIR' to PATH in '$SHELL_CONFIG_FILE'..."

    if grep -q "export PATH=.*$INSTALL_DIR" "$SHELL_CONFIG_FILE"; then
        echo "Path is already set in $SHELL_CONFIG_FILE. No changes needed."
    else
        echo '' >> "$SHELL_CONFIG_FILE"
        echo '# Add Zerionyx to PATH' >> "$SHELL_CONFIG_FILE"
        echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$SHELL_CONFIG_FILE"
        echo "Successfully added Zerionyx to PATH."
        echo "Please run 'source $SHELL_CONFIG_FILE' or restart your terminal for the changes to take effect."
    fi
elif [ "$1" == "--uninstall" ]; then
    echo "Removing '$INSTALL_DIR' from PATH in '$SHELL_CONFIG_FILE'..."
    if [ -f "$SHELL_CONFIG_FILE" ]; then
        sed -i.bak "/# Add Zerionyx to PATH/d" "$SHELL_CONFIG_FILE"
        sed -i.bak "/export PATH=.*$INSTALL_DIR/d" "$SHELL_CONFIG_FILE"
        echo "Successfully removed Zerionyx from PATH."
        echo "A backup of your config was saved to '$SHELL_CONFIG_FILE.bak'."
        echo "Please restart your terminal for the changes to take effect."
    else
        echo "Warning: Shell config file '$SHELL_CONFIG_FILE' not found."
    fi
elif [ -z "$1" ]; then
    echo "Building Zerionyx executable..."
    if [ ! -d "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR"
    fi
    nuitka --standalone --onefile --lto=yes --remove-output --output-dir="$OUTPUT_DIR" --output-filename="$EXE_NAME" "$PYTHON_FILE"
    echo "Build complete. Executable is in '$OUTPUT_DIR'."
else
    echo "Error: Invalid option '$1'."
    echo "Use './build.sh --help' to see available options."
    EXIT_code=1
fi

exit $EXIT_code
