# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security

## [1.0.0] - 2025-01-24

### Added
- Initial release of Clang-Format Configuration UI
- Visual GUI for configuring all clang-format options
- Real-time C++ code preview with live formatting
- Support for all clang-format field types:
  - Boolean fields with checkboxes and descriptions
  - Integer fields with spin boxes and validation
  - String and vector fields with text inputs
  - Enum fields with radio button selections
  - Struct fields with nested configurations
- File management (New, Open, Save, Save As) for `.clang-format` files
- Rich documentation with Doxygen markup parsing to HTML
- Debounced updates for smooth user interaction
- Error handling with clear user feedback
- Menu system with File and Tools menus
- Custom clang-format binary path configuration
- clang-format binary testing functionality
- Automatic Format.h downloading from LLVM repository
- Format.h parsing to extract clang-format option definitions
- Professional UI styling with organized option categories
- Comprehensive help system with expandable descriptions
- YAML configuration file support with proper type handling
- Enum value mapping between C++ constants and YAML values
- Command-line arguments support:
  - `--clang-format-binary` for custom binary path
  - `--verbose` for debug output
- Cross-platform compatibility (Linux, macOS, Windows)
- Virtual environment setup script
- Comprehensive documentation (README, LICENSE, setup instructions)

### Fixed
- Boolean checkbox state handling (PySide6 enum vs integer comparison)
- Enum value emission (C++ constant names vs YAML values)
- Proper YAML serialization for all data types
- Memory management and widget cleanup
- File loading/saving with proper encoding
- Temporary file cleanup after formatting operations

## [0.9.0] - Development Phase

### Added
- Core GUI framework with PySide6
- Basic field widget architecture
- Configuration management system
- File I/O operations
- Format.h parsing infrastructure

### Fixed
- Initial implementation bugs
- UI layout and styling issues
- Data type handling problems

---

## Release Notes

### Version 1.0.0

This is the initial stable release of the Clang-Format Configuration UI. The application provides a complete graphical interface for configuring clang-format with real-time preview capabilities.

**Key Features:**
- Complete clang-format option support (159+ options)
- Live C++ code formatting preview
- Professional GUI with intuitive organization
- Robust file handling and error management
- Extensible architecture for future enhancements

**Requirements:**
- Python 3.7+
- PySide6
- PyYAML
- clang-format binary

**Installation:**
Run `./setup.sh` to automatically set up the environment and dependencies.

**Known Issues:**
- None reported in this release

**Future Plans:**
- Additional code samples and templates
- Custom styling themes
- Plugin system for extensions
- Integration with popular IDEs

---

## Contributing

When contributing to this project, please:

1. Follow [Semantic Versioning](https://semver.org/) for version numbers
2. Update this changelog with your changes
3. Use the following categories:
   - **Added** for new features
   - **Changed** for changes in existing functionality
   - **Deprecated** for soon-to-be removed features
   - **Removed** for now removed features
   - **Fixed** for any bug fixes
   - **Security** for vulnerability fixes

## Links

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [clang-format Documentation](https://clang.llvm.org/docs/ClangFormat.html)
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
