import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))
from qgis.core import QgsApplication, QgsPointXY
from app import MartianMapWindow
from permanent_waypoints import PermanentWaypoints
app = QgsApplication([], True)
app.initQgis()
window = MartianMapWindow()
assert len(window.waypoints) == 8
assert len(window.map_canvas.waypoint_markers) == 8
layer = window.layer_manager.get_layer('Elevation')
for marker, waypoint in window.map_canvas.waypoint_markers:
    assert layer.extent().contains(waypoint['point']), waypoint['name']
    assert waypoint['elevation'] is not None, waypoint['name']
    window.map_canvas.select_waypoint(marker, waypoint)
    assert window.waypoint_name_input.text() == waypoint['name']
    assert not window.delete_waypoint_button.isEnabled()
    assert marker.color().name() == PermanentWaypoints.COLOR.lower()
    window.delete_waypoint()
    window.map_canvas.remove_waypoint_marker(waypoint)
    assert len(window.waypoints) == 8
    assert len(window.map_canvas.waypoint_markers) == 8
assert window.permanent_waypoints.insert(window) == 0
first = window.waypoints[0]
window.handle_waypoint_location(QgsPointXY(first['point']))
window.waypoint_name_input.setText('User point')
window.save_waypoint()
assert len(window.waypoints) == 9
user = window.waypoints[-1]
marker = window.map_canvas.waypoint_markers[-1][0]
window.map_canvas.select_waypoint(marker, user)
assert window.delete_waypoint_button.isEnabled()
window.delete_waypoint()
assert len(window.waypoints) == 8
assert len(window.map_canvas.waypoint_markers) == 8
window.route_selection_mode = True
window.handle_saved_waypoint_selection(first)
assert window.route_destination is first
print('PASS: eight projected locations within DEM, elevation samples, normal selection, deletion guards, idempotence, user waypoint deletion, route destination', flush=True)
window.close()
