

"""
MartianMap - Map display
"""

import logging
logger = logging.getLogger("martian_map.map_canvas")


from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import pyqtSignal, Qt, QPoint
from qgis.core import QgsProject, QgsRectangle, QgsWkbTypes, QgsPointXY
from qgis.gui import (
    QgsMapCanvas,
    QgsMapTool,
    QgsMapToolEmitPoint,
    QgsVertexMarker,
    QgsRubberBand
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

    WAYPOINT_COLOR = "#E9A96B"
    ASTRONAUT_COLOR = "#45D6E8"
    SELECTED_COLOR = "#F4D35E"
    MARKER_OUTLINE = "#111923"

    # Signal emitted when the user selects a location.
    location_picked = pyqtSignal(object)
    # Signal emitted when the user selects a saved waypoint.
    waypoint_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing map canvas, rendering cache, and selection tools")

        self.setCanvasColor(QColor("#252B32"))
        self.enableAntiAliasing(True)
        self.setCachingEnabled(True)
        self.setProject(QgsProject.instance())
        # Store the temporary and saved waypoint markers.
        self.preview_marker = None
        self.waypoint_markers = []
        self.selected_waypoint_marker = None
        self.astronaut_marker = None
        self.route_band = None

        # Create the map interaction tools.
        self.pan_tool = WaypointPanTool(self)
        self.point_tool = QgsMapToolEmitPoint(self)

        # Connect the point tool to the click handler.
        self.point_tool.canvasClicked.connect(
            self.on_map_clicked
        )

        # Enable panning by default.
        self.setMapTool(self.pan_tool)
        self._initial_render_logged = False
        self.mapCanvasRefreshed.connect(self._log_render_complete)
        logger.info("Map canvas ready; pan and waypoint tools connected")

    def _log_render_complete(self):
        if not self._initial_render_logged:
            logger.info("Initial map render completed")
            self._initial_render_logged = True
        else:
            logger.debug("Map render completed")

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
        logger.debug("Selecting waypoint: %s", waypoint.get("name"))

        # Reset the previously selected marker.
        if self.selected_waypoint_marker is not None:

            previous = next((p for m, p in self.waypoint_markers
                             if m is self.selected_waypoint_marker), {})
            self.style_marker(self.selected_waypoint_marker,
                              previous.get("color", self.WAYPOINT_COLOR))

        # Use the same selection highlight for user and permanent waypoints.
        self.style_marker(marker, self.SELECTED_COLOR, size=20)

        self.selected_waypoint_marker = marker

        # Send the selected waypoint information to app.py.
        self.waypoint_selected.emit(waypoint)

    @staticmethod
    def style_marker(marker, color, size=16, shape=QgsVertexMarker.ICON_RHOMBUS):
        marker.setIconType(shape)
        marker.setColor(QColor(MapCanvas.MARKER_OUTLINE))
        marker.setFillColor(QColor(color))
        marker.setIconSize(size)
        marker.setPenWidth(2)

    def add_waypoint_marker(self, waypoint):
        """Insert a saved waypoint without using the user's preview marker."""
        marker = QgsVertexMarker(self)
        self.style_marker(marker, waypoint.get("color", self.WAYPOINT_COLOR))
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

        self.style_marker(self.astronaut_marker, self.ASTRONAUT_COLOR,
                          size=22, shape=QgsVertexMarker.ICON_CIRCLE)

        self.astronaut_marker.setCenter(point)
        self.astronaut_marker.show()

        self.refresh()
        
    def show_waypoint_preview(self, point):

        # Create the preview marker if it doesn't exist.
        if self.preview_marker is None:

            self.preview_marker = QgsVertexMarker(self)

            self.style_marker(self.preview_marker, self.WAYPOINT_COLOR)

        # Move the preview marker to the selected location.
        self.preview_marker.setCenter(point)
        self.preview_marker.show()

    def draw_route(self, path):

        # Remove the previous route.
        self.clear_route()

        # Create a new route line.
        self.route_band = QgsRubberBand(
            self,
            QgsWkbTypes.LineGeometry
        )

        self.route_band.setColor(QColor("#174A78"))
        self.route_band.setWidth(3)
        self.route_band.setLineStyle(Qt.SolidLine)

        # Draw the path.
        for x, y in path:
            self.route_band.addPoint(
                QgsPointXY(x, y),
                False
            )

        self.route_band.show()
        self.refresh()


    def zoom_to_route(self, path):
        """Fit all route points with padding, including degenerate routes."""
        if not path:
            return
        min_x = max_x = path[0][0]
        min_y = max_y = path[0][1]
        for x, y in path:
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
        # The map uses metres; keep at least a 20 m view on either axis.
        padding = max(max_x - min_x, max_y - min_y) * 0.15
        pad_x = max(padding, (20 - (max_x - min_x)) / 2)
        pad_y = max(padding, (20 - (max_y - min_y)) / 2)
        self.setExtent(QgsRectangle(
            min_x - pad_x, min_y - pad_y,
            max_x + pad_x, max_y + pad_y,
        ))
        self.refresh()

    def clear_route(self):

        if self.route_band is not None:
            self.route_band.reset(QgsWkbTypes.LineGeometry)
            self.route_band = None

        self.refresh()
