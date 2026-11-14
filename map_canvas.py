

"""
MartianMap - Map display
"""

from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapCanvas, QgsMapToolPan
from qgis.core import QgsProject, QgsRasterLayer


class MapCanvas(QgsMapCanvas):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set the map background.
        self.setCanvasColor(QColor("#252B32"))

        # Enable smoother rendering.
        self.enableAntiAliasing(True)

        # Connect the canvas to the QGIS project.
        self.setProject(QgsProject.instance())

        # Enable mouse-drag panning.
        self.pan_tool = QgsMapToolPan(self)
        self.setMapTool(self.pan_tool)

        self.setCachingEnabled(True)

    def load_raster(self, file_path):

        # Create the raster layer.
        layer = QgsRasterLayer(file_path, "Mars Elevation", "gdal")

        # Check whether the raster loaded successfully.
        if not layer.isValid():
            raise RuntimeError("Failed to load elevation raster.")

        # Add the layer to the QGIS project.
        project = QgsProject.instance()
        project.setCrs(layer.crs())
        project.addMapLayer(layer)

        # Display the raster on the map canvas.
        self.setLayers([layer])

        # Zoom to the raster's extent.
        self.setExtent(layer.extent())

        # Refresh the canvas.
        self.refresh()
