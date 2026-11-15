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
    QLineEdit
)

import os

from qgis.PyQt.QtGui import QColor
from qgis.core import QgsCoordinateTransform, QgsProject

from layer_manager import LayerManager
from map_canvas import MapCanvas


class MartianMapWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Martian Map")
        self.resize(1440, 900)
        self.waypoints = []
        self.pending_waypoint = None

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
            self.map_canvas.start_waypoint_selection
        )

        self.map_canvas.location_picked.connect(
            self.handle_waypoint_location
        )

        self.map_canvas.waypoint_selected.connect(
            self.handle_saved_waypoint_selection
        )

        # Bottom status bar
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)

        # Load the initial Mars elevation map.
        self.load_initial_map()
    
    def load_initial_map(self):

        project_dir = os.path.dirname(os.path.abspath(__file__))

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
    

    def handle_waypoint_location(self, point):

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

        # Store the selected location as a pending waypoint.
        self.pending_waypoint = {
            "point": point,
            "x": x,
            "y": y,
            "elevation": elevation
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

        # Reset the name field for the new selection.
        self.waypoint_name_input.clear()

        # Enable saving now that a location has been selected.
        self.save_waypoint_button.setEnabled(True)

        # Display the information panel.
        self.info_panel.show()

        # Update the status bar.
        self.status_label.setText("Waypoint preview")

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
            "Not evaluated"
        )

        self.waypoint_geology.setText(
            "Not available"
        )

        # Disable saving because this waypoint already exists.
        self.save_waypoint_button.setEnabled(False)

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

        layout.addWidget(self.elevation_button)
        layout.addWidget(self.optical_button)

        # Connect the buttons.
        self.elevation_button.clicked.connect(
            self.show_elevation_map
        )

        self.optical_button.clicked.connect(
            self.show_optical_map
        )
        layout.addSpacing(20)

        # Mission section
        mission_title = QLabel("MISSION PLANNING")
        mission_title.setObjectName("sectionTitle")

        layout.addWidget(mission_title)

        self.route_button = QPushButton("Plan Route")
        self.waypoint_button = QPushButton("Add Waypoint")
        self.clear_route_button = QPushButton("Clear Route")

        layout.addWidget(self.route_button)
        layout.addWidget(self.waypoint_button)
        layout.addWidget(self.clear_route_button)

        layout.addStretch()

        # Selected location section
        location_title = QLabel("SELECTED LOCATION")
        location_title.setObjectName("sectionTitle")

        layout.addWidget(location_title)

        self.location_label = QLabel("No location selected")
        self.location_label.setObjectName("secondaryText")

        layout.addWidget(self.location_label)
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
    
    def show_elevation_map(self):

        layer = self.layer_manager.get_layer("Elevation")

        if layer is not None:

            self.layer_manager.show_layers(["Elevation"])
            self.status_label.setText("Elevation map displayed")


    def show_optical_map(self):

        layer = self.layer_manager.get_layer("Optical")

        if layer is not None:

            self.layer_manager.show_layers(["Optical"])
            self.status_label.setText("Optical map displayed")

    def create_info_panel(self):

        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(260)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)

        title = QLabel("WAYPOINT INFORMATION")
        title.setObjectName("sectionTitle")

        layout.addWidget(title)

        # Waypoint name
        layout.addWidget(QLabel("Waypoint Name"))

        self.waypoint_name_input = QLineEdit()
        self.waypoint_name_input.setPlaceholderText(
            "Enter a name (optional)"
        )

        layout.addWidget(self.waypoint_name_input)

        layout.addSpacing(10)

        # Coordinates
        layout.addWidget(QLabel("Coordinates"))

        self.waypoint_coordinates = QLabel("Not selected")
        self.waypoint_coordinates.setObjectName("secondaryText")
        layout.addWidget(self.waypoint_coordinates)

        layout.addSpacing(10)

        # Elevation
        layout.addWidget(QLabel("Elevation"))

        self.waypoint_elevation = QLabel("Unavailable")
        self.waypoint_elevation.setObjectName("secondaryText")
        layout.addWidget(self.waypoint_elevation)

        layout.addSpacing(10)

        # Traversability
        layout.addWidget(QLabel("Traversability"))

        self.waypoint_traversability = QLabel("Not evaluated")
        self.waypoint_traversability.setObjectName("secondaryText")
        layout.addWidget(self.waypoint_traversability)

        layout.addSpacing(10)

        # Geology
        layout.addWidget(QLabel("Geology"))

        self.waypoint_geology = QLabel("Not available")
        self.waypoint_geology.setObjectName("secondaryText")
        layout.addWidget(self.waypoint_geology)

        layout.addStretch()

        # Save button
        self.save_waypoint_button = QPushButton("Save Waypoint")
        self.save_waypoint_button.setEnabled(False)

        self.save_waypoint_button.clicked.connect(
            self.save_waypoint
        )

        layout.addWidget(self.save_waypoint_button)

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