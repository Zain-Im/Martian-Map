"""Reusable dark-theme map legend, driven by the active layer renderer."""
from qgis.PyQt.QtCore import Qt, QPoint
from qgis.PyQt.QtGui import QColor, QPainter, QPen, QPixmap, QPolygon
from qgis.PyQt.QtWidgets import (
    QFrame, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QSizePolicy, QLayout
)
from qgis.core import QgsCategorizedSymbolRenderer
from permanent_waypoints import PermanentWaypoints
from map_canvas import MapCanvas


class MapLegend(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('mapLegend')
        self.setMinimumHeight(264)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.setStyleSheet('''
            QFrame#mapLegend { background: #172330; border: 1px solid #34465A; border-radius: 8px; }
            QFrame#mapLegend QWidget { background: transparent; }
            QFrame#mapLegend QLabel { color: #E6EDF3; font-size: 13px; font-weight: bold; border: none; }
            QFrame#mapLegend QScrollArea { border: none; }
            QFrame#mapLegend QScrollBar:vertical { background: #172330; width: 6px; margin: 0; }
            QFrame#mapLegend QScrollBar::handle:vertical { background: #40566D; border-radius: 3px; min-height: 24px; }
            QFrame#mapLegend QScrollBar::add-line:vertical, QFrame#mapLegend QScrollBar::sub-line:vertical { height: 0; }
            QFrame#mapLegend QScrollBar::add-page:vertical, QFrame#mapLegend QScrollBar::sub-page:vertical { background: transparent; }
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.scroll, 1)
        content = QWidget()
        self.scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 7, 0)
        layout.setSpacing(10)
        layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.title = QLabel('Elevation · metres')
        self.title.setWordWrap(True)
        self.title.setStyleSheet('color: #E9A96B; font-size: 14px; font-weight: bold;')
        layout.addWidget(self.title)
        self.layer_details = QVBoxLayout()
        layout.addLayout(self.layer_details)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet('background-color: #34465A; border: none;')
        layout.addWidget(divider)
        heading = QLabel('MAP MARKERS')
        heading.setStyleSheet('color: #9BAFC2; font-size: 11px; font-weight: bold;')
        layout.addWidget(heading)
        for title, color in [('Landmarks', PermanentWaypoints.COLOR),
                             ('Your waypoints', MapCanvas.WAYPOINT_COLOR),
                             ('Astronaut', MapCanvas.ASTRONAUT_COLOR)]:
            layout.addWidget(self.swatch_row(title, color, circle=title == 'Astronaut',
                                            diamond=title != 'Astronaut'))
        layout.addStretch()

    @staticmethod
    def swatch_row(text, color, circle=False, diamond=False):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 3, 0, 3)
        row.setSpacing(10)
        swatch = QFrame()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(f'background-color: {color}; border: 1px solid #9BAFC2; border-radius: {7 if circle else 3}px;')
        if circle or diamond:
            pixmap = QPixmap(20, 20)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor(MapCanvas.MARKER_OUTLINE), 2))
            painter.setBrush(QColor(color))
            if diamond:
                painter.drawPolygon(QPolygon([QPoint(10, 2), QPoint(18, 10),
                                               QPoint(10, 18), QPoint(2, 10)]))
            else:
                painter.drawEllipse(3, 3, 14, 14)
            painter.end()
            swatch = QLabel()
            swatch.setPixmap(pixmap)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMinimumWidth(0)
        row.addWidget(swatch, 0, Qt.AlignTop)
        row.addWidget(label, 1)
        return widget

    @staticmethod
    def scale(stops, low, high):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(7)
        ramp = QFrame()
        ramp.setFixedHeight(18)
        gradient = ', '.join(f'stop: {position:.6f} {color}' for position, color in stops)
        ramp.setStyleSheet(f'background: qlineargradient(x1:0,y1:0,x2:1,y2:0,{gradient}); border: 1px solid #59636E; border-radius: 3px;')
        layout.addWidget(ramp)
        labels = QHBoxLayout()
        for text, alignment in [(low, Qt.AlignLeft), (high, Qt.AlignRight)]:
            label = QLabel(text)
            label.setAlignment(alignment)
            label.setStyleSheet('color: #9BAFC2; font-size: 12px; font-weight: bold;')
            labels.addWidget(label, 1)
        layout.addLayout(labels)
        return widget

    def update_layer(self, name, layer=None):
        self.title.setText({'Elevation': 'Elevation · metres', 'Traversability': 'Terrain difficulty',
                            'Geology': 'Geological units', 'Optical': 'Optical imagery'}.get(name, name))
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 7, 0)
        layout.setSpacing(6)
        if name == 'Optical':
            label = QLabel('Surface imagery\nUse the marker key below to identify locations.')
            label.setWordWrap(True)
            label.setStyleSheet('color: #9BAFC2; font-weight: bold;')
            layout.addWidget(label)
        elif layer is None:
            layout.addWidget(QLabel('Layer unavailable'))
        elif name == 'Geology' and isinstance(layer.renderer(), QgsCategorizedSymbolRenderer):
            for category in layer.renderer().categories():
                layout.addWidget(self.swatch_row(category.label(), category.symbol().color().name()))
        elif name in ('Elevation', 'Traversability'):
            items = layer.renderer().shader().rasterShaderFunction().colorRampItemList()
            if name == 'Traversability':
                continuous = [item for item in items if item.value < 1]
                stops = [(item.value / continuous[-1].value, item.color.name()) for item in continuous]
                layout.addWidget(self.scale(stops, '0 · Easy', '<1 · Difficult'))
                blocked = next(item for item in items if item.value == 1)
                layout.addWidget(self.swatch_row('Blocked · score 1', blocked.color.name()))
            elif items:
                low, high = items[0].value, items[-1].value
                stops = [((item.value-low)/(high-low), item.color.name()) for item in items]
                layout.addWidget(self.scale(stops, f'{low:,.0f}', f'{high:,.0f}'))
        old = self.layer_details.takeAt(0)
        if old is not None:
            old.widget().deleteLater()
        self.layer_details.addWidget(content)
        self.scroll.verticalScrollBar().setValue(0)
