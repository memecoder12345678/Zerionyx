
#!/bin/bash
set -e
PYTHON_FILE="zerionyx.py"
OUTPUT_DIR="output"
EXIT_code=0
if [ "$1" == "--clean" ]; then
    if [ -d "$OUTPUT_DIR" ]; then
        rm -rf "$OUTPUT_DIR"
    fi
elif [ "$1" == "--help" ]; then
    echo "Usage: ./build.sh [option]"
    echo "Options:"
    echo "  --clean    Clean the output directory."
    echo "  --help     Show this help message."
    echo
    echo "If no option is provided, the script will build the Python file."
elif [ -z "$1" ]; then
    if [ ! -d "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR"
    fi
    nuitka --standalone --onefile --lto=yes --remove-output --output-dir="$OUTPUT_DIR" "$PYTHON_FILE"
    echo "WARNING: This script only creates executable files. To be able to call them, you need to add them to your \$PATH."
else
    echo "Error: Invalid option '$1'."
    echo "Use './build.sh --help' to see available options."
    EXIT_code=1
fi
exit $EXIT_code
