#!/usr/bin/env python3
"""
Clang-Format UI - A GUI for configuring clang-format options.

This application provides a visual interface for configuring clang-format
options based on the FormatStyle struct from LLVM's Format.h.
"""

import sys
import json
import re
import yaml
import tempfile
import subprocess
import threading
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Global verbose mode flag
VERBOSE_MODE = False

def debug_print(*args, **kwargs):
    """Print debug message only if verbose mode is enabled."""
    if VERBOSE_MODE:
        print(*args, **kwargs)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QScrollArea, QTextEdit, QSplitter, QLabel, QFrame, QCheckBox,
    QPushButton, QGroupBox, QSpinBox, QLineEdit, QRadioButton, QButtonGroup,
    QMenuBar, QMenu, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QAction
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
            }
        """)
    
    def on_checkbox_changed(self, state):
        """Handle checkbox state change."""
        # PySide6 stateChanged emits integers: 0=Unchecked, 1=PartiallyChecked, 2=Checked
        is_checked = state == Qt.Checked.value  # state == 2
        debug_print(f"Checkbox state changed: state={state}, is_checked={is_checked}")
        
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
    """Widget for integer configuration fields (int, unsigned, std::optional<unsigned>)."""
    
    value_changed = Signal(str, int)  # field_name, value
    value_removed = Signal(str)  # field_name
    
    def __init__(self, field_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.field_name = field_data["name"]
        self.field_data = field_data
        self.field_type = field_data.get("type", "int")
        self.is_optional = "optional" in self.field_type.lower()
        self.is_unsigned = "unsigned" in self.field_type.lower()
        self.is_set = False  # Track if this field is currently set in config
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the widget UI."""
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Top row: field name, optional checkbox, spin box, and buttons
        top_layout = QHBoxLayout()
        
        # Field name label
        self.name_label = QLabel(self.field_name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setMinimumWidth(200)  # Ensure consistent spacing
        top_layout.addWidget(self.name_label)
        
        # Optional checkbox (only for optional types)
        if self.is_optional:
            self.optional_checkbox = QCheckBox("Enable")
            self.optional_checkbox.setToolTip("Enable this optional setting")
            self.optional_checkbox.setChecked(False)  # Initially disabled
            self.optional_checkbox.stateChanged.connect(self.on_optional_changed)
            self.optional_checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 9px;
                    color: #7f8c8d;
                    margin-right: 5px;
                }
                QCheckBox:checked {
                    color: #27ae60;
                }
            """)
            top_layout.addWidget(self.optional_checkbox)
        
        # Integer spin box
        self.spin_box = QSpinBox()
        
        # Set range based on type
        if self.is_unsigned:
            self.spin_box.setRange(0, 999999)  # No negative values for unsigned
            self.spin_box.setValue(0)  # Default value for unsigned
        else:
            self.spin_box.setRange(-999999, 999999)  # Full range for signed int
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
            QSpinBox:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
            }
        """)
        
        # Initially disable spin box for optional fields
        if self.is_optional:
            self.spin_box.setEnabled(False)
        
        top_layout.addWidget(self.spin_box)
        
        # Type indicator label
        type_text = ""
        if self.is_optional:
            type_text = "optional "
        if self.is_unsigned:
            type_text += "unsigned"
        else:
            type_text += "int"
        
        self.type_label = QLabel(f"({type_text})")
        self.type_label.setStyleSheet("""
            QLabel {
                font-size: 8px;
                color: #6c757d;
                font-style: italic;
                margin-left: 5px;
            }
        """)
        top_layout.addWidget(self.type_label)
        
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
            }
        """)
    
    def on_optional_changed(self, state):
        """Handle optional checkbox state change."""
        # Compare integer values directly since PySide6 stateChanged emits integers
        is_checked = state == 2  # Qt.Checked has value 2
        self.spin_box.setEnabled(is_checked)
        
        if is_checked:
            # Optional field is now enabled, explicitly emit the current value
            # This ensures the config gets updated and trash button gets enabled
            current_value = self.spin_box.value()
            self.value_changed.emit(self.field_name, current_value)
        else:
            # Optional field is disabled, remove from config
            self.value_removed.emit(self.field_name)
        
        # Also update trash button state directly to ensure it's in sync
        self.trash_button.setEnabled(is_checked)
    
    def on_value_changed(self, value):
        """Handle spin box value change."""
        # For optional fields, only emit if checkbox is checked
        # For non-optional fields, always emit
        should_emit = False
        
        if self.is_optional:
            if hasattr(self, 'optional_checkbox') and self.optional_checkbox.isChecked():
                should_emit = True
        else:
            should_emit = True
        
        if should_emit:
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
        if self.is_optional and hasattr(self, 'optional_checkbox'):
            self.optional_checkbox.setChecked(True)
            self.spin_box.setEnabled(True)
        
        self.spin_box.setValue(value)
        self.is_set = True
        self.trash_button.setEnabled(True)
    
    def update_trash_button_state(self, is_in_config: bool):
        """Update the trash button state based on whether field is in config dictionary."""
        self.is_set = is_in_config
        self.trash_button.setEnabled(is_in_config)
    
    def reset_to_default(self):
        """Reset the field to its default state."""
        # Temporarily disconnect signals to avoid triggering value_changed
        self.spin_box.valueChanged.disconnect()
        if self.is_optional and hasattr(self, 'optional_checkbox'):
            self.optional_checkbox.stateChanged.disconnect()
            self.optional_checkbox.setChecked(False)  # Disable optional field
            self.spin_box.setEnabled(False)
        
        self.spin_box.setValue(0)  # Default state is 0
        
        # Reconnect signals
        self.spin_box.valueChanged.connect(self.on_value_changed)
        if self.is_optional and hasattr(self, 'optional_checkbox'):
            self.optional_checkbox.stateChanged.connect(self.on_optional_changed)


class StringFieldWidget(QWidget):
    """Widget for string and vector<string> configuration fields."""
    
    value_changed = Signal(str, object)  # field_name, value (string or list)
    value_removed = Signal(str)  # field_name
    
    def __init__(self, field_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.field_name = field_data["name"]
        self.field_data = field_data
        self.field_type = field_data.get("type", "std::string")
        self.is_vector = "vector" in self.field_type.lower()
        self.is_set = False  # Track if this field is currently set in config
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the widget UI."""
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Top row: field name, input field, and buttons
        top_layout = QHBoxLayout()
        
        # Field name label
        self.name_label = QLabel(self.field_name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setMinimumWidth(200)  # Ensure consistent spacing
        top_layout.addWidget(self.name_label)
        
        # String input field
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(
            "Enter comma-separated values..." if self.is_vector 
            else "Enter string value..."
        )
        self.line_edit.textChanged.connect(self.on_text_changed)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background-color: white;
                font-size: 10px;
                font-family: monospace;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QLineEdit:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
            }
        """)
        top_layout.addWidget(self.line_edit)
        
        # Type indicator label
        type_text = "vector<string>" if self.is_vector else "string"
        
        self.type_label = QLabel(f"({type_text})")
        self.type_label.setStyleSheet("""
            QLabel {
                font-size: 8px;
                color: #6c757d;
                font-style: italic;
                margin-left: 5px;
            }
        """)
        top_layout.addWidget(self.type_label)
        
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
        
        # Help text for vector fields
        if self.is_vector:
            help_label = QLabel("💡 Separate multiple values with commas (e.g., value1, value2, value3)")
            help_label.setStyleSheet("""
                QLabel {
                    font-size: 8px;
                    color: #7f8c8d;
                    font-style: italic;
                    margin-left: 20px;
                    margin-top: 2px;
                }
            """)
            layout.addWidget(help_label)
        
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
            StringFieldWidget {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 3px 0px;
            }
            StringFieldWidget:hover {
                border-color: #27ae60;
            }
        """)
    
    def on_text_changed(self, text):
        """Handle text input change."""
        # Only emit value if there's actually text (non-empty after strip)
        text = text.strip()
        if text:
            if self.is_vector:
                # Split by comma and trim each value
                values = [item.strip() for item in text.split(',') if item.strip()]
                self.value_changed.emit(self.field_name, values)
            else:
                # Single string value
                self.value_changed.emit(self.field_name, text)
        else:
            # Empty text means remove the field
            self.value_removed.emit(self.field_name)
    
    def on_info_clicked(self):
        """Handle info button click to toggle description visibility."""
        is_checked = self.info_button.isChecked()
        self.description_label.setVisible(is_checked)
    
    def on_trash_clicked(self):
        """Handle trash button click."""
        # Clear the input and remove from config
        self.line_edit.clear()
        self.value_removed.emit(self.field_name)
    
    def set_value(self, value):
        """Set the input value programmatically."""
        if self.is_vector and isinstance(value, list):
            # Join list values with comma and space
            text = ", ".join(str(v) for v in value)
        else:
            # Single string value
            text = str(value) if value is not None else ""
        
        self.line_edit.setText(text)
        self.is_set = bool(text.strip())
        self.trash_button.setEnabled(self.is_set)
    
    def update_trash_button_state(self, is_in_config: bool):
        """Update the trash button state based on whether field is in config dictionary."""
        self.is_set = is_in_config
        self.trash_button.setEnabled(is_in_config)
    
    def reset_to_default(self):
        """Reset the field to its default state."""
        # Temporarily disconnect the signal to avoid triggering value_changed
        self.line_edit.textChanged.disconnect()
        self.line_edit.clear()  # Default state is empty
        # Reconnect the signal
        self.line_edit.textChanged.connect(self.on_text_changed)


