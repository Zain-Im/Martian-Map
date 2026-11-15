

"""
MartianMap - Map display
"""

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import pyqtSignal, Qt, QPoint
from qgis.core import QgsProject, QgsRectangle
from qgis.gui import (
    QgsMapCanvas,
    QgsMapTool,
    QgsMapToolEmitPoint,
    QgsVertexMarker
)

class WaypointPanTool(QgsMapTool):

    def __init__(self, canvas):
        super().__init__(canvas)

        self.canvas = canvas
        self.start_position = None
        self.start_extent = None
        self.dragging = False

        self.canvas.setCursor(Qt.OpenHandCursor)

    def canvasPressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        # Record the starting mouse position and map extent.
        self.start_position = event.pos()
        self.start_extent = self.canvas.extent()

        self.dragging = False

    def canvasMoveEvent(self, event):

        if self.start_position is None:
            return

        if not (event.buttons() & Qt.LeftButton):
            return

        # Calculate the mouse movement.
        dx = event.pos().x() - self.start_position.x()
        dy = event.pos().y() - self.start_position.y()

        # Only start panning after the mouse has moved.
        if abs(dx) > 5 or abs(dy) > 5:
            self.dragging = True

        if self.dragging:

            self.canvas.setCursor(Qt.ClosedHandCursor)

            # Convert pixel movement into map coordinates.
            scale = self.canvas.mapSettings().mapUnitsPerPixel()

            x_offset = dx * scale
            y_offset = dy * scale

            # Move the map in the direction of the mouse.
            new_extent = QgsRectangle(
                self.start_extent.xMinimum() - x_offset,
                self.start_extent.yMinimum() + y_offset,
                self.start_extent.xMaximum() - x_offset,
                self.start_extent.yMaximum() + y_offset
            )

            self.canvas.setExtent(new_extent)

    def canvasReleaseEvent(self, event):

        if self.start_position is None:
            return

        if not self.dragging:

            # Check whether a saved waypoint was clicked.
            click_position = event.pos()

            for marker, waypoint in self.canvas.waypoint_markers:

                marker_position = (
                    self.canvas.getCoordinateTransform().transform(
                        marker.center()
                    )
                )

                marker_position = QPoint(
                    round(marker_position.x()),
                    round(marker_position.y())
                )

                distance = (
                    click_position - marker_position
                ).manhattanLength()

                if distance <= 20:

                    self.canvas.select_waypoint(
                        marker,
                        waypoint
                    )

                    break
        if self.dragging:
            self.canvas.refresh()

        # Reset the interaction state.
        self.start_position = None
        self.start_extent = None
        self.dragging = False

        self.canvas.setCursor(Qt.OpenHandCursor)
        
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
        self.astronaut_marker = None

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

    def remove_waypoint_marker(self, waypoint):
        if waypoint.get("permanent", False):
            return
        for marker, saved_waypoint in self.waypoint_markers:
            if saved_waypoint == waypoint:
                self.scene().removeItem(marker)
                self.waypoint_markers.remove((marker, saved_waypoint))
                break

        self.selected_waypoint_marker = None
        self.refresh()

    def select_waypoint(self, marker, waypoint):

        # Reset the previously selected marker.
        if self.selected_waypoint_marker is not None:

            previous = next((p for m, p in self.waypoint_markers
                             if m is self.selected_waypoint_marker), {})
            color = QColor(previous.get("color", "#E9A96B"))
            self.selected_waypoint_marker.setColor(color)
            self.selected_waypoint_marker.setFillColor(color)

            self.selected_waypoint_marker.setIconSize(14)
            self.selected_waypoint_marker.setPenWidth(3)

        # Highlight the newly selected marker.
        color = waypoint.get("color", "#E9A96B") if waypoint.get("permanent") else "#F4D35E"
        marker.setColor(QColor(color))
        marker.setFillColor(QColor(color))
        marker.setIconSize(20)
        marker.setPenWidth(4)

        self.selected_waypoint_marker = marker

        # Send the selected waypoint information to app.py.
        self.waypoint_selected.emit(waypoint)

    def add_waypoint_marker(self, waypoint):
        """Insert a saved waypoint without using the user's preview marker."""
        marker = QgsVertexMarker(self)
        color = QColor(waypoint.get("color", "#E9A96B"))
        marker.setColor(color)
        marker.setFillColor(color)
        marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
        marker.setIconSize(14)
        marker.setPenWidth(3)
        marker.setCenter(waypoint["point"])
        marker.show()
        self.waypoint_markers.append((marker, waypoint))
        return marker

    def set_astronaut_marker(self, point):

        # Remove the previous astronaut marker.
        if self.astronaut_marker is not None:
            self.scene().removeItem(self.astronaut_marker)

        # Create a new astronaut marker.
        self.astronaut_marker = QgsVertexMarker(self)

        self.astronaut_marker.setColor(QColor("#45D6E8"))
        self.astronaut_marker.setFillColor(QColor("#45D6E8"))
        self.astronaut_marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
        self.astronaut_marker.setIconSize(22)
        self.astronaut_marker.setPenWidth(4)

        self.astronaut_marker.setCenter(point)
        self.astronaut_marker.show()

        self.refresh()
        
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
