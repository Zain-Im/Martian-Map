
"""
MartianMap - Application entry point
"""

import sys

from qgis.core import QgsApplication
from app import MartianMapWindow


def main():
    # Initialize QGIS without launching its desktop interface.
    qgs = QgsApplication([], True)
    qgs.initQgis()

    # Create and display our application.
    window = MartianMapWindow()
    window.show()

    # Start the application event loop.
    exit_code = qgs.exec()

    # Clean up QGIS resources.
    qgs.exitQgis()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
