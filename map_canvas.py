

"""
MartianMap - Map display
"""

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import pyqtSignal, Qt, QPoint

from qgis.gui import (
    QgsMapCanvas,
    QgsMapToolPan,
    QgsMapToolEmitPoint,
    QgsVertexMarker
)

from qgis.core import QgsProject

class WaypointPanTool(QgsMapToolPan):

    def __init__(self, canvas):
        super().__init__(canvas)

        self.canvas = canvas
        self.press_position = None

    def canvasPressEvent(self, event):

        self.press_position = event.pos()

        super().canvasPressEvent(event)

    def canvasReleaseEvent(self, event):

        # Check whether the user clicked rather than dragged.
        is_click = False

        if self.press_position is not None:

            distance = (
                event.pos() - self.press_position
            ).manhattanLength()

            if distance < 5 and event.button() == Qt.LeftButton:
                is_click = True

        # Preserve the normal pan behavior.
        super().canvasReleaseEvent(event)

        if not is_click:
            return

        # Check whether the click was close to a saved waypoint.
        click_position = event.pos()

        for marker, waypoint in self.canvas.waypoint_markers:

            marker_position = self.canvas.getCoordinateTransform().transform(
                marker.center()
            )

            marker_position = QPoint(
                round(marker_position.x()),
                round(marker_position.y())
            )
            distance = (
                click_position - marker_position
            ).manhattanLength()

            if distance <= 20:

                self.canvas.select_waypoint(marker, waypoint)
                break

class MapCanvas(QgsMapCanvas):

    # Signal emitted when the user selects a location.
    location_picked = pyqtSignal(object)
    # Signal emitted when the user selects a saved waypoint.
    waypoint_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setCanvasColor(QColor("#252B32"))
        self.enableAntiAliasing(True)
        self.setCachingEnabled(True)
        self.setProject(QgsProject.instance())
        # Store the temporary and saved waypoint markers.
        self.preview_marker = None
        self.waypoint_markers = []
        self.selected_waypoint_marker = None

        # Create the map interaction tools.
        self.pan_tool = WaypointPanTool(self)
        self.point_tool = QgsMapToolEmitPoint(self)

        # Connect the point tool to the click handler.
        self.point_tool.canvasClicked.connect(
            self.on_map_clicked
        )

        # Enable panning by default.
        self.setMapTool(self.pan_tool)

    def start_waypoint_selection(self):

        # Switch from panning to location selection.
        self.setMapTool(self.point_tool)

    def on_map_clicked(self, point, button):

        # Send the selected coordinates to the main window.
        self.location_picked.emit(point)

        # Return to panning mode.
        self.setMapTool(self.pan_tool)

    def save_waypoint_marker(self, waypoint):

        if self.preview_marker is None:
            return

        # Keep the marker as a permanent waypoint.
        self.waypoint_markers.append(
            (self.preview_marker, waypoint)
        )

        # Allow a new preview marker to be created.
        self.preview_marker = None

    def select_waypoint(self, marker, waypoint):

        # Reset the previously selected marker.
        if self.selected_waypoint_marker is not None:

            self.selected_waypoint_marker.setColor(
                QColor("#E9A96B")
            )

            self.selected_waypoint_marker.setFillColor(
                QColor("#E9A96B")
            )

            self.selected_waypoint_marker.setIconSize(14)
            self.selected_waypoint_marker.setPenWidth(3)

        # Highlight the newly selected marker.
        marker.setColor(QColor("#F4D35E"))
        marker.setFillColor(QColor("#F4D35E"))
        marker.setIconSize(20)
        marker.setPenWidth(4)

        self.selected_waypoint_marker = marker

        # Send the selected waypoint information to app.py.
        self.waypoint_selected.emit(waypoint)

    def show_waypoint_preview(self, point):

        # Create the preview marker if it doesn't exist.
        if self.preview_marker is None:

            self.preview_marker = QgsVertexMarker(self)

            self.preview_marker.setColor(QColor("#E9A96B"))
            self.preview_marker.setFillColor(QColor("#E9A96B"))
            self.preview_marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
            self.preview_marker.setIconSize(14)
            self.preview_marker.setPenWidth(3)

        # Move the preview marker to the selected location.
        self.preview_marker.setCenter(point)
        self.preview_marker.show()