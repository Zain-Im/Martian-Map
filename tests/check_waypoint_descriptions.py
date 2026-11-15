import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))
from qgis.core import QgsApplication, QgsPointXY
from qgis.PyQt.QtTest import QTest
from app import MartianMapWindow
app = QgsApplication([], True)
app.initQgis()
w = MartianMapWindow()
field = w.waypoint_description_input
permanent = w.waypoints[0]
assert all(0 < len(p['description']) <= 250 for p in w.waypoints)
original_description = permanent['description']
w.handle_saved_waypoint_selection(permanent)
assert field.isReadOnly() and field.toPlainText() == original_description
assert w.waypoint_name_input.isReadOnly()
QTest.keyClicks(w.waypoint_name_input, 'changed')
assert w.waypoint_name_input.text() == permanent['name']
QTest.keyClicks(field, 'changed')
w.update_waypoint_description('changed')
assert permanent['description'] == original_description and field.toPlainText() == original_description
w.handle_waypoint_location(QgsPointXY(permanent['point']))
assert not field.isReadOnly() and field.toPlainText() == ''
assert not w.waypoint_name_input.isReadOnly()
QTest.keyClicks(field, 'a' * 251)
assert field.toPlainText() == 'a' * 250
assert w.waypoint_description_count.text() == '250 / 250'
w.save_waypoint()
user = w.waypoints[-1]
assert user['description'] == 'a' * 250
field.selectAll()
app.clipboard().setText('b' * 300)
field.paste()
assert field.toPlainText() == 'b' * 250 and user['description'] == 'b' * 250
w.handle_saved_waypoint_selection(permanent)
assert field.toPlainText() == original_description and user['description'] == 'b' * 250
w.handle_saved_waypoint_selection(user)
assert not field.isReadOnly() and field.toPlainText() == 'b' * 250
field.selectAll()
QTest.keyClicks(field, 'Edited description')
assert user['description'] == 'Edited description'
field.selectAll()
app.clipboard().setText('Line\n' * 45)
field.paste()
assert '\n' in field.toPlainText() and len(field.toPlainText()) <= 250
field.resize(240, 110)
field.show()
app.processEvents()
assert field.verticalScrollBar().maximum() > 0
assert user['description'] == field.toPlainText()
w.delete_waypoint()
assert field.toPlainText() == ''
print('PASS: description creation, typing/paste limits, editing, selection isolation, immutable permanent descriptions, deletion reset', flush=True)
w.close()
