#!/usr/bin/env python3
"""
Clang-Format UI - A GUI for configuring clang-format options.

This application provides a visual interface for configuring clang-format
options based on the FormatStyle struct from LLVM's Format.h.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QScrollArea, QTextEdit, QSplitter, QLabel, QFrame, QCheckBox,
    QPushButton, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon


class BooleanFieldWidget(QWidget):
    """Widget for boolean configuration fields."""
    
    value_changed = Signal(str, bool)  # field_name, value
    value_removed = Signal(str)  # field_name
    
    def __init__(self, field_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.field_name = field_data["name"]
        self.field_data = field_data
        self.is_set = False  # Track if this field is currently set in config
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the widget UI."""
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Top row: checkbox and trash button
        top_layout = QHBoxLayout()
        
        # Checkbox with field name
        self.checkbox = QCheckBox(self.field_name)
        self.checkbox.setFont(QFont("Arial", 10, QFont.Bold))
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        top_layout.addWidget(self.checkbox)
        
        # Spacer
        top_layout.addStretch()
        
        # Info button (toggles description visibility)
        self.info_button = QPushButton("ℹ")
        self.info_button.setFixedSize(30, 30)
        self.info_button.setToolTip("Show/hide description")
        self.info_button.setCheckable(True)  # Make it toggleable
        self.info_button.setChecked(False)  # Initially unchecked (description hidden)
        self.info_button.clicked.connect(self.on_info_clicked)
        self.info_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:checked {
                background-color: #27ae60;
            }
            QPushButton:checked:hover {
                background-color: #219a52;
            }
        """)
        top_layout.addWidget(self.info_button)
        
        # Trash button
        self.trash_button = QPushButton("🗑")
        self.trash_button.setFixedSize(30, 30)
        self.trash_button.setToolTip("Remove this setting")
        self.trash_button.setEnabled(False)  # Initially disabled
        self.trash_button.clicked.connect(self.on_trash_clicked)
        self.trash_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        top_layout.addWidget(self.trash_button)
        
        layout.addLayout(top_layout)
        
        # Description label
        self.description_label = QLabel(self.field_data["description"])
        self.description_label.setFont(QFont("Arial", 10))  # Increased from 8 to 10
        self.description_label.setStyleSheet("color: #7f8c8d; margin-left: 20px;")
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumWidth(400)
        self.description_label.setVisible(False)  # Initially hidden
        layout.addWidget(self.description_label)
        
        # Style the entire widget as a box
        self.setStyleSheet("""
            BooleanFieldWidget {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 5px;
                margin: 2px;
            }
            BooleanFieldWidget:hover {
                border-color: #3498db;
            }
        """)
    
    def on_checkbox_changed(self, state):
        """Handle checkbox state change."""
        is_checked = state == Qt.Checked
        # Always emit value_changed when checkbox changes, regardless of checked state
        self.value_changed.emit(self.field_name, is_checked)
    
    def on_info_clicked(self):
        """Handle info button click to toggle description visibility."""
        is_checked = self.info_button.isChecked()
        self.description_label.setVisible(is_checked)
    
    def on_trash_clicked(self):
        """Handle trash button click."""
        # Don't change checkbox state, just remove from dictionary
        self.value_removed.emit(self.field_name)
    
    def set_value(self, value: bool):
        """Set the checkbox value programmatically."""
        self.checkbox.setChecked(value)
        self.is_set = value
        self.trash_button.setEnabled(value)
    
    def update_trash_button_state(self, is_in_config: bool):
        """Update the trash button state based on whether field is in config dictionary."""
        self.is_set = is_in_config
        self.trash_button.setEnabled(is_in_config)
    
    def reset_to_default(self):
        """Reset the field to its default state (unchecked, not configured)."""
        # Temporarily disconnect the signal to avoid triggering value_changed
        self.checkbox.stateChanged.disconnect()
        self.checkbox.setChecked(False)  # Default state is unchecked
        # Reconnect the signal
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)


class ClangFormatUI(QMainWindow):
    """Main window for the Clang-Format UI application."""
    
    def __init__(self):
        super().__init__()
        self.format_data: Dict[str, Any] = {}
        self.config_values: Dict[str, Any] = {}  # Store current configuration values
        self.field_widgets: List[BooleanFieldWidget] = []  # Track created widgets
        self.init_ui()
        self.load_format_data()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Clang-Format Configuration UI")
        self.setGeometry(100, 100, 1400, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create splitter for resizable columns
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left column: Configuration options
        self.create_left_column(splitter)
        
        # Right column: Code preview
        self.create_right_column(splitter)
        
        # Set initial splitter sizes (60% left, 40% right)
        splitter.setSizes([840, 560])
        
    def create_left_column(self, parent):
        """Create the left column containing configuration options."""
        # Create left panel frame
        left_frame = QFrame()
        left_frame.setFrameStyle(QFrame.StyledPanel)
        left_frame.setLineWidth(1)
        
        # Layout for left column
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        
        # Title for left column
        title_label = QLabel("Clang-Format Configuration Options")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                border-bottom: 2px solid #3498db;
                margin-bottom: 10px;
            }
        """)
        left_layout.addWidget(title_label)
        
        # Scroll area for configuration options
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Widget to contain the configuration options
        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout(self.config_widget)
        self.config_layout.setContentsMargins(5, 5, 5, 5)
        self.config_layout.setSpacing(8)
        
        # This will be replaced when we load the format data
        self.create_placeholder_content()
        
        scroll_area.setWidget(self.config_widget)
        left_layout.addWidget(scroll_area)
        
        parent.addWidget(left_frame)
    
    def create_placeholder_content(self):
        """Create placeholder content before format data is loaded."""
        placeholder_label = QLabel("Loading configuration options...")
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-style: italic;
                padding: 20px;
                text-align: center;
            }
        """)
        self.config_layout.addWidget(placeholder_label)
        
        # Add stretch to push content to top
        self.config_layout.addStretch()
        
    def create_right_column(self, parent):
        """Create the right column containing code preview."""
        # Create right panel frame
        right_frame = QFrame()
        right_frame.setFrameStyle(QFrame.StyledPanel)
        right_frame.setLineWidth(1)
        
        # Layout for right column
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # Title for right column
        title_label = QLabel("C++ Code Preview")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                border-bottom: 2px solid #e74c3c;
                margin-bottom: 10px;
            }
        """)
        right_layout.addWidget(title_label)
        
        # Text editor for code preview
        self.code_editor = QTextEdit()
        self.code_editor.setPlainText(self.get_sample_code())
        
        # Set monospace font for code
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Monaco", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.code_editor.setFont(font)
        
        # Style the code editor
        self.code_editor.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 10px;
                selection-background-color: #3498db;
            }
        """)
        
        right_layout.addWidget(self.code_editor)
        
        parent.addWidget(right_frame)
        
    def get_sample_code(self) -> str:
        """Return sample C++ code for formatting preview."""
        return """#include <iostream>
