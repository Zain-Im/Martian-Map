
"""
MartianMap - Map display
"""

from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapCanvas
from qgis.core import QgsProject


class MapCanvas(QgsMapCanvas):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set the map background.
        self.setCanvasColor(QColor("white"))

        # Enable smoother rendering.
        self.enableAntiAliasing(True)

        # Connect the canvas to the QGIS project.
        self.setProject(QgsProject.instance())

        # Initial map extent will be configured
        # once the Martian datasets are selected.
