
"""
MartianMap - GIS Layer Manager
"""

from pathlib import Path

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer
)


class LayerManager:

    def __init__(self, map_canvas):

        self.map_canvas = map_canvas
        self.project = QgsProject.instance()

    def load_layer(self, file_path, name=None):
        """Load a raster or vector dataset."""

        path = Path(file_path)

        if not path.exists():
            print("File does not exist:", file_path)
            return None

        layer_name = name or path.stem
        extension = path.suffix.lower()

        # Load raster datasets.
        if extension in [".tif", ".tiff", ".vrt", ".img"]:

            layer = QgsRasterLayer(
                str(path),
                layer_name
            )

        # Load vector datasets.
        else:

            layer = QgsVectorLayer(
                str(path),
                layer_name,
                "ogr"
            )

        # Validate the dataset.
        if not layer.isValid():
            print("Failed to load layer:", file_path)
            return None

        # Add the layer to the project.
        self.project.addMapLayer(layer)

        self.refresh_canvas()

        return layer

    def remove_layer(self, layer_id):
        """Remove a layer from the project."""

        self.project.removeMapLayer(layer_id)

        self.refresh_canvas()

    def get_layers(self):
        """Return all currently loaded layers."""

        return list(
            self.project.mapLayers().values()
        )

    def refresh_canvas(self):
        """Refresh the displayed map."""

        layers = list(
            self.project.mapLayers().values()
        )

        self.map_canvas.setLayers(layers)
        self.map_canvas.refresh()