#include <vector>
#include <string>

namespace Example {
    class FormatDemo {
    public:
        FormatDemo(int value, const std::string& name) 
            : m_value(value), m_name(name) {}
        
        void processData() {
            if (m_value > 0) {
                std::cout << "Processing: " << m_name << std::endl;
                
                std::vector<int> numbers = {1, 2, 3, 4, 5};
                for (const auto& num : numbers) {
                    if (num % 2 == 0) {
                        std::cout << num << " is even" << std::endl;
                    } else {
                        std::cout << num << " is odd" << std::endl;
                    }
                }
            }
        }
        
        template<typename T>
        bool compare(const T& a, const T& b) {
            return a < b;
        }
        
    private:
        int m_value;
        std::string m_name;
    };
    
    enum class Status {
        Pending,
        InProgress,
        Completed,
        Failed
    };
    
    struct Configuration {
        bool enableLogging = true;
        int maxRetries = 3;
        std::string outputPath = "/tmp/output";
    };
}

int main() {
    Example::FormatDemo demo(42, "Test Demo");
    demo.processData();
    
    Example::Configuration config;
    config.enableLogging = false;
    
    return 0;
}"""
        
    def load_format_data(self):
        """Load format style data from JSON file."""
        json_file = Path("format_style_fields.json")
        
        if not json_file.exists():
            print(f"Warning: {json_file} not found. UI will show placeholder content.")
            return
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.format_data = json.load(f)
            print(f"Loaded {len(self.format_data.get('fields', []))} format options")
            
            # Create UI elements from format_data
            self.create_config_widgets()
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading format data: {e}")
    
    def create_config_widgets(self):
        """Create widgets for configuration options based on loaded data."""
        # Clear existing content
        self.clear_layout(self.config_layout)
        
        # Filter boolean fields
        boolean_fields = [
            field for field in self.format_data.get('fields', [])
            if field.get('type') == 'bool'
        ]
        
        print(f"Creating widgets for {len(boolean_fields)} boolean fields")
        
        # Create section header
        header_label = QLabel(f"Boolean Options ({len(boolean_fields)} fields)")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px 5px;
                border-bottom: 1px solid #bdc3c7;
                margin-bottom: 10px;
            }
        """)
        self.config_layout.addWidget(header_label)
        
        # Create widgets for each boolean field
        for field in boolean_fields:
            widget = BooleanFieldWidget(field)
            widget.value_changed.connect(self.on_field_value_changed)
            widget.value_removed.connect(self.on_field_value_removed)
            self.field_widgets.append(widget)
            self.config_layout.addWidget(widget)
        
        # Add stretch to push content to top
        self.config_layout.addStretch()
        
        # Show some statistics
        stats_label = QLabel(f"Total fields: {len(self.format_data.get('fields', []))}\n"
                           f"Boolean fields: {len(boolean_fields)}\n"
                           f"Other types: {len(self.format_data.get('fields', [])) - len(boolean_fields)}")
        stats_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 9px;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 3px;
                margin-top: 10px;
            }
        """)
        self.config_layout.addWidget(stats_label)
    
    def clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def on_field_value_changed(self, field_name: str, value: bool):
        """Handle when a field value is changed."""
        # Always add to config dictionary when checkbox changes
        self.config_values[field_name] = value
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        print(f"Set {field_name} = {value}")
        print(f"Current config has {len(self.config_values)} values")
    
    def on_field_value_removed(self, field_name: str):
        """Handle when a field value is removed."""
        if field_name in self.config_values:
            del self.config_values[field_name]
            
            # Update trash button state and reset checkbox for this field
            widget = self.get_field_widget(field_name)
            if widget:
                widget.update_trash_button_state(False)  # Field no longer in config
                widget.reset_to_default()  # Reset checkbox to unchecked (default state)
            
            print(f"Removed {field_name}")
            print(f"Current config has {len(self.config_values)} values")
    
    def get_field_widget(self, field_name: str) -> 'BooleanFieldWidget':
        """Get the widget for a specific field name."""
        for widget in self.field_widgets:
            if widget.field_name == field_name:
                return widget
        return None


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Clang-Format UI")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Development Tools")
    
    # Create and show main window
    window = ClangFormatUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
