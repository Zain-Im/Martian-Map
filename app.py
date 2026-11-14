from qgis.PyQt.QtWidgets import (
    QMainWindow,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy
)

import os

from qgis.PyQt.QtGui import QColor

from map_canvas import MapCanvas


class MartianMapWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Martian Map")
        self.resize(1440, 900)

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

        # Bottom status bar
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)

        # Load the initial Mars elevation map.
        self.load_initial_map()
        
    def load_initial_map(self):
        # Get the path to the elevation raster.
        project_dir = os.path.dirname(os.path.abspath(__file__))
        raster_path = os.path.join(
            project_dir,
            "data",
            "raw",
            "elevation_map.tif"
        )

        # Load the raster into the map canvas.
        try:
            self.map_canvas.load_raster(raster_path)
            self.status_label.setText("Elevation map loaded")

        except Exception as error:
            self.status_label.setText("Failed to load elevation map")
            print("Raster loading error:", error)

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

        layout.addWidget(QLabel("Satellite Imagery"))
        layout.addWidget(QLabel("Elevation"))
        layout.addWidget(QLabel("Geology"))
        layout.addWidget(QLabel("Traversability"))

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
        self.waypoint_button.setEnabled(False)
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