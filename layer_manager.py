
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

        # Store loaded layers by their names.
        self.layers = {}

    def load_layer(self, file_path, name=None, display=False):
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
                layer_name,
                "gdal"
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

        # Add the layer to the QGIS project.
        self.project.addMapLayer(layer)

        # Store a reference to the layer.
        self.layers[layer_name] = layer

        if display:
            self.show_layers([layer_name])

        return layer

    def remove_layer(self, layer_id):
        """Remove a layer from the project."""

        self.project.removeMapLayer(layer_id)

        # Remove the layer from our dictionary.
        for name, layer in list(self.layers.items()):

            if layer.id() == layer_id:
                del self.layers[name]

        self.refresh_canvas()

    def get_layers(self):
        """Return all currently loaded layers."""

        return list(self.layers.values())

    def get_layer(self, name):
        """Retrieve a layer by its name."""

        return self.layers.get(name)

    def show_layers(self, layer_names):
        """Display only the requested layers."""

        visible_layers = []

        for name in layer_names:

            if name in self.layers:
                visible_layers.append(self.layers[name])

        self.map_canvas.setLayers(visible_layers)
        self.map_canvas.refresh()

    def refresh_canvas(self):
        """Refresh the currently displayed layers."""

        self.map_canvas.refresh()
