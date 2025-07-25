#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Dependencies installed successfully!"
echo ""
echo "To set up and run the application:"
echo "  1. Download the latest Format.h:"
echo "     source venv/bin/activate"
echo "     python download_format_h.py"
echo ""
echo "  2. Parse the format style definitions:"
echo "     python parse_format_style.py"
echo ""
echo "  3. Run the Clang-Format UI:"
echo "     python clang_format_ui.py"
echo ""
echo "  4. Format entire directories (optional):"
echo "     ./format_directory.py /path/to/your/project"
echo ""
echo "Or run all steps at once:"
echo "  source venv/bin/activate && python download_format_h.py && python parse_format_style.py && python clang_format_ui.py"
