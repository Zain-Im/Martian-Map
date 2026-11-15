
"""
MartianMap - GIS Layer Manager
"""

import logging
logger = logging.getLogger("martian_map.layer_manager")


from pathlib import Path

from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsFillSymbol,
    QgsSingleBandPseudoColorRenderer,
    QgsRasterShader,
    QgsColorRampShader
)


class LayerManager:

    def __init__(self, map_canvas):

        self.map_canvas = map_canvas
        self.project = QgsProject.instance()

        # Store loaded layers by their names.
        self.layers = {}
        logger.info("Layer manager initialized")

    def load_layer(self, file_path, name=None, display=False):
        """Load a raster or vector dataset."""

        logger.info("Loading layer %s: %s", name, file_path)
        path = Path(file_path)

        if not path.exists():
            logger.warning("Layer file missing: %s", file_path)
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
            logger.error("Layer invalid: %s | %s", file_path, layer.error().summary())
            return None

        # Add the layer to the QGIS project.
        self.project.addMapLayer(layer)

        # Store a reference to the layer.
        self.layers[layer_name] = layer
        # Apply elevation symbology.
        if layer_name == "Elevation":
            self.apply_elevation_symbology(layer)

        # Apply geology symbology.
        if layer_name == "Geology":
            self.apply_geology_symbology(layer)

        if layer_name == "Traversability":
            self.apply_traversability_symbology(layer)

        if display:
            self.show_layers([layer_name])

        logger.info("Layer ready: %s | CRS=%s", layer_name, layer.crs().description())
        return layer
    
    def apply_elevation_symbology(self, layer):
        """Apply the custom elevation colour gradient."""

        # Elevation range from the original QGIS symbology.
        minimum = -2651.6625977
        maximum = -2391.2768555

        # Extracted colour stops from the QGIS style.
        colors = [
            "#000000",
            "#263B28",
            "#355E36",
            "#4E8242",
            "#82A650",
            "#C2C35B",
            "#E5CB55",
            "#DFA74A",
            "#BB8140",
            "#966039",
            "#A54830",
            "#BB3028",
            "#D73D30"
        ]

        items = []

        for i, color in enumerate(colors):

            value = minimum + (maximum - minimum) * i / (len(colors) - 1)

            item = QgsColorRampShader.ColorRampItem(
                value,
                QColor(color),
                f"{value:.4f}"
            )

            items.append(item)

        # Create the interpolated colour ramp.
        ramp_shader = QgsColorRampShader()
        ramp_shader.setColorRampType(
            QgsColorRampShader.Interpolated
        )
        ramp_shader.setColorRampItemList(items)

        # Create the raster shader.
        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(ramp_shader)

        # Create the raster renderer.
        renderer = QgsSingleBandPseudoColorRenderer(
            layer.dataProvider(),
            1,
            raster_shader
        )

        renderer.setClassificationMin(minimum)
        renderer.setClassificationMax(maximum)

        layer.setRenderer(renderer)
        layer.triggerRepaint()

        logger.info("Elevation symbology applied")

    def apply_geology_symbology(self, layer):
        """Apply categorized colours based on geological names."""
        logger.info("Building geology categories")

        field_name = "name"

        # Hardcoded geological colour palette.

        colors = [
            "#A94F42",  # Rust red
            "#D18A36",  # Ochre
            "#8D713C",  # Earth brown
            "#C5A36B",  # Sand
            "#A0A34D",  # Moss
            "#547D45",  # Forest green
            "#9566A6",  # Purple
            "#667A91",  # Slate blue
            "#91A64B",  # Olive
            "#367F78",  # Teal
            "#397AAB",  # Blue
            "#625B9B",  # Indigo
            "#B45D83",  # Rose
            "#C16B58",  # Terracotta
            "#8B806C",  # Taupe
            "#795A70"   # Plum
        ]


        # Check that the field exists.
        if layer.fields().indexFromName(field_name) == -1:
            logger.warning("Geology styling skipped: name field missing")
            return

        # Collect unique geological names.
        names = set()

        for feature in layer.getFeatures():

            name = feature[field_name]

            if name is not None:
                names.add(name)

        # Sort names for consistent colour assignments.
        names = sorted(names)
        logger.info("Geology categories found: %s", len(names))

        categories = []

        # Assign a hardcoded colour to each name.
        for i, name in enumerate(names):

            color = colors[i % len(colors)]

            symbol = QgsFillSymbol.createSimple({
                "color": color,
                "outline_color": "#5A4036",
                "outline_width": "0.15"
            })

            category = QgsRendererCategory(
                name,
                symbol,
                str(name)
            )

            categories.append(category)

        # Apply categorized symbology.
        renderer = QgsCategorizedSymbolRenderer(
            field_name,
            categories
        )

        layer.setRenderer(renderer)


    def apply_traversability_symbology(self, layer):

        shader = QgsColorRampShader()
        shader.setColorRampType(QgsColorRampShader.Interpolated)
        shader.setMinimumValue(0)
        shader.setMaximumValue(1)

        colors = [
            QgsColorRampShader.ColorRampItem(
                0.0, QColor("#559455"), "0.0000"
            ),
            QgsColorRampShader.ColorRampItem(
                0.5, QColor("#F7E164"), "0.5000"
            ),
            QgsColorRampShader.ColorRampItem(
                0.9999, QColor("#EF9819"), "0.9999"
            ),
            QgsColorRampShader.ColorRampItem(
                1.0, QColor("#A80407"), "1.0000"
            )
        ]

        shader.setColorRampItemList(colors)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(shader)

        renderer = QgsSingleBandPseudoColorRenderer(
            layer.dataProvider(),
            1,
            raster_shader
        )

        renderer.setClassificationMin(0)
        renderer.setClassificationMax(1)

        layer.setRenderer(renderer)
        layer.triggerRepaint()


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
        logger.info("Displaying layers: %s", ", ".join(layer_names))

        visible_layers = []

        for name in layer_names:

            if name in self.layers:
                visible_layers.append(self.layers[name])

        self.map_canvas.setLayers(visible_layers)
        self.map_canvas.refresh()

    def refresh_canvas(self):
        """Refresh the currently displayed layers."""

        self.map_canvas.refresh()
