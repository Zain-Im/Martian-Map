"""
MartianMap - Primary Application 
"""

from qgis.PyQt.QtWidgets import (
    QMainWindow,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QLineEdit,
    QScrollArea
)

import os
import numpy as np
from pathlib import Path

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsCoordinateTransform, 
    QgsProject, 
    QgsCategorizedSymbolRenderer,
    QgsCoordinateTransform,
    QgsProject,
    QgsGeometry,
    QgsPointXY
)

from layer_manager import LayerManager
from map_canvas import MapCanvas


class MartianMapWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Martian Map")
        self.resize(1440, 900)
        self.waypoints = []
        self.pending_waypoint = None
        self.astronaut_position = None
        self.placement_mode = None

        self.setStyleSheet("""
            QMainWindow {
                background-color: #111923;
            }

            QWidget {
                color: #E6EDF3;
                font-family: Segoe UI;
                font-size: 13px;
            }

            QFrame#topBar {
                background-color: #1B2938;
                border-bottom: 1px solid #34465A;
            }

            QFrame#sidebar {
                background-color: #1B2938;
                border-right: 1px solid #34465A;
            }

            QFrame#mapPanel {
                background-color: #111923;
            }

            QLabel#appTitle {
                font-size: 20px;
                font-weight: bold;
                color: #E9A96B;
            }

            QLabel#sectionTitle {
                font-size: 14px;
                font-weight: bold;
                color: #E9A96B;
            }

            QLabel#secondaryText {
                color: #9BAFC2;
            }

            QPushButton {
                background-color: #293B4F;
                border: 1px solid #40566D;
                border-radius: 5px;
                padding: 8px 12px;
            }

            QPushButton:hover {
                background-color: #3A526B;
            }

            QPushButton:pressed {
                background-color: #172536;
            }
            QLineEdit {
                background-color: #293B4F;
                color: #E6EDF3;
                border: 1px solid #40566D;
                border-radius: 5px;
                padding: 7px;
            }

            QLineEdit:focus {
                border: 1px solid #E9A96B;
            }
        """)

        # Main container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create top toolbar
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)

        # Main content area
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        main_layout.addLayout(content_layout)

        # Left sidebar
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar)

        # Map canvas
        map_panel = self.create_map_panel()
        content_layout.addWidget(map_panel, 1)
        
        # Create the GIS layer manager.
        self.layer_manager = LayerManager(self.map_canvas)

        # Create the waypoint information panel.
        self.info_panel = self.create_info_panel()
        content_layout.addWidget(self.info_panel)

        # Hide the information panel until a waypoint is selected.
        self.info_panel.hide()
        
        # Connect waypoint selection.
        self.waypoint_button.clicked.connect(
            self.start_waypoint_selection
        )

        self.map_canvas.location_picked.connect(
            self.handle_map_location_picked
        )

        self.map_canvas.waypoint_selected.connect(
            self.handle_saved_waypoint_selection
        )
        self.selected_waypoint = None
        # Bottom status bar
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)

        # Load the initial Mars elevation map.
        self.load_initial_map()
    
    def load_initial_map(self):

        project_dir = Path(__file__).resolve().parent.parent

        data_dir = os.path.join(
            project_dir,
            "data",
            "raw"
        )

        elevation_path = os.path.join(
            data_dir,
            "elevation_map.tif"
        )

        optical_path = os.path.join(
            data_dir,
            "optical_map.tif"
        )

        geology_path = os.path.join(
            data_dir,
            "geology_map.gpkg"
        )

        traversability_path = os.path.join(
            data_dir, "Traversability.tif"
        )

        # Load the elevation raster.
        elevation_layer = self.layer_manager.load_layer(
            elevation_path,
            "Elevation"
        )
        if elevation_layer is not None:
            QgsProject.instance().setCrs(elevation_layer.crs())

        # Load the optical raster.
        optical_layer = self.layer_manager.load_layer(
            optical_path,
            "Optical"
        )
        # Load the geology map.
        geology_layer = self.layer_manager.load_layer(
            geology_path,
            "Geology"
        )

        traversability_layer = self.layer_manager.load_layer(
            traversability_path,
            "Traversability"
        )

        # Display elevation by default.
        if elevation_layer is not None:

            self.layer_manager.show_layers(["Elevation"])

            self.map_canvas.setExtent(
                elevation_layer.extent()
            )

            self.status_label.setText("Elevation map loaded")

        else:
            self.status_label.setText("Failed to load elevation map")

        if optical_layer is None:
            print("Optical map could not be loaded.")

        if geology_layer is None:
            print("Geology map could not be loaded.")

        if traversability_layer is None:
            print("Traversability map could not be loaded.")

    def start_astronaut_selection(self):

        self.placement_mode = "astronaut"
        self.map_canvas.start_waypoint_selection()

        self.status_label.setText(
            "Select astronaut location on the map"
        )


    def handle_map_location_picked(self, point):

        if self.placement_mode == "astronaut":

            self.handle_astronaut_location(point)

        elif self.placement_mode == "waypoint":

            self.handle_waypoint_location(point)

        self.placement_mode = None

    def handle_astronaut_location(self, point):
        # Get the selected coordinates.
        x = point.x()
        y = point.y()

        # Retrieve the elevation layer.
        elevation_layer = self.layer_manager.get_layer("Elevation")

        elevation = None

        if elevation_layer is not None:

            # Convert the point to the elevation layer CRS.
            canvas_crs = self.map_canvas.mapSettings().destinationCrs()

            transform = QgsCoordinateTransform(
                canvas_crs,
                elevation_layer.crs(),
                QgsProject.instance()
            )

            elevation_point = transform.transform(point)

            # Sample the elevation raster.
            provider = elevation_layer.dataProvider()

            value, success = provider.sample(elevation_point, 1)

            if success:
                elevation = value

        # Store the astronaut position separately from waypoints.
        self.astronaut_position = {
            "point": point,
            "x": x,
            "y": y,
            "elevation": elevation
        }

        self.astronaut_status.setText("Location set")

        # Display the astronaut marker.
        self.map_canvas.set_astronaut_marker(point)

        # Update the sidebar.
        self.coordinates_label.setText(
            f"Astronaut: X: {x:.2f}, Y: {y:.2f}"
        )

        if elevation is not None:
            self.elevation_label.setText(
                f"Elevation: {elevation:.2f} m"
            )
        else:
            self.elevation_label.setText("Elevation: Unavailable")

        self.status_label.setText("Astronaut location set")

    def start_waypoint_selection(self):

        self.placement_mode = "waypoint"
        self.map_canvas.start_waypoint_selection()

        self.status_label.setText(
            "Select waypoint location on the map"
        )

    def handle_waypoint_location(self, point):
        self.selected_waypoint = None
        self.delete_waypoint_button.setEnabled(False)

        # Get the selected coordinates in the canvas CRS.
        x = point.x()
        y = point.y()

        # Retrieve the elevation layer.
        elevation_layer = self.layer_manager.get_layer("Elevation")

        elevation = None

        if elevation_layer is not None:

            # Convert the selected point to the elevation layer CRS.
            canvas_crs = self.map_canvas.mapSettings().destinationCrs()

            transform = QgsCoordinateTransform(
                canvas_crs,
                elevation_layer.crs(),
                QgsProject.instance()
            )

            elevation_point = transform.transform(point)

            # Sample the elevation raster.
            provider = elevation_layer.dataProvider()

            value, success = provider.sample(elevation_point, 1)

            if success:
                elevation = value
                # Get geological information at this location.
        
        geology = "Unavailable"

        geology_layer = self.layer_manager.get_layer("Geology")

        if geology_layer is not None:

            # Transform the clicked point into the geology layer CRS.
            geology_transform = QgsCoordinateTransform(
                self.map_canvas.mapSettings().destinationCrs(),
                geology_layer.crs(),
                QgsProject.instance()
            )

            geology_point = geology_transform.transform(point)

            point_geometry = QgsGeometry.fromPointXY(
                QgsPointXY(geology_point)
            )

            # Find the geological polygon containing the point.
            for feature in geology_layer.getFeatures():

                if feature.geometry().intersects(point_geometry):

                    geology = feature["name"]
                    break
        # Retrieve traversability at waypoint.
        traversability = "Unavailable"

        traversability_layer = self.layer_manager.get_layer("Traversability")

        if traversability_layer is not None:

            provider = traversability_layer.dataProvider()

            value, success = provider.sample(point, 1)

            if success and np.isfinite(value) and 0 <= value <= 1:
                traversability = self.classify_traversability(value)

        # Store the selected location as a pending waypoint.
        self.pending_waypoint = {
            "point": point,
            "x": x,
            "y": y,
            "elevation": elevation,
            "geology": geology,
            "traversability": traversability
        }

        self.map_canvas.show_waypoint_preview(point)

        # Update the waypoint information panel.
        self.waypoint_coordinates.setText(
            f"X: {x:.2f}\nY: {y:.2f}"
        )

        if elevation is not None:
            self.waypoint_elevation.setText(
                f"{elevation:.2f}"
            )
        else:
            self.waypoint_elevation.setText("Unavailable")

        self.waypoint_geology.setText(str(geology))

        self.waypoint_traversability.setText(traversability)

        # Reset the name field for the new selection.
        self.waypoint_name_input.clear()

        # Enable saving now that a location has been selected.
        self.save_waypoint_button.setEnabled(True)

        # Display the information panel.
        self.info_panel.show()

        # Update the status bar.
        self.status_label.setText("Waypoint preview")


    def delete_waypoint(self):
        if self.selected_waypoint is None:
            return

        waypoint = self.selected_waypoint

        self.waypoints.remove(waypoint)
        self.map_canvas.remove_waypoint_marker(waypoint)

        self.selected_waypoint = None
        self.delete_waypoint_button.setEnabled(False)

        # Clear the waypoint information.
        self.waypoint_name_input.clear()
        self.waypoint_coordinates.setText("Not selected")
        self.waypoint_elevation.setText("Unavailable")
        self.waypoint_traversability.setText("Not evaluated")
        self.waypoint_geology.setText("Not available")

        self.info_panel.hide()
        self.status_label.setText("Waypoint deleted")

    def save_waypoint(self):

        if self.pending_waypoint is None:
            return

        # Get the waypoint name.
        name = self.waypoint_name_input.text().strip()

        # Assign a default name if none was entered.
        if name == "":
            name = f"Waypoint {len(self.waypoints) + 1}"

        # Add the waypoint to the saved list.
        waypoint = self.pending_waypoint.copy()
        waypoint["name"] = name

        self.waypoints.append(waypoint)
        self.map_canvas.save_waypoint_marker(waypoint)

        # Clear the pending waypoint.
        self.pending_waypoint = None

        # Disable saving until another location is selected.
        self.save_waypoint_button.setEnabled(False)

        # Update the status bar.
        self.status_label.setText(f"Saved {name}")

    def handle_saved_waypoint_selection(self, waypoint):

        # Clear any pending waypoint.
        self.pending_waypoint = None

        # Display the selected waypoint's name.
        self.waypoint_name_input.setText(
            waypoint["name"]
        )

        # Display its coordinates.
        self.waypoint_coordinates.setText(
            f"X: {waypoint['x']:.2f}\nY: {waypoint['y']:.2f}"
        )

        # Display its elevation.
        elevation = waypoint["elevation"]

        if elevation is not None:
            self.waypoint_elevation.setText(
                f"{elevation:.2f}"
            )
        else:
            self.waypoint_elevation.setText("Unavailable")

        # Display the other information.
        self.waypoint_traversability.setText(
            waypoint.get("traversability", "Unavailable")
        )

        self.waypoint_geology.setText(
            str(waypoint.get("geology", "Unavailable"))
        )

        # Disable saving because this waypoint already exists.
        self.save_waypoint_button.setEnabled(False)
        self.selected_waypoint = waypoint
        self.delete_waypoint_button.setEnabled(True)

        # Display the information panel.
        self.info_panel.show()

        self.status_label.setText(
            f"Selected {waypoint['name']}"
        )
        
    def create_top_bar(self):

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(65)

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(20, 5, 20, 5)

        title = QLabel("MARTIAN MAP")
        title.setObjectName("appTitle")

        mission = QLabel("MISSION PLANNER  /  JEZERO CRATER")
        mission.setObjectName("secondaryText")

        layout.addWidget(title)
        layout.addSpacing(25)
        layout.addWidget(mission)

        layout.addStretch()

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_out_button = QPushButton("Zoom Out")
        self.reset_button = QPushButton("Full Extent")

        layout.addWidget(self.zoom_in_button)
        layout.addWidget(self.zoom_out_button)
        layout.addWidget(self.reset_button)

        return top_bar

    def create_sidebar(self):

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)

        # Layer section
        layer_title = QLabel("MAP LAYERS")
        layer_title.setObjectName("sectionTitle")

        layout.addWidget(layer_title)

        # Basemap selection buttons.
        self.elevation_button = QPushButton("Elevation Map")
        self.optical_button = QPushButton("Optical Map")
        self.geology_button = QPushButton("Geology Map")
        self.traversability_button = QPushButton("Traversability Map")

        self.elevation_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        self.optical_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        self.geology_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        self.traversability_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        layout.addWidget(self.elevation_button)
        layout.addWidget(self.optical_button)
        layout.addWidget(self.geology_button)
        layout.addWidget(self.traversability_button)
        
        # Map legend section
        layout.addSpacing(10)

        legend_title = QLabel("MAP LEGEND")
        legend_title.setObjectName("sectionTitle")
        layout.addWidget(legend_title)

        # Scrollable area for legend contents.
        self.legend_scroll = QScrollArea()
        self.legend_scroll.setWidgetResizable(True)
        self.legend_scroll.setFrameShape(QFrame.NoFrame)
        self.legend_scroll.setMinimumHeight(260)

        self.legend_content = QWidget()

        self.legend_content.setStyleSheet("""
            background-color: #F0F2F4;
            border-radius: 5px;
        """)

        self.legend_content_layout = QVBoxLayout(self.legend_content)
        self.legend_content_layout.setContentsMargins(0, 5, 0, 5)
        self.legend_content_layout.setSpacing(8)

        self.legend_scroll.setWidget(self.legend_content)

        layout.addWidget(self.legend_scroll)

        self.update_map_legend("Elevation")

        # Connect the buttons.
        self.elevation_button.clicked.connect(
            self.show_elevation_map
        )

        self.optical_button.clicked.connect(
            self.show_optical_map
        )

        self.geology_button.clicked.connect(
            self.show_geology_map
        )

        self.traversability_button.clicked.connect(
            self.show_traversability_map
        )

        layout.addSpacing(20)

        # Mission section
        mission_title = QLabel("MISSION PLANNING")
        mission_title.setObjectName("sectionTitle")

        layout.addWidget(mission_title)

        self.route_button = QPushButton("Plan Route")
        self.waypoint_button = QPushButton("Add Waypoint")
        self.clear_route_button = QPushButton("Clear Route")

        self.route_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        self.waypoint_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        self.clear_route_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        layout.addWidget(self.route_button)
        layout.addWidget(self.waypoint_button)
        layout.addWidget(self.clear_route_button)
        layout.addSpacing(20)

        # Mission position section
        position_title = QLabel("MISSION POSITION")
        position_title.setObjectName("sectionTitle")

        layout.addWidget(position_title)

        self.astronaut_button = QPushButton("Set / Update Location")
        self.astronaut_button.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
        """)

        layout.addWidget(self.astronaut_button)

        self.astronaut_status = QLabel("Location not set")
        self.astronaut_status.setObjectName("secondaryText")

        layout.addWidget(self.astronaut_status)

        self.astronaut_button.clicked.connect(
            self.start_astronaut_selection
        )

        layout.addStretch()
        
        self.route_button.setEnabled(False)
        self.clear_route_button.setEnabled(False)

        return sidebar

    def create_map_panel(self):

        map_panel = QFrame()
        map_panel.setObjectName("mapPanel")

        layout = QVBoxLayout(map_panel)
        layout.setContentsMargins(8, 8, 8, 8)

        self.map_canvas = MapCanvas()
        self.map_canvas.setCanvasColor(QColor("#252B32"))

        self.map_canvas.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        layout.addWidget(self.map_canvas)

        # Connect map navigation controls
        self.zoom_in_button.clicked.connect(self.map_canvas.zoomIn)
        self.zoom_out_button.clicked.connect(self.map_canvas.zoomOut)
        self.reset_button.clicked.connect(
            self.map_canvas.zoomToFullExtent
        )

        return map_panel
    
    def update_map_legend(self, map_type):
        # Adjust legend height depending on the map.
        if map_type == "Geology":
            self.legend_scroll.setMinimumHeight(350)
        else:
            self.legend_scroll.setMinimumHeight(180)
        # Remove all previous legend contents.
        while self.legend_content_layout.count():

            item = self.legend_content_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

            elif item.layout():
                while item.layout().count():

                    child = item.layout().takeAt(0)

                    if child.widget():
                        child.widget().deleteLater()
                        
        # Elevation map legend.
        if map_type == "Elevation":

            # Maximum elevation.
            maximum_label = QLabel("-2391 m")
            maximum_label.setStyleSheet("""
                color: #263238;
                font-size: 13px;
                font-weight: bold;
            """)

            self.legend_content_layout.addWidget(
                maximum_label,
                alignment=Qt.AlignRight
            )

            # Horizontal elevation gradient.
            gradient = QFrame()
            gradient.setFixedSize(210, 22)
            gradient.setStyleSheet("""
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #000000,
                    stop: 0.08 #263B28,
                    stop: 0.17 #355E36,
                    stop: 0.25 #4E8242,
                    stop: 0.33 #82A650,
                    stop: 0.42 #C2C35B,
                    stop: 0.5 #E5CB55,
                    stop: 0.58 #DFA74A,
                    stop: 0.67 #BB8140,
                    stop: 0.75 #966039,
                    stop: 0.83 #A54830,
                    stop: 0.92 #BB3028,
                    stop: 1 #D73D30
                );
                border: 1px solid #59636E;
                border-radius: 3px;
            """)

            self.legend_content_layout.addWidget(
                gradient,
                alignment=Qt.AlignHCenter
            )

            # Minimum elevation.
            minimum_label = QLabel("-2652 m")
            minimum_label.setStyleSheet("""
                color: #263238;
                font-size: 13px;
                font-weight: bold;
            """)
            self.legend_content_layout.addWidget(
                minimum_label,
                alignment=Qt.AlignLeft
            )

        # Geology map legend.
        elif map_type == "Geology":

            layer = self.layer_manager.get_layer("Geology")

            if layer is not None:

                renderer = layer.renderer()

                if isinstance(renderer, QgsCategorizedSymbolRenderer):

                    categories = renderer.categories()

                    for category in categories:

                        # Create a row for each geological category.
                        row = QHBoxLayout()
                        row.setSpacing(8)

                        # Colour swatch.
                        color_box = QFrame()
                        color_box.setFixedSize(18, 18)

                        color = category.symbol().color().name()

                        color_box.setStyleSheet(f"""
                            background-color: {color};
                            border: 1px solid #5A4036;
                        """)

                        # Geological unit name.
                        name_label = QLabel(category.label())
                        name_label.setStyleSheet("""
                            color: #263238;
                            font-size: 13px;
                            font-weight: bold;
                        """)                        
                        name_label.setWordWrap(True)

                        row.addWidget(color_box)
                        row.addWidget(name_label, 1)

                        self.legend_content_layout.addLayout(row)

                # Traversability map legend.
        elif map_type == "Traversability":

            # Maximum traversability cost.
            maximum_label = QLabel("1.0 - Untraversable")
            maximum_label.setStyleSheet("""
                color: #263238;
                font-size: 13px;
                font-weight: bold;
            """)
            self.legend_content_layout.addWidget(
                maximum_label,
                alignment=Qt.AlignRight
            )

            # Horizontal traversability gradient.
            gradient = QFrame()
            gradient.setFixedSize(210, 22)
            gradient.setStyleSheet("""
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #559455,
                    stop: 0.5 #F7E164,
                    stop: 0.9 #EF9819,
                    stop: 1 #A80407
                );
                border: 1px solid #59636E;
                border-radius: 3px;
            """)

            self.legend_content_layout.addWidget(
                gradient,
                alignment=Qt.AlignHCenter
            )

            # Minimum traversability cost.
            minimum_label = QLabel("0.0 - Traversable")
            minimum_label.setStyleSheet("""
                color: #263238;
                font-size: 13px;
                font-weight: bold;
            """)

            self.legend_content_layout.addWidget(
                minimum_label,
                alignment=Qt.AlignLeft
            )

        # Optical map has no legend.
        else:

            no_legend = QLabel("No legend available")
            no_legend.setObjectName("secondaryText")
            self.legend_content_layout.addWidget(no_legend)

    def show_elevation_map(self):

        layer = self.layer_manager.get_layer("Elevation")

        if layer is not None:

            self.layer_manager.show_layers(["Elevation"])
            self.update_map_legend("Elevation")
            self.status_label.setText("Elevation map displayed")


    def show_optical_map(self):

        layer = self.layer_manager.get_layer("Optical")

        if layer is not None:

            self.layer_manager.show_layers(["Optical"])
            self.update_map_legend("Optical")
            self.status_label.setText("Optical map displayed")

    def show_geology_map(self):

        layer = self.layer_manager.get_layer("Geology")

        if layer is not None:

            self.layer_manager.show_layers(["Geology"])
            self.update_map_legend("Geology")
            self.status_label.setText("Geology map displayed")

    def show_traversability_map(self):

        layer = self.layer_manager.get_layer("Traversability")
        
        if layer is not None:
                        
            self.layer_manager.show_layers(["Traversability"])
            self.update_map_legend("Traversability")
            self.status_label.setText("Traversability map Displayed")

    def classify_traversability(self, value):

        if value < 0.5:
            return "Traversable"
        elif value < 1.0:
            return "Difficult"
        else:
            return "Untraversable"
    def create_info_panel(self):

        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(260)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)
        label_style = """
            font-size: 15px;
            font-weight: bold;
            color: #E9A96B;
        """

        value_style = """
            font-size: 16px;
            font-weight: bold;
            color: #E6EDF3;
        """
        title = QLabel("WAYPOINT INFO")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #E9A96B;
        """)

        layout.addWidget(title)

        # Waypoint name
        name_title = QLabel("Waypoint Name")
        name_title.setStyleSheet(label_style)
        layout.addWidget(name_title)

        self.waypoint_name_input = QLineEdit()
        self.waypoint_name_input.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
        """)
        self.waypoint_name_input.setPlaceholderText(
            "Enter a name (optional)"
        )

        layout.addWidget(self.waypoint_name_input)

        layout.addSpacing(10)

        # Coordinates
        coordinates_title = QLabel("Coordinates")
        coordinates_title.setStyleSheet(label_style)
        layout.addWidget(coordinates_title)

        self.waypoint_coordinates = QLabel("Not selected")
        self.waypoint_coordinates.setStyleSheet(value_style)
        layout.addWidget(self.waypoint_coordinates)

        layout.addSpacing(10)

        # Elevation
        elevation_title = QLabel("Elevation")
        elevation_title.setStyleSheet(label_style)
        layout.addWidget(elevation_title)

        self.waypoint_elevation = QLabel("Unavailable")
        self.waypoint_elevation.setStyleSheet(value_style)
        layout.addWidget(self.waypoint_elevation)

        layout.addSpacing(10)

        # Traversability
        traversability_title = QLabel("Traversability")
        traversability_title.setStyleSheet(label_style)
        layout.addWidget(traversability_title)

        self.waypoint_traversability = QLabel("Not evaluated")
        self.waypoint_traversability.setStyleSheet(value_style)
        layout.addWidget(self.waypoint_traversability)

        layout.addSpacing(10)

        # Geology
        geology_title = QLabel("Geology")
        geology_title.setStyleSheet(label_style)
        layout.addWidget(geology_title)

        self.waypoint_geology = QLabel("Not available")
        self.waypoint_geology.setStyleSheet(value_style)
        layout.addWidget(self.waypoint_geology)

        layout.addStretch()

        # Save button
        self.save_waypoint_button = QPushButton("Save Waypoint")
        self.save_waypoint_button.setEnabled(False)

        self.save_waypoint_button.clicked.connect(
            self.save_waypoint
        )

        layout.addWidget(self.save_waypoint_button)

        self.delete_waypoint_button = QPushButton("Delete Waypoint")
        self.delete_waypoint_button.setEnabled(False)
        self.delete_waypoint_button.clicked.connect(self.delete_waypoint)

        layout.addWidget(self.delete_waypoint_button)

        return panel
    
    def create_status_bar(self):

        status_bar = QFrame()
        status_bar.setObjectName("topBar")
        status_bar.setFixedHeight(32)

        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(15, 2, 15, 2)

        self.coordinates_label = QLabel("Coordinates: --")
        self.elevation_label = QLabel("Elevation: --")
        self.status_label = QLabel("Ready")

        self.coordinates_label.setObjectName("secondaryText")
        self.elevation_label.setObjectName("secondaryText")
        self.status_label.setObjectName("secondaryText")

        layout.addWidget(self.coordinates_label)
        layout.addSpacing(25)
        layout.addWidget(self.elevation_label)

        layout.addStretch()

        layout.addWidget(self.status_label)

        return status_bar
