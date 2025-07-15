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
    QScrollArea, QTextEdit, QSplitter, QLabel, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ClangFormatUI(QMainWindow):
    """Main window for the Clang-Format UI application."""
    
    def __init__(self):
        super().__init__()
        self.format_data: Dict[str, Any] = {}
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
        
        # Placeholder content
        placeholder_label = QLabel("Configuration options will be loaded here...")
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
        
        scroll_area.setWidget(self.config_widget)
        left_layout.addWidget(scroll_area)
        
        parent.addWidget(left_frame)
        
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
            
            # TODO: Create UI elements from format_data
            # This will be implemented in the next step
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading format data: {e}")


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
