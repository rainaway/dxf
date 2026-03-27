#!/usr/bin/env python3
"""
Drawing Editor - Main Entry Point

A PyQt5-based 2D CAD drawing editor with DXF support.
"""

import sys
from PyQt5.QtWidgets import QApplication
from drawing_editor.ui.main_window import CadWindow


def main() -> int:
    """Run the drawing editor application."""
    app = QApplication(sys.argv)
    window = CadWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