class EnumFieldWidget(QWidget):
    """Widget for enum configuration fields."""
    
    value_changed = Signal(str, str)  # field_name, enum_value
    value_removed = Signal(str)  # field_name
    
    def __init__(self, field_data: Dict[str, Any], enum_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.field_name = field_data["name"]
        self.field_data = field_data
        self.enum_type = field_data.get("type", "")
        self.enum_values = enum_data.get(self.enum_type, [])
        self.selected_value = None
        self.is_set = False
        self.is_expanded = False  # Track if enum options are visible
        
        # Radio button group for enum values
        self.button_group = QButtonGroup()
        self.radio_buttons = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the widget UI."""
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Top row: field name, current value, and buttons
        top_layout = QHBoxLayout()
        
        # Field name label
        self.name_label = QLabel(self.field_name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setMinimumWidth(200)  # Ensure consistent spacing
        top_layout.addWidget(self.name_label)
        
        # Current value label
        self.value_label = QLabel("(no selection)")
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #7f8c8d;
                font-style: italic;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 3px;
                min-width: 120px;
            }
        """)
        top_layout.addWidget(self.value_label)
        
        # Type indicator label
        self.type_label = QLabel(f"({self.enum_type})")
        self.type_label.setStyleSheet("""
            QLabel {
                font-size: 8px;
                color: #6c757d;
                font-style: italic;
                margin-left: 5px;
            }
        """)
        top_layout.addWidget(self.type_label)
        
        # Spacer
        top_layout.addStretch()
        
        # Info button (toggles description and enum options visibility)
        self.info_button = QPushButton("ℹ")
        self.info_button.setFixedSize(30, 30)
        self.info_button.setToolTip("Show/hide enum options and description")
        self.info_button.setCheckable(True)  # Make it toggleable
        self.info_button.setChecked(False)  # Initially unchecked (options hidden)
        self.info_button.clicked.connect(self.on_info_clicked)
        self.info_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
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
        
        # Container for enum description and options (initially hidden)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(8)
        
        # Enum description (field description)
        if self.field_data.get("description"):
            raw_description = self.field_data["description"]
            formatted_description = DoxygenParser.parse_to_html(raw_description)
            
            self.description_label = QLabel()
            self.description_label.setTextFormat(Qt.RichText)
            self.description_label.setText(formatted_description)
            self.description_label.setFont(QFont("Arial", 10))
            self.description_label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    background-color: #f8f9fa;
                    padding: 8px;
                    border-radius: 4px;
                    border: 1px solid #e9ecef;
                    margin-bottom: 10px;
                }
            """)
            self.description_label.setWordWrap(True)
            self.description_label.setMaximumWidth(450)
            self.description_label.setOpenExternalLinks(False)
            self.content_layout.addWidget(self.description_label)
        
        # Enum options section
        options_header = QLabel(f"Available Options ({len(self.enum_values)} values):")
        options_header.setFont(QFont("Arial", 9, QFont.Bold))
        options_header.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                margin-bottom: 5px;
                border-bottom: 1px solid #9b59b6;
                padding-bottom: 2px;
            }
        """)
        self.content_layout.addWidget(options_header)
        
        # Create radio buttons for each enum value
        for i, enum_value in enumerate(self.enum_values):
            value_name = enum_value.get("name", "")
            value_description = enum_value.get("description", "")
            
            # Container for each option
            option_widget = QWidget()
            option_layout = QVBoxLayout(option_widget)
            option_layout.setContentsMargins(5, 5, 5, 5)
            option_layout.setSpacing(3)
            
            # Radio button with enum value name
            radio_button = QRadioButton(value_name)
            radio_button.setFont(QFont("Arial", 9, QFont.Bold))
            radio_button.toggled.connect(lambda checked, name=value_name: self.on_option_selected(checked, name))
            radio_button.setStyleSheet("""
                QRadioButton {
                    color: #2c3e50;
                }
                QRadioButton:checked {
                    color: #9b59b6;
                    font-weight: bold;
                }
            """)
            self.radio_buttons.append(radio_button)
            self.button_group.addButton(radio_button, i)
            option_layout.addWidget(radio_button)
            
            # Description for this enum value
            if value_description:
                formatted_description = DoxygenParser.parse_to_html(value_description)
                
                desc_label = QLabel()
                desc_label.setTextFormat(Qt.RichText)
                desc_label.setText(formatted_description)
                desc_label.setFont(QFont("Arial", 8))
                desc_label.setStyleSheet("""
                    QLabel {
                        color: #6c757d;
                        margin-left: 20px;
                        background-color: #fdfdfe;
                        padding: 5px;
                        border-radius: 3px;
                        border: 1px solid #e9ecef;
                    }
                """)
                desc_label.setWordWrap(True)
                desc_label.setMaximumWidth(400)
                desc_label.setOpenExternalLinks(False)
                option_layout.addWidget(desc_label)
            
            # Style the option widget
            option_widget.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                    margin: 2px 0px;
                }
                QWidget:hover {
                    border-color: #9b59b6;
                }
            """)
            
            self.content_layout.addWidget(option_widget)
        
        # Initially hide the content widget
        self.content_widget.setVisible(False)
        layout.addWidget(self.content_widget)
        
        # Style the entire widget as a box
        self.setStyleSheet("""
            EnumFieldWidget {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 3px 0px;
            }
            EnumFieldWidget:hover {
                border-color: #9b59b6;
            }
        """)
    
    def convert_enum_to_yaml_value(self, enum_name: str) -> str:
        """Convert enum name (e.g., 'BOS_None') to YAML value (e.g., 'None')."""
        # Remove the enum prefix (everything up to and including the first underscore)
        if '_' in enum_name:
            return enum_name.split('_', 1)[1]
        return enum_name
    
    def convert_yaml_value_to_enum(self, yaml_value: str) -> str:
        """Convert YAML value (e.g., 'None') to enum name (e.g., 'BOS_None')."""
        # Find the enum that matches the YAML value
        for enum_value in self.enum_values:
            enum_name = enum_value.get("name", "")
            if self.convert_enum_to_yaml_value(enum_name) == yaml_value:
                return enum_name
        # If no match found, return the original value
        return yaml_value
    
    def on_option_selected(self, checked: bool, value_name: str):
        """Handle when an enum option is selected."""
        if checked:  # Only handle when option is selected (not deselected)
            self.selected_value = value_name
            self.value_label.setText(value_name)
            self.value_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #9b59b6;
                    font-weight: bold;
                    padding: 4px 8px;
                    background-color: #f4f1f8;
                    border: 1px solid #9b59b6;
                    border-radius: 3px;
                    min-width: 120px;
                }
            """)
            
            # Convert enum name to YAML value and emit the change
            yaml_value = self.convert_enum_to_yaml_value(value_name)
            self.value_changed.emit(self.field_name, yaml_value)
            
            # Update radio button styles to highlight selected
            self.update_radio_button_styles()
    
    def update_radio_button_styles(self):
        """Update radio button styles to highlight the selected one."""
        for radio_button in self.radio_buttons:
            if radio_button.isChecked():
                radio_button.setStyleSheet("""
                    QRadioButton {
                        color: #9b59b6;
                        font-weight: bold;
                        background-color: #f4f1f8;
                        padding: 2px;
                        border-radius: 3px;
                    }
                """)
            else:
                radio_button.setStyleSheet("""
                    QRadioButton {
                        color: #2c3e50;
                    }
                    QRadioButton:hover {
                        color: #9b59b6;
                    }
                """)
    
    def on_info_clicked(self):
        """Handle info button click to toggle options visibility."""
        self.is_expanded = self.info_button.isChecked()
        self.content_widget.setVisible(self.is_expanded)
    
    def on_trash_clicked(self):
        """Handle trash button click."""
        # Clear selection and remove from config
        self.button_group.setExclusive(False)  # Temporarily allow no selection
        for radio_button in self.radio_buttons:
            radio_button.setChecked(False)
        self.button_group.setExclusive(True)  # Restore exclusive selection
        
        self.selected_value = None
        self.value_label.setText("(no selection)")
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #7f8c8d;
                font-style: italic;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 3px;
                min-width: 120px;
            }
        """)
        
        self.update_radio_button_styles()
        self.value_removed.emit(self.field_name)
    
    def set_value(self, value: str):
        """Set the enum value programmatically."""
        # Convert YAML value to enum name for UI display
        enum_name = self.convert_yaml_value_to_enum(value)
        
        for radio_button in self.radio_buttons:
            if radio_button.text() == enum_name:
                radio_button.setChecked(True)
                self.selected_value = enum_name
                self.value_label.setText(enum_name)
                self.value_label.setStyleSheet("""
                    QLabel {
                        font-size: 10px;
                        color: #9b59b6;
                        font-weight: bold;
                        padding: 4px 8px;
                        background-color: #f4f1f8;
                        border: 1px solid #9b59b6;
                        border-radius: 3px;
                        min-width: 120px;
                    }
                """)
                self.is_set = True
                self.trash_button.setEnabled(True)
                self.update_radio_button_styles()
                break
    
    def update_trash_button_state(self, is_in_config: bool):
        """Update the trash button state based on whether field is in config dictionary."""
        self.is_set = is_in_config
        self.trash_button.setEnabled(is_in_config)
    
    def reset_to_default(self):
        """Reset the field to its default state."""
        # Clear all radio button selections
        self.button_group.setExclusive(False)
        for radio_button in self.radio_buttons:
            radio_button.setChecked(False)
        self.button_group.setExclusive(True)
        
        self.selected_value = None
        self.value_label.setText("(no selection)")
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #7f8c8d;
                font-style: italic;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 3px;
                min-width: 120px;
            }
        """)
        self.update_radio_button_styles()


