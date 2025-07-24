# Clang-Format Configuration UI

A modern, user-friendly graphical interface for configuring clang-format options with real-time C++ code preview.

![Clang-Format UI Screenshot](https://via.placeholder.com/800x400/2c3e50/ffffff?text=Clang-Format+UI)

## Features

- **Visual Configuration**: Intuitive GUI for all clang-format options
- **Real-time Preview**: See formatting changes applied to sample C++ code instantly
- **Complete Option Support**: 
  - Boolean fields (checkboxes)
  - Integer fields (spin boxes with validation)
  - String and vector fields (text inputs)
  - Enum fields (radio button selections)
  - Struct fields (nested configurations)
- **File Management**: Load, save, and create `.clang-format` files
- **Rich Documentation**: Built-in help with formatted descriptions for all options
- **Debounced Updates**: Smooth interaction without performance issues
- **Error Handling**: Clear feedback for configuration errors

## Requirements

- Python 3.7 or higher
- PySide6 (Qt for Python)
- PyYAML
- clang-format binary (for code formatting)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd clangformatui
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   This will:
   - Create a Python virtual environment
   - Install all required dependencies
   - Display instructions for running the application

## Usage

### Quick Start

After running the setup script, follow these steps:

1. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Download the latest Format.h from LLVM:**
   ```bash
   python download_format_h.py
   ```

3. **Parse the format style definitions:**
   ```bash
   python parse_format_style.py
   ```

4. **Launch the UI:**
   ```bash
   python clang_format_ui.py
   ```

### One-line Setup and Run
```bash
source venv/bin/activate && python download_format_h.py && python parse_format_style.py && python clang_format_ui.py
```

### Using the Interface

1. **Configuration Panel (Left)**: Browse and modify clang-format options organized by type
2. **Code Preview (Right)**: See real-time formatting applied to sample C++ code
3. **File Menu**: Create new configurations, open existing `.clang-format` files, or save your settings
4. **Tools Menu**: Set custom clang-format binary path or test your installation

### Configuration Options

The UI organizes clang-format options into categories:

- **Boolean Options**: Simple on/off toggles (e.g., `AllowShortFunctionsOnASingleLine`)
- **Integer Options**: Numeric values with validation (e.g., `IndentWidth`)
- **String Options**: Text and list inputs (e.g., `MacroBlockBegin`)
- **Enum Options**: Predefined choices (e.g., `BreakBeforeBraces: Allman`)
- **Struct Options**: Complex nested configurations (e.g., `SpaceBeforeParens`)

### File Operations

- **New**: Create a fresh configuration
- **Open**: Load an existing `.clang-format` file
- **Save**: Save current configuration
- **Save As**: Save with a new filename

## Project Structure

```
clangformatui/
├── clang_format_ui.py          # Main GUI application
├── download_format_h.py        # Downloads Format.h from LLVM
├── parse_format_style.py       # Parses Format.h into JSON
├── format_style_fields.json    # Parsed format definitions
├── Format.h                    # LLVM Format.h header file
├── requirements.txt            # Python dependencies
├── setup.sh                    # Setup script
├── test.clang-format          # Sample configuration file
├── README.md                   # This file
├── CHANGELOG.md                # Version history and changes
└── LICENSE                     # License information
```

## Development

### Architecture

The application consists of several key components:

- **Field Widgets**: Custom Qt widgets for different option types
  - `BooleanFieldWidget`: Checkboxes with descriptions
  - `IntegerFieldWidget`: Spin boxes with type validation
  - `StringFieldWidget`: Text inputs with list support
  - `EnumFieldWidget`: Radio button groups with descriptions
  - `StructFieldWidget`: Nested field containers

- **Configuration Management**: YAML serialization with proper type handling
- **Live Formatting**: Subprocess integration with clang-format binary
- **Rich Text Support**: Doxygen documentation parsing to HTML

### Extending the Application

To add support for new clang-format options:

1. Update `download_format_h.py` if needed for new LLVM versions
2. Run `parse_format_style.py` to regenerate `format_style_fields.json`
3. The UI will automatically detect and create appropriate widgets

### Custom clang-format Binary

If clang-format is not in your PATH or you want to use a specific version:

1. Use **Tools → Set clang-format Binary** in the menu
2. Or pass the path as a command line argument:
   ```bash
   python clang_format_ui.py --clang-format-binary /path/to/clang-format
   ```

## Troubleshooting

### Common Issues

**"clang-format not found"**
- Install clang-format: `sudo apt install clang-format` (Ubuntu/Debian) or `brew install clang-format` (macOS)
- Or set a custom binary path via the Tools menu

**"No format options loaded"**
- Ensure `format_style_fields.json` exists by running `python parse_format_style.py`
- Check that `Format.h` was downloaded successfully

**"Permission denied on setup.sh"**
- Make the script executable: `chmod +x setup.sh`

### Debug Mode

For debugging, you can run with verbose output:
```bash
python clang_format_ui.py --verbose
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### Development Setup

1. Follow the installation instructions
2. Install development dependencies (if any)
3. Make your changes
4. Test with various clang-format configurations
5. Submit a pull request

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PySide6](https://www.qt.io/qt-for-python) (Qt for Python)
- Integrates with [clang-format](https://clang.llvm.org/docs/ClangFormat.html) from the LLVM project
- Format definitions parsed from LLVM's Format.h header file
