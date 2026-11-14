
"""
MartianMap - Map Navigation Controls
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton
)


class MapControls(QWidget):

    def __init__(self, map_canvas, parent=None):
        super().__init__(parent)

        self.map_canvas = map_canvas

        self.create_controls()

    def create_controls(self):

        layout = QVBoxLayout(self)

        # Zoom in button.
        zoom_in = QPushButton("Zoom In")
        zoom_in.clicked.connect(self.zoom_in)

        # Zoom out button.
        zoom_out = QPushButton("Zoom Out")
        zoom_out.clicked.connect(self.zoom_out)

        # Reset map extent button.
        full_extent = QPushButton("Full Extent")
        full_extent.clicked.connect(self.zoom_full)

        layout.addWidget(zoom_in)
        layout.addWidget(zoom_out)
        layout.addWidget(full_extent)

    def zoom_in(self):

        self.map_canvas.zoomIn()
        self.map_canvas.refresh()

    def zoom_out(self):

        self.map_canvas.zoomOut()
        self.map_canvas.refresh()

    def zoom_full(self):

        self.map_canvas.zoomToFullExtent()
        self.map_canvas.refresh()