class StructFieldWidget(QWidget):
    """Widget for custom struct configuration fields."""
    
    value_changed = Signal(str, dict)  # field_name, struct_dict
    value_removed = Signal(str)  # field_name
    
    def __init__(self, field_data: Dict[str, Any], struct_data: Dict[str, Any], format_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.field_name = field_data["name"]
        self.field_data = field_data
        self.struct_type = field_data.get("type", "")
        self.struct_definition = struct_data.get(self.struct_type, {})
        self.struct_fields = self.struct_definition.get("fields", [])
        self.format_data = format_data  # Full format data for nested lookups
        self.selected_values = {}  # Track selected values for each field
        self.is_set = False
        self.is_expanded = False  # Track if struct options are visible
        
        # Track nested field widgets
        self.nested_widgets = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the widget UI."""
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Top row: field name, current status, and buttons
        top_layout = QHBoxLayout()
        
        # Field name label
        self.name_label = QLabel(self.field_name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setMinimumWidth(200)  # Ensure consistent spacing
        top_layout.addWidget(self.name_label)
        
        # Current status label
        self.status_label = QLabel(f"({len(self.selected_values)} of {len(self.struct_fields)} set)")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #7f8c8d;
                font-style: italic;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 3px;
                min-width: 120px;
            }
        """)
        top_layout.addWidget(self.status_label)
        
        # Type indicator label
        self.type_label = QLabel(f"({self.struct_type})")
        self.type_label.setStyleSheet("""
            QLabel {
                font-size: 8px;
                color: #6c757d;
                font-style: italic;
                margin-left: 5px;
            }
        """)
        top_layout.addWidget(self.type_label)
        
        # Spacer
        top_layout.addStretch()
        
        # Info button (toggles description and struct fields visibility)
        self.info_button = QPushButton("ℹ")
        self.info_button.setFixedSize(30, 30)
        self.info_button.setToolTip("Show/hide struct fields and description")
        self.info_button.setCheckable(True)  # Make it toggleable
        self.info_button.setChecked(False)  # Initially unchecked (fields hidden)
        self.info_button.clicked.connect(self.on_info_clicked)
        self.info_button.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d35400;
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
        
        # Container for struct description and fields (initially hidden)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(8)
        
        # Struct description (field description)
        if self.field_data.get("description"):
            raw_description = self.field_data["description"]
            formatted_description = DoxygenParser.parse_to_html(raw_description)
            
            self.description_label = QLabel()
            self.description_label.setTextFormat(Qt.RichText)
            self.description_label.setText(formatted_description)
            self.description_label.setFont(QFont("Arial", 10))
            self.description_label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    background-color: #f8f9fa;
                    padding: 8px;
                    border-radius: 4px;
                    border: 1px solid #e9ecef;
                    margin-bottom: 10px;
                }
            """)
            self.description_label.setWordWrap(True)
            self.description_label.setMaximumWidth(450)
            self.description_label.setOpenExternalLinks(False)
            self.content_layout.addWidget(self.description_label)
        
        # Struct fields section
        fields_header = QLabel(f"Struct Fields ({len(self.struct_fields)} fields):")
        fields_header.setFont(QFont("Arial", 9, QFont.Bold))
        fields_header.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                margin-bottom: 5px;
                border-bottom: 1px solid #e67e22;
                padding-bottom: 2px;
            }
        """)
        self.content_layout.addWidget(fields_header)
        
        # Create nested widgets for each struct field in definition order
        for struct_field in self.struct_fields:
            self.create_nested_field_widget(struct_field)
        
        # Initially hide the content widget
        self.content_widget.setVisible(False)
        layout.addWidget(self.content_widget)
        
        # Style the entire widget as a box
        self.setStyleSheet("""
            StructFieldWidget {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 3px 0px;
            }
            StructFieldWidget:hover {
                border-color: #e67e22;
            }
        """)
    
    def create_nested_field_widget(self, struct_field: Dict[str, Any]):
        """Create a nested widget for a struct field."""
        field_type = struct_field.get("type", "")
        field_name = struct_field.get("name", "")
        
        # Create widget container
        field_container = QWidget()
        field_layout = QVBoxLayout(field_container)
        field_layout.setContentsMargins(5, 5, 5, 5)
        field_layout.setSpacing(3)
        
        # Determine widget type and create appropriate widget
        widget = None
        
        if field_type == "bool":
            widget = BooleanFieldWidget(struct_field)
            widget.value_changed.connect(lambda name, value: self.on_nested_value_changed(name, value))
            widget.value_removed.connect(lambda name: self.on_nested_value_removed(name))
        elif field_type in ['int', 'unsigned', 'std::optional<unsigned>']:
            widget = IntegerFieldWidget(struct_field)
            widget.value_changed.connect(lambda name, value: self.on_nested_value_changed(name, value))
            widget.value_removed.connect(lambda name: self.on_nested_value_removed(name))
        elif field_type in ['std::string', 'std::vector<std::string>']:
            widget = StringFieldWidget(struct_field)
            widget.value_changed.connect(lambda name, value: self.on_nested_value_changed(name, value))
            widget.value_removed.connect(lambda name: self.on_nested_value_removed(name))
        elif field_type in self.format_data.get('enum_definitions', {}):
            widget = EnumFieldWidget(struct_field, self.format_data.get('enum_definitions', {}))
            widget.value_changed.connect(lambda name, value: self.on_nested_value_changed(name, value))
            widget.value_removed.connect(lambda name: self.on_nested_value_removed(name))
        elif field_type in self.format_data.get('struct_definitions', {}):
            widget = StructFieldWidget(struct_field, self.format_data.get('struct_definitions', {}), self.format_data)
            widget.value_changed.connect(lambda name, value: self.on_nested_value_changed(name, value))
            widget.value_removed.connect(lambda name: self.on_nested_value_removed(name))
        
        if widget:
            # Style the nested widget with slightly different appearance
            widget.setStyleSheet("""
                QWidget {
                    background-color: #fdfdfe;
                    border: 1px solid #ecf0f1;
                    border-radius: 4px;
                    margin: 1px;
                }
                QWidget:hover {
                    border-color: #e67e22;
                }
            """)
            
            field_layout.addWidget(widget)
            self.nested_widgets.append(widget)
            self.content_layout.addWidget(field_container)
        else:
            # For unsupported field types, show a placeholder
            placeholder_label = QLabel(f"{field_name}: {field_type} (unsupported)")
            placeholder_label.setStyleSheet("""
                QLabel {
                    color: #7f8c8d;
                    font-style: italic;
                    padding: 8px;
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 3px;
                }
            """)
            field_layout.addWidget(placeholder_label)
            self.content_layout.addWidget(field_container)
    
    def on_nested_value_changed(self, field_name: str, value):
        """Handle when a nested field value is changed."""
        self.selected_values[field_name] = value
        self.update_status()
        
        # Emit the struct change with current values
        if self.selected_values:
            self.value_changed.emit(self.field_name, dict(self.selected_values))
    
    def on_nested_value_removed(self, field_name: str):
        """Handle when a nested field value is removed."""
        if field_name in self.selected_values:
            del self.selected_values[field_name]
        
        self.update_status()
        
        # Emit struct change or removal
        if self.selected_values:
            self.value_changed.emit(self.field_name, dict(self.selected_values))
        else:
            self.value_removed.emit(self.field_name)
    
    def update_status(self):
        """Update the status label and trash button state."""
        count = len(self.selected_values)
        total = len(self.struct_fields)
        
        self.status_label.setText(f"({count} of {total} set)")
        
        if count > 0:
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #e67e22;
                    font-weight: bold;
                    padding: 4px 8px;
                    background-color: #fdf2e9;
                    border: 1px solid #e67e22;
                    border-radius: 3px;
                    min-width: 120px;
                }
            """)
            self.trash_button.setEnabled(True)
            self.is_set = True
        else:
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #7f8c8d;
                    font-style: italic;
                    padding: 4px 8px;
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 3px;
                    min-width: 120px;
                }
            """)
            self.trash_button.setEnabled(False)
            self.is_set = False
    
    def on_info_clicked(self):
        """Handle info button click to toggle fields visibility."""
        self.is_expanded = self.info_button.isChecked()
        self.content_widget.setVisible(self.is_expanded)
    
    def on_trash_clicked(self):
        """Handle trash button click."""
        # Clear all nested selections and remove from config
        self.selected_values.clear()
        
        # Reset all nested widgets
        for widget in self.nested_widgets:
            widget.reset_to_default()
        
        self.update_status()
        self.value_removed.emit(self.field_name)
    
    def set_value(self, value: dict):
        """Set the struct value programmatically."""
        if isinstance(value, dict):
            self.selected_values = dict(value)
            
            # Update nested widgets
            for widget in self.nested_widgets:
                field_name = widget.field_name
                if field_name in value:
                    widget.set_value(value[field_name])
            
            self.update_status()
    
    def update_trash_button_state(self, is_in_config: bool):
        """Update the trash button state based on whether field is in config dictionary."""
        self.is_set = is_in_config
        if is_in_config:
            self.trash_button.setEnabled(True)
        else:
            if not self.selected_values:  # Only disable if no nested values
                self.trash_button.setEnabled(False)
    
    def reset_to_default(self):
        """Reset the field to its default state."""
        self.selected_values.clear()
        
        # Reset all nested widgets
        for widget in self.nested_widgets:
            widget.reset_to_default()
        
        self.update_status()


