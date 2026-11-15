"""Predefined Mars locations inserted into the normal waypoint collection."""

from math import isfinite
from osgeo import osr
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeatureRequest,
    QgsGeometry, QgsPointXY, QgsProject,
)


class PermanentWaypoints:
    COLOR = "#C084FC"
    DESCRIPTIONS = {
        "Rochette": "A basaltic rock in the Máaz formation sampled by Perseverance. Its minerals and signs of water alteration provide clues about Jezero Crater's volcanic and environmental history.",
        "Brac": "An olivine-rich igneous rock studied by Perseverance. Its mineral composition provides evidence of crystal accumulation in ancient Martian magma.",
        "Issole": "An igneous rock target in the Séítah formation. Its olivine-rich composition helps scientists investigate magma cooling and the formation of Mars' ancient crust.",
        "Sid": "An igneous rock target in the Máaz formation. Its chemical composition helps scientists investigate volcanic processes and the diversity of rocks on Jezero Crater's floor.",
        "Roubion": "A basaltic rock target examined by Perseverance. Its geological characteristics help scientists understand ancient volcanic activity and subsequent alteration on Mars.",
        "Octavia E. Butler Landing Site": "The historic landing site of NASA's Perseverance rover, which touched down on February 18, 2021, beginning its mission to investigate ancient Martian environments and search for signs of past life.",
        "Three Forks": "A location where Perseverance deposited backup samples of Martian rock and soil. These samples preserve geological evidence that could help scientists study Mars' history.",
        "Jezero Delta Front": "The edge of an ancient river delta formed when water flowed into Jezero Crater billions of years ago. Its sedimentary deposits may preserve evidence of ancient habitable environments.",
    }
    # East-positive longitude, latitude in degrees on the map's Mars datum.
    LOCATIONS = (
        ("Rochette", 77.44437, 18.43074),
        ("Brac", 77.44301, 18.43397),
        ("Issole", 77.44133, 18.43264),
        ("Sid", 77.45242, 18.44386),
        ("Roubion", 77.45165, 18.42769),
        ("Octavia E. Butler Landing Site", 77.45080, 18.44470),
        ("Three Forks", 77.40820, 18.45280),
        ("Jezero Delta Front", 77.40610, 18.45890),
    )

    def insert(self, window):
        """Add missing predefined points after map layers are loaded."""
        elevation = window.layer_manager.get_layer("Elevation")
        if elevation is None:
            return 0
        # Derive geographic coordinates from Mars, never Earth's EPSG:4326.
        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromWkt(elevation.crs().toWkt())
        geographic = QgsCoordinateReferenceSystem()
        if not geographic.createFromWkt(spatial_ref.CloneGeogCS().ExportToWkt()):
            raise ValueError("Could not determine the Mars geographic CRS")
        canvas_crs = window.map_canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(geographic, canvas_crs, QgsProject.instance())
        existing = {p.get("permanent_id") for p in window.waypoints}
        added = 0
        for name, longitude, latitude in self.LOCATIONS:
            if name in existing:
                continue
            point = transform.transform(QgsPointXY(longitude, latitude))
            waypoint = {
                "name": name, "point": point, "x": point.x(), "y": point.y(),
                "longitude": longitude, "latitude": latitude,
                "permanent": True, "permanent_id": name, "color": self.COLOR,
                "description": self.DESCRIPTIONS[name],
                "elevation": self.sample(elevation, point, canvas_crs),
                "geology": "Unavailable", "traversability": "Unavailable",
            }
            cost = self.sample(window.layer_manager.get_layer("Traversability"), point, canvas_crs)
            if cost is not None and 0 <= cost <= 1:
                waypoint["traversability"] = window.classify_traversability(cost)
            geology = window.layer_manager.get_layer("Geology")
            if geology is not None:
                location = QgsCoordinateTransform(canvas_crs, geology.crs(), QgsProject.instance()).transform(point)
                geometry = QgsGeometry.fromPointXY(location)
                request = QgsFeatureRequest().setFilterRect(geometry.boundingBox())
                for feature in geology.getFeatures(request):
                    if feature.geometry().intersects(geometry):
                        waypoint["geology"] = feature["name"]
                        break
            window.map_canvas.add_waypoint_marker(waypoint)
            window.waypoints.append(waypoint)
            added += 1
        return added

    @staticmethod
    def sample(layer, point, source_crs):
        if layer is None:
            return None
        location = QgsCoordinateTransform(source_crs, layer.crs(), QgsProject.instance()).transform(point)
        value, success = layer.dataProvider().sample(location, 1)
        return value if success and isfinite(value) else None
