
"""
MartianMap - Main application window
"""

from qgis.PyQt.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel
)

from map_canvas import MapCanvas
from layer_manager import LayerManager
from map_controls import MapControls


class MartianMapWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("MartianMap")
        self.resize(1200, 800)

        # Initialize map components.
        self.map_canvas = MapCanvas()
        self.layer_manager = LayerManager(self.map_canvas)
        self.map_controls = MapControls(self.map_canvas)

        self.create_interface()

    def create_interface(self):
        # Main application layout.
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)

        # Sidebar.
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)

        title = QLabel("MartianMap")
        sidebar_layout.addWidget(title)

        sidebar_layout.addWidget(
            QLabel("Map Layers")
        )

        sidebar_layout.addWidget(self.map_controls)
        sidebar_layout.addStretch()

        sidebar.setMinimumWidth(220)

        # Add sidebar and map canvas.
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.map_canvas, 1)

        self.setCentralWidget(central_widget)

        self.statusBar().showMessage(
            "Ready - No map layers loaded"
        )

    def load_example_layer(self, file_path):
        """Load a dataset into the map."""

        layer = self.layer_manager.load_layer(file_path)

        if layer is not None:
            self.statusBar().showMessage(
                "Loaded: " + layer.name()
            )
        else:
            self.statusBar().showMessage(
                "Failed to load map layer"
            )