class ClangFormatUI(QMainWindow):
    """Main window for the Clang-Format UI application."""
    
    def __init__(self, clang_format_binary: str = "clang-format"):
        super().__init__()
        self.format_data: Dict[str, Any] = {}
        self.config_values: Dict[str, Any] = {}  # Store current configuration values
        self.field_widgets: List[QWidget] = []  # Track created widgets (both boolean and integer)
        self.current_file_path: str = ""  # Track currently loaded file
        self.is_modified: bool = False  # Track if current config has unsaved changes
        self.is_quitting: bool = False  # Track if we're in the quit process
        self.clang_format_binary: str = clang_format_binary  # Path to clang-format binary
        
        # Timer for debouncing format updates
        self.format_timer = QTimer()
        self.format_timer.setSingleShot(True)
        self.format_timer.timeout.connect(self.format_code_preview)
        self.format_timer.setInterval(500)  # 500ms delay
        
        self.init_ui()
        self.load_format_data()
        # Initial formatting
        self.schedule_format_update()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Clang-Format Configuration UI")
        self.setGeometry(100, 100, 1400, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
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
        
        # Header with title and status
        header_layout = QHBoxLayout()
        
        # Title for right column
        title_label = QLabel("C++ Code Preview")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
            }
        """)
        header_layout.addWidget(title_label)
        
        # Status label for formatting feedback
        self.format_status_label = QLabel("Ready")
        self.format_status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #27ae60;
                padding: 5px 10px;
                background-color: #d5f4e6;
                border-radius: 3px;
                border: 1px solid #27ae60;
            }
        """)
        header_layout.addStretch()
        header_layout.addWidget(self.format_status_label)
        
        right_layout.addLayout(header_layout)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #e74c3c;")
        right_layout.addWidget(separator)
        
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
        
        # Info label
        info_label = QLabel("💡 Code preview updates automatically as you change formatting options")
        info_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #7f8c8d;
                font-style: italic;
                padding: 5px;
                background-color: #f8f9fa;
                border-radius: 3px;
            }
        """)
        right_layout.addWidget(info_label)
        
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
    
    def create_menu_bar(self):
        """Create the menu bar with File menu."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        # New action
        new_action = QAction('&New', self)
        new_action.setShortcut('Ctrl+N')
        new_action.setStatusTip('Create a new clang-format configuration')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Open action
        open_action = QAction('&Open...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.setStatusTip('Open an existing .clang-format file')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Save action
        save_action = QAction('&Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.setStatusTip('Save the current configuration')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        # Save As action
        save_as_action = QAction('Save &As...', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.setStatusTip('Save the current configuration with a new name')
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Quit action
        quit_action = QAction('&Quit', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.setStatusTip('Exit the application')
        quit_action.triggered.connect(self.quit_application)
        file_menu.addAction(quit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('&Tools')
        
        # Set clang-format binary action
        set_binary_action = QAction('Set clang-format &Binary...', self)
        set_binary_action.setStatusTip('Set the path to the clang-format binary')
        set_binary_action.triggered.connect(self.set_clang_format_binary_dialog)
        tools_menu.addAction(set_binary_action)
        
        # Test clang-format action
        test_binary_action = QAction('&Test clang-format', self)
        test_binary_action.setStatusTip('Test if clang-format binary is working')
        test_binary_action.triggered.connect(self.test_clang_format_binary)
        tools_menu.addAction(test_binary_action)
        
    def load_format_data(self):
        """Load format style data from JSON file."""
        json_file = Path("format_style_fields.json")
        
        if not json_file.exists():
            print(f"Warning: {json_file} not found. UI will show placeholder content.")
            return
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.format_data = json.load(f)
            debug_print(f"Loaded {len(self.format_data.get('fields', []))} format options")
            
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
            if field.get('type') in ['int', 'unsigned', 'std::optional<unsigned>']
        ]
        
        string_fields = [
            field for field in self.format_data.get('fields', [])
            if field.get('type') in ['std::string', 'std::vector<std::string>']
        ]
        
        # Get list of known basic types
        basic_types = {'bool', 'int', 'unsigned', 'std::optional<unsigned>', 'std::string', 'std::vector<std::string>'}
        
        enum_fields = [
            field for field in self.format_data.get('fields', [])
            if field.get('type') not in basic_types and field.get('type') in self.format_data.get('enum_definitions', {})
        ]
        
        struct_fields = [
            field for field in self.format_data.get('fields', [])
            if field.get('type') not in basic_types and field.get('type') in self.format_data.get('struct_definitions', {})
        ]
        
        debug_print(f"Creating widgets for {len(boolean_fields)} boolean fields, {len(integer_fields)} integer fields, {len(string_fields)} string fields, {len(enum_fields)} enum fields, and {len(struct_fields)} struct fields")
        
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
        
        # Create string section
        if string_fields:
            string_header = QLabel(f"String Options ({len(string_fields)} fields)")
            string_header.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #2c3e50;
                    padding: 10px 5px;
                    border-bottom: 1px solid #27ae60;
                    margin-bottom: 10px;
                    margin-top: 15px;
                    background-color: #e8f8f5;
                }
            """)
            self.config_layout.addWidget(string_header)
            
            # Create widgets for each string field
            for field in string_fields:
                widget = StringFieldWidget(field)
                widget.value_changed.connect(self.on_string_value_changed)
                widget.value_removed.connect(self.on_field_value_removed)
                self.field_widgets.append(widget)
                self.config_layout.addWidget(widget)
        
        # Create enum section
        if enum_fields:
            enum_header = QLabel(f"Enum Options ({len(enum_fields)} fields)")
            enum_header.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #2c3e50;
                    padding: 10px 5px;
                    border-bottom: 1px solid #9b59b6;
                    margin-bottom: 10px;
                    margin-top: 15px;
                    background-color: #f4f1f8;
                }
            """)
            self.config_layout.addWidget(enum_header)
            
            # Create widgets for each enum field
            for field in enum_fields:
                widget = EnumFieldWidget(field, self.format_data.get('enum_definitions', {}))
                widget.value_changed.connect(self.on_enum_value_changed)
                widget.value_removed.connect(self.on_field_value_removed)
                self.field_widgets.append(widget)
                self.config_layout.addWidget(widget)
        
        # Create struct section
        if struct_fields:
            struct_header = QLabel(f"Struct Options ({len(struct_fields)} fields)")
            struct_header.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #2c3e50;
                    padding: 10px 5px;
                    border-bottom: 1px solid #e67e22;
                    margin-bottom: 10px;
                    margin-top: 15px;
                    background-color: #fdf2e9;
                }
            """)
            self.config_layout.addWidget(struct_header)
            
            # Create widgets for each struct field
            for field in struct_fields:
                widget = StructFieldWidget(field, self.format_data.get('struct_definitions', {}), self.format_data)
                widget.value_changed.connect(self.on_struct_value_changed)
                widget.value_removed.connect(self.on_field_value_removed)
                self.field_widgets.append(widget)
                self.config_layout.addWidget(widget)
        
        # Add stretch to push content to top
        self.config_layout.addStretch()
        
        # Show some statistics
        total_fields = len(self.format_data.get('fields', []))
        other_fields = total_fields - len(boolean_fields) - len(integer_fields) - len(string_fields) - len(enum_fields) - len(struct_fields)
        
        stats_label = QLabel(f"Total fields: {total_fields}\n"
                           f"Boolean fields: {len(boolean_fields)}\n"
                           f"Integer fields: {len(integer_fields)}\n"
                           f"String fields: {len(string_fields)}\n"
                           f"Enum fields: {len(enum_fields)}\n"
                           f"Struct fields: {len(struct_fields)}\n"
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
        debug_print(f"Set boolean {field_name} = {value}")
        debug_print(f"Current config has {len(self.config_values)} values")
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        # Mark as modified
        self.mark_as_modified()
        
        # Schedule format update
        self.schedule_format_update()
    
    def on_integer_value_changed(self, field_name: str, value: int):
        """Handle when an integer field value is changed."""
        # Always add to config dictionary when spin box changes
        self.config_values[field_name] = value
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        # Mark as modified
        self.mark_as_modified()
        
        # Schedule format update
        self.schedule_format_update()
        
        debug_print(f"Set integer {field_name} = {value}")
        debug_print(f"Current config has {len(self.config_values)} values")
    
    def on_string_value_changed(self, field_name: str, value):
        """Handle when a string field value is changed."""
        # Always add to config dictionary when text changes
        self.config_values[field_name] = value
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        # Mark as modified
        self.mark_as_modified()
        
        # Schedule format update
        self.schedule_format_update()
        
        value_str = f"[{', '.join(value)}]" if isinstance(value, list) else f'"{value}"'
        debug_print(f"Set string {field_name} = {value_str}")
        debug_print(f"Current config has {len(self.config_values)} values")
    
    def on_enum_value_changed(self, field_name: str, value: str):
        """Handle when an enum field value is changed."""
        # Always add to config dictionary when enum selection changes
        self.config_values[field_name] = value
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        # Mark as modified
        self.mark_as_modified()
        
        # Schedule format update
        self.schedule_format_update()
        
        debug_print(f"Set enum {field_name} = {value}")
        debug_print(f"Current config has {len(self.config_values)} values")
    
    def on_struct_value_changed(self, field_name: str, struct_dict: dict):
        """Handle when a struct field value is changed."""
        # Add struct dict to config dictionary when any nested field changes
        self.config_values[field_name] = struct_dict
        
        # Update trash button state for this field
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_trash_button_state(True)  # Field is now in config
        
        # Mark as modified
        self.mark_as_modified()
        
        # Schedule format update
        self.schedule_format_update()
        
        debug_print(f"Set struct {field_name} = {struct_dict}")
        debug_print(f"Current config has {len(self.config_values)} values")
    
    def on_field_value_removed(self, field_name: str):
        """Handle when a field value is removed."""
        if field_name in self.config_values:
            del self.config_values[field_name]
            
            # Update trash button state and reset checkbox for this field
            widget = self.get_field_widget(field_name)
            if widget:
                widget.update_trash_button_state(False)  # Field no longer in config
                widget.reset_to_default()  # Reset checkbox to unchecked (default state)
            
            # Mark as modified
            self.mark_as_modified()
            
            # Schedule format update
            self.schedule_format_update()
            
            debug_print(f"Removed {field_name}")
            debug_print(f"Current config has {len(self.config_values)} values")
    
    def get_field_widget(self, field_name: str):
        """Get the widget for a specific field name (returns BooleanFieldWidget, IntegerFieldWidget, StringFieldWidget, or EnumFieldWidget)."""
        for widget in self.field_widgets:
            if widget.field_name == field_name:
                return widget
        return None
    
    def new_file(self):
        """Create a new configuration file."""
        if self.is_modified:
            reply = QMessageBox.question(
                self, 
                'Unsaved Changes',
                'You have unsaved changes. Do you want to save them first?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                if not self.save_file():
                    return  # User cancelled save
            elif reply == QMessageBox.Cancel:
                return
        
        # Clear current configuration
        self.config_values.clear()
        self.current_file_path = ""
        self.is_modified = False
        self.update_window_title()
        
        # Reset all field widgets to default state
        for widget in self.field_widgets:
            widget.reset_to_default()
            widget.update_trash_button_state(False)
    
    def open_file(self):
        """Open an existing .clang-format file."""
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                'Unsaved Changes',
                'You have unsaved changes. Do you want to save them first?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                if not self.save_file():
                    return  # User cancelled save
            elif reply == QMessageBox.Cancel:
                return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Open clang-format file',
            '',
            'Clang-format files (*.clang-format);;YAML files (*.yaml *.yml);;All files (*)'
        )
        
        if file_path:
            try:
                self.load_clang_format_file(file_path)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    'Error Loading File',
                    f'Failed to load file "{file_path}":\n{str(e)}'
                )
    
    def save_file(self) -> bool:
        """Save the current configuration. Returns True if successful."""
        if not self.current_file_path:
            return self.save_as_file()
        
        try:
            self.save_clang_format_file(self.current_file_path)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                'Error Saving File',
                f'Failed to save file "{self.current_file_path}":\n{str(e)}'
            )
            return False
    
    def save_as_file(self) -> bool:
        """Save the current configuration with a new name. Returns True if successful."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Save clang-format file',
            '.clang-format',
            'Clang-format files (*.clang-format);;YAML files (*.yaml *.yml);;All files (*)'
        )
        
        if file_path:
            try:
                self.save_clang_format_file(file_path)
                return True
            except Exception as e:
                QMessageBox.critical(
                    self,
                    'Error Saving File',
                    f'Failed to save file "{file_path}":\n{str(e)}'
                )
                return False
        return False
    
    def load_clang_format_file(self, file_path: str):
        """Load configuration from a .clang-format YAML file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            # Load YAML content
            yaml_content = yaml.safe_load(file)
        
        if not yaml_content:
            yaml_content = {}
        
        # Clear current configuration
        self.config_values.clear()
        
        # Reset all widgets first
        for widget in self.field_widgets:
            widget.reset_to_default()
            widget.update_trash_button_state(False)
        
        # Apply loaded values to widgets
        for key, value in yaml_content.items():
            widget = self.get_field_widget(key)
            if widget:
                widget.set_value(value)
                widget.update_trash_button_state(True)
                self.config_values[key] = value
        
        # Update file tracking
        self.current_file_path = file_path
        self.is_modified = False
        self.update_window_title()
        
        # Schedule format update
        self.schedule_format_update()
        
        debug_print(f"Loaded {len(yaml_content)} configuration values from {file_path}")
    
    def save_clang_format_file(self, file_path: str):
        """Save current configuration to a .clang-format YAML file."""
        # Create YAML content from current config values
        yaml_content = dict(self.config_values)
        
        # Always add Language: Cpp if not specified
        if 'Language' not in yaml_content:
            yaml_content = {'Language': 'Cpp', **yaml_content}
        
        # Write to file in proper YAML format
        with open(file_path, 'w', encoding='utf-8') as file:
            # Write YAML document start
            file.write('---\n')
            
            # Write content using yaml.dump with proper formatting
            yaml_str = yaml.dump(
                yaml_content,
                default_flow_style=False,
                sort_keys=False,  # Preserve order (Python 3.7+ dict order)
                allow_unicode=True,
                width=1000  # Prevent line wrapping for most values
            )
            file.write(yaml_str)
            
            # Write YAML document end
            file.write('...\n')
        
        # Update file tracking
        self.current_file_path = file_path
        self.is_modified = False
        self.update_window_title()
        
        debug_print(f"Saved {len(yaml_content)} configuration values to {file_path}")
    
    def update_window_title(self):
        """Update the window title to show current file and modification status."""
        title = "Clang-Format Configuration UI"
        
        if self.current_file_path:
            file_name = Path(self.current_file_path).name
            title += f" - {file_name}"
        else:
            title += " - Untitled"
        
        if self.is_modified:
            title += " *"
        
        self.setWindowTitle(title)
    
    def mark_as_modified(self):
        """Mark the current configuration as modified."""
        if not self.is_modified:
            self.is_modified = True
            self.update_window_title()
    
    def quit_application(self):
        """Handle application quit with unsaved changes check."""
        if self.is_modified and not self.is_quitting:
            self.is_quitting = True  # Set flag to prevent double dialog
            reply = QMessageBox.question(
                self,
                'Unsaved Changes',
                'You have unsaved changes. Do you want to save them before quitting?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                if not self.save_file():
                    self.is_quitting = False  # Reset flag if save was cancelled
                    return  # User cancelled save, don't quit
            elif reply == QMessageBox.Cancel:
                self.is_quitting = False  # Reset flag if quit was cancelled
                return  # User cancelled quit
        
        # If we get here, it's safe to quit
        self.is_quitting = True  # Ensure flag is set for closeEvent
        self.close()
    
    def closeEvent(self, event):
        """Handle window close event (X button) with unsaved changes check."""
        # If we're already in the quit process, don't show dialog again
        if self.is_quitting:
            event.accept()
            return
            
        if self.is_modified:
            self.is_quitting = True  # Set flag to prevent recursion
            reply = QMessageBox.question(
                self,
                'Unsaved Changes',
                'You have unsaved changes. Do you want to save them before quitting?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                if not self.save_file():
                    self.is_quitting = False  # Reset flag if save was cancelled
                    event.ignore()  # User cancelled save, don't close
                    return
            elif reply == QMessageBox.Cancel:
                self.is_quitting = False  # Reset flag if quit was cancelled
                event.ignore()  # User cancelled quit, don't close
                return
        
        # If we get here, it's safe to close
        event.accept()
    
    def set_clang_format_binary_dialog(self):
        """Show dialog to set the clang-format binary path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Select clang-format binary',
            self.clang_format_binary,
            'Executable files (clang-format*);;All files (*)'
        )
        
        if file_path:
            self.set_clang_format_binary(file_path)
            QMessageBox.information(
                self,
                'Binary Updated',
                f'clang-format binary set to:\n{file_path}\n\nCode preview will update automatically.'
            )
    
    def test_clang_format_binary(self):
        """Test if the clang-format binary is working."""
        try:
            result = subprocess.run([
                self.clang_format_binary, '--version'
            ], capture_output=True, text=True, timeout=5, encoding='utf-8')
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                QMessageBox.information(
                    self,
                    'clang-format Test',
                    f'✓ clang-format is working!\n\nBinary: {self.clang_format_binary}\nVersion: {version_info}'
                )
            else:
                error_msg = result.stderr or "Unknown error"
                QMessageBox.warning(
                    self,
                    'clang-format Test Failed',
                    f'⚠ clang-format returned an error:\n{error_msg}\n\nBinary: {self.clang_format_binary}'
                )
                
        except subprocess.TimeoutExpired:
            QMessageBox.warning(
                self,
                'clang-format Test Failed',
                f'⚠ clang-format process timed out.\n\nBinary: {self.clang_format_binary}'
            )
            
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                'clang-format Not Found',
                f'⚠ clang-format binary not found:\n{self.clang_format_binary}\n\nPlease check the path or install clang-format.'
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                'clang-format Test Error',
                f'⚠ Unexpected error testing clang-format:\n{str(e)}\n\nBinary: {self.clang_format_binary}'
            )
    
    def schedule_format_update(self):
        """Schedule a format update after a short delay to debounce rapid changes."""
        self.format_timer.stop()  # Cancel any pending update
        self.format_timer.start()  # Start new delay
    
    def format_code_preview(self):
        """Format the sample C++ code using current configuration and update the preview."""
        try:
            # Get current sample code
            sample_code = self.get_sample_code()
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.clang-format', delete=False, encoding='utf-8') as config_file:
                # Create YAML content from current config values
                yaml_content = dict(self.config_values)
                
                # Always add Language: Cpp if not specified
                if 'Language' not in yaml_content:
                    yaml_content = {'Language': 'Cpp', **yaml_content}
                
                # Write YAML content
                config_file.write('---\n')
                yaml_str = yaml.dump(
                    yaml_content,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=1000
                )
                config_file.write(yaml_str)
                config_file.write('...\n')
                config_file_path = config_file.name
            
            # Create temporary source file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False, encoding='utf-8') as source_file:
                source_file.write(sample_code)
                source_file_path = source_file.name
            
            # Run clang-format
            try:
                result = subprocess.run([
                    self.clang_format_binary,
                    f'--style=file:{config_file_path}',
                    source_file_path
                ], capture_output=True, text=True, timeout=10, encoding='utf-8')
                
                if result.returncode == 0:
                    # Successfully formatted
                    formatted_code = result.stdout
                    self.code_editor.setPlainText(formatted_code)
                    
                    # Update status in title bar or status area
                    self.update_format_status("✓ Code formatted successfully")
                else:
                    # Error during formatting
                    error_msg = result.stderr or "Unknown formatting error"
                    self.update_format_status(f"⚠ Formatting error: {error_msg[:100]}")
                    print(f"clang-format error: {error_msg}")
                    
                    # Show original code with error annotation
                    error_annotation = f"// Formatting error: {error_msg}\n\n"
                    self.code_editor.setPlainText(error_annotation + sample_code)
                    
            except subprocess.TimeoutExpired:
                self.update_format_status("⚠ Formatting timeout")
                print("clang-format process timed out")
                self.code_editor.setPlainText("// Formatting timed out\n\n" + sample_code)
                
            except FileNotFoundError:
                self.update_format_status(f"⚠ clang-format not found: {self.clang_format_binary}")
                print(f"clang-format binary not found: {self.clang_format_binary}")
                self.code_editor.setPlainText(f"// clang-format not found: {self.clang_format_binary}\n\n" + sample_code)
                
            except Exception as e:
                self.update_format_status(f"⚠ Error: {str(e)[:50]}")
                print(f"Unexpected error during formatting: {e}")
                self.code_editor.setPlainText(f"// Error: {str(e)}\n\n" + sample_code)
            
            # Clean up temporary files
            try:
                Path(config_file_path).unlink()
                Path(source_file_path).unlink()
            except Exception as e:
                print(f"Warning: Could not clean up temporary files: {e}")
                
        except Exception as e:
            print(f"Error in format_code_preview: {e}")
            self.update_format_status(f"⚠ Preview error: {str(e)[:50]}")
    
    def update_format_status(self, message: str):
        """Update the formatting status in the UI."""
        debug_print(f"Format status: {message}")
        
        # Update status label with appropriate styling
        if hasattr(self, 'format_status_label'):
            self.format_status_label.setText(message)
            
            # Style based on message type
            if message.startswith("✓"):
                # Success
                self.format_status_label.setStyleSheet("""
                    QLabel {
                        font-size: 12px;
                        color: #27ae60;
                        padding: 5px 10px;
                        background-color: #d5f4e6;
                        border-radius: 3px;
                        border: 1px solid #27ae60;
                    }
                """)
            elif message.startswith("⚠"):
                # Warning/Error
                self.format_status_label.setStyleSheet("""
                    QLabel {
                        font-size: 12px;
                        color: #e74c3c;
                        padding: 5px 10px;
                        background-color: #fdf2f2;
                        border-radius: 3px;
                        border: 1px solid #e74c3c;
                    }
                """)
            else:
                # Default/Info
                self.format_status_label.setStyleSheet("""
                    QLabel {
                        font-size: 12px;
                        color: #3498db;
                        padding: 5px 10px;
                        background-color: #ebf3fd;
                        border-radius: 3px;
                        border: 1px solid #3498db;
                    }
                """)
    
    def set_clang_format_binary(self, binary_path: str):
        """Set the path to the clang-format binary and trigger a format update."""
        self.clang_format_binary = binary_path
        self.schedule_format_update()


def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Clang-Format Configuration UI')
    parser.add_argument(
        '--clang-format-binary', 
        default='clang-format',
        help='Path to clang-format binary (default: clang-format from PATH)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose debug output'
    )
    args = parser.parse_args()
    
    # Set global verbose flag
    global VERBOSE_MODE
    VERBOSE_MODE = args.verbose
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Clang-Format UI")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Development Tools")
    
    # Create and show main window
    window = ClangFormatUI(clang_format_binary=args.clang_format_binary)
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
