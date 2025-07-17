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
    QPushButton, QGroupBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
import re


class DoxygenParser:
    """Parser for converting Doxygen markup to HTML for rich text display."""
    
    @staticmethod
    def parse_to_html(doxygen_text: str) -> str:
        """Convert Doxygen markup to HTML."""
        if not doxygen_text:
            return ""
        
        html = doxygen_text
        
        # Handle escaped backslashes (\\code -> \code)
        html = html.replace('\\\\', '\\')
        
        # Parse version tags
        html = DoxygenParser._parse_version_tags(html)
        
        # Parse code blocks
        html = DoxygenParser._parse_code_blocks(html)
        
        # Parse inline code (backticks or \c command)
        html = DoxygenParser._parse_inline_code(html)
        
        # Convert newlines to HTML breaks (preserve formatting)
        html = html.replace('\n', '<br>')
        
        # Basic text formatting
        html = DoxygenParser._parse_basic_formatting(html)
        
        return html
    
    @staticmethod
    def _parse_version_tags(text: str) -> str:
        """Parse \\version tags."""
        # Match \version X.Y or \version X
        version_pattern = r'\\version\s+([0-9]+(?:\.[0-9]+)?)'
        
        def replace_version(match):
            version = match.group(1)
            return f'<div style="background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 5px 10px; margin: 5px 0; font-size: 9px;"><strong>Since version {version}</strong></div>'
        
        return re.sub(version_pattern, replace_version, text)
    
    @staticmethod
    def _parse_code_blocks(text: str) -> str:
        """Parse \\code...\\endcode blocks."""
        # Match code blocks with optional language specification
        code_pattern = r'\\code(?:\{\.(\w+)\})?\s*(.*?)\\endcode'
        
        def replace_code_block(match):
            language = match.group(1) or 'cpp'
            code_content = match.group(2).strip()
            
            # Clean up the code content
            code_content = code_content.replace('<br>', '\n')
            
            # Language-specific styling
            lang_color = {
                'java': '#f39c12',
                'cpp': '#2ecc71', 
                'c': '#2ecc71',
                'python': '#3498db'
            }.get(language.lower(), '#2ecc71')
            
            return f'''<div style="margin: 10px 0;">
                <div style="background-color: {lang_color}; color: white; padding: 2px 8px; font-size: 8px; font-weight: bold; border-radius: 3px 3px 0 0; display: inline-block;">
                    {language.upper()}
                </div>
                <pre style="background-color: #2b2b2b; color: #ffffff; padding: 10px; margin: 0; border-radius: 0 5px 5px 5px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 9px; white-space: pre-wrap; border-left: 3px solid {lang_color};">{code_content}</pre>
            </div>'''
        
        return re.sub(code_pattern, replace_code_block, text, flags=re.DOTALL)
    
    @staticmethod
    def _parse_inline_code(text: str) -> str:
        """Parse inline code with \\c or backticks."""
        # Parse \c command for inline code
        text = re.sub(r'\\c\s+(\w+)', r'<code style="background-color: #f1f2f6; color: #2f3542; padding: 1px 4px; border-radius: 2px; font-family: monospace; font-size: 9px;">\1</code>', text)
        
        # Parse backticks for inline code
        text = re.sub(r'`([^`]+)`', r'<code style="background-color: #f1f2f6; color: #2f3542; padding: 1px 4px; border-radius: 2px; font-family: monospace; font-size: 9px;">\1</code>', text)
        
        return text
    
    @staticmethod
    def _parse_basic_formatting(text: str) -> str:
        """Parse basic text formatting."""
        # Bold text (**text** or __text__)
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)
        
        # Italic text (*text* or _text_)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)
        
        return text


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
        
        # Description label with rich text support
        raw_description = self.field_data["description"]
        formatted_description = DoxygenParser.parse_to_html(raw_description)
        
        self.description_label = QLabel()
        self.description_label.setTextFormat(Qt.RichText)  # Enable rich text
        self.description_label.setText(formatted_description)
        self.description_label.setFont(QFont("Arial", 10))
        self.description_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                margin-left: 20px;
                background-color: #f8f9fa;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }
        """)
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumWidth(450)  # Slightly wider for formatted content
        self.description_label.setVisible(False)  # Initially hidden
        self.description_label.setOpenExternalLinks(False)  # Security: don't open external links
        layout.addWidget(self.description_label)
        
        # Style the entire widget as a box
        self.setStyleSheet("""
            BooleanFieldWidget {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 3px 0px;
            }
            BooleanFieldWidget:hover {
                border-color: #3498db;
                box-shadow: 0 2px 4px rgba(52, 152, 219, 0.1);
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


class IntegerFieldWidget(QWidget):
    """Widget for integer configuration fields."""
    
    value_changed = Signal(str, int)  # field_name, value
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
        
        # Top row: field name, spin box, and buttons
        top_layout = QHBoxLayout()
        
        # Field name label
        self.name_label = QLabel(self.field_name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setMinimumWidth(200)  # Ensure consistent spacing
        top_layout.addWidget(self.name_label)
        
        # Integer spin box
        self.spin_box = QSpinBox()
        self.spin_box.setRange(-999999, 999999)  # Wide range for various integer values
        self.spin_box.setValue(0)  # Default value
        self.spin_box.setFixedWidth(80)
        self.spin_box.valueChanged.connect(self.on_value_changed)
        self.spin_box.setStyleSheet("""
            QSpinBox {
                padding: 4px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background-color: white;
                font-size: 10px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        top_layout.addWidget(self.spin_box)
        
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
        
        # Description label with rich text support
        raw_description = self.field_data["description"]
        formatted_description = DoxygenParser.parse_to_html(raw_description)
        
        self.description_label = QLabel()
        self.description_label.setTextFormat(Qt.RichText)  # Enable rich text
        self.description_label.setText(formatted_description)
        self.description_label.setFont(QFont("Arial", 10))
        self.description_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                margin-left: 20px;
                background-color: #f8f9fa;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }
        """)
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumWidth(450)  # Slightly wider for formatted content
        self.description_label.setVisible(False)  # Initially hidden
        self.description_label.setOpenExternalLinks(False)  # Security: don't open external links
        layout.addWidget(self.description_label)
        
        # Style the entire widget as a box
        self.setStyleSheet("""
            IntegerFieldWidget {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 3px 0px;
            }
            IntegerFieldWidget:hover {
                border-color: #f39c12;
                box-shadow: 0 2px 4px rgba(243, 156, 18, 0.1);
            }
        """)
    
    def on_value_changed(self, value):
        """Handle spin box value change."""
        # Always emit value_changed when spin box changes
        self.value_changed.emit(self.field_name, value)
    
    def on_info_clicked(self):
        """Handle info button click to toggle description visibility."""
        is_checked = self.info_button.isChecked()
        self.description_label.setVisible(is_checked)
    
    def on_trash_clicked(self):
        """Handle trash button click."""
        # Remove from dictionary and reset to default
        self.value_removed.emit(self.field_name)
    
    def set_value(self, value: int):
        """Set the spin box value programmatically."""
        self.spin_box.setValue(value)
        self.is_set = True
        self.trash_button.setEnabled(True)
    
    def update_trash_button_state(self, is_in_config: bool):
        """Update the trash button state based on whether field is in config dictionary."""
        self.is_set = is_in_config
        self.trash_button.setEnabled(is_in_config)
    
    def reset_to_default(self):
        """Reset the field to its default state (0, not configured)."""
        # Temporarily disconnect the signal to avoid triggering value_changed
        self.spin_box.valueChanged.disconnect()
        self.spin_box.setValue(0)  # Default state is 0
        # Reconnect the signal
        self.spin_box.valueChanged.connect(self.on_value_changed)


class ClangFormatUI(QMainWindow):
    """Main window for the Clang-Format UI application."""
    
    def __init__(self):
        super().__init__()
        self.format_data: Dict[str, Any] = {}
        self.config_values: Dict[str, Any] = {}  # Store current configuration values
        self.field_widgets: List[QWidget] = []  # Track created widgets (both boolean and integer)
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
        
        # Filter fields by type
        boolean_fields = [
            field for field in self.format_data.get('fields', [])
            if field.get('type') == 'bool'
        ]
        
        integer_fields = [
            field for field in self.format_data.get('fields', [])
            if field.get('type') in ['int', 'unsigned']
        ]
        
        print(f"Creating widgets for {len(boolean_fields)} boolean fields and {len(integer_fields)} integer fields")
        
        # Create boolean section
        if boolean_fields:
            boolean_header = QLabel(f"Boolean Options ({len(boolean_fields)} fields)")
            boolean_header.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #2c3e50;
                    padding: 10px 5px;
                    border-bottom: 1px solid #3498db;
                    margin-bottom: 10px;
                    background-color: #ecf0f1;
                }
            """)
            self.config_layout.addWidget(boolean_header)
            
            # Create widgets for each boolean field
            for field in boolean_fields:
                widget = BooleanFieldWidget(field)
                widget.value_changed.connect(self.on_boolean_value_changed)
                widget.value_removed.connect(self.on_field_value_removed)
                self.field_widgets.append(widget)
                self.config_layout.addWidget(widget)
        
        # Create integer section
        if integer_fields:
            integer_header = QLabel(f"Integer Options ({len(integer_fields)} fields)")
            integer_header.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #2c3e50;
                    padding: 10px 5px;
                    border-bottom: 1px solid #f39c12;
                    margin-bottom: 10px;
                    margin-top: 15px;
                    background-color: #fef9e7;
                }
            """)
            self.config_layout.addWidget(integer_header)
            
            # Create widgets for each integer field
            for field in integer_fields:
                widget = IntegerFieldWidget(field)
                widget.value_changed.connect(self.on_integer_value_changed)
                widget.value_removed.connect(self.on_field_value_removed)
                self.field_widgets.append(widget)
                self.config_layout.addWidget(widget)
        
        # Add stretch to push content to top
        self.config_layout.addStretch()
        
        # Show some statistics
        total_fields = len(self.format_data.get('fields', []))
        other_fields = total_fields - len(boolean_fields) - len(integer_fields)
        
        stats_label = QLabel(f"Total fields: {total_fields}\n"
                           f"Boolean fields: {len(boolean_fields)}\n"
                           f"Integer fields: {len(integer_fields)}\n"
                           f"Other types: {other_fields}")
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
    
    def on_field_value_changed(self, field_name: str, value):
        """Handle when a field value is changed (for boolean fields - keeping for compatibility)."""
        # Always add to config dictionary when value changes
        self.config_values[field_name] = value
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        print(f"Set {field_name} = {value}")
        print(f"Current config has {len(self.config_values)} values")
    
    def on_boolean_value_changed(self, field_name: str, value: bool):
        """Handle when a boolean field value is changed."""
        # Always add to config dictionary when checkbox changes
        self.config_values[field_name] = value
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        print(f"Set boolean {field_name} = {value}")
        print(f"Current config has {len(self.config_values)} values")
    
    def on_integer_value_changed(self, field_name: str, value: int):
        """Handle when an integer field value is changed."""
        # Always add to config dictionary when spin box changes
        self.config_values[field_name] = value
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        print(f"Set integer {field_name} = {value}")
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
    
    def get_field_widget(self, field_name: str):
        """Get the widget for a specific field name (returns BooleanFieldWidget or IntegerFieldWidget)."""
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
