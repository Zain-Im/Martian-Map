"""Map feedback that sizes itself to the complete message."""
from qgis.PyQt.QtCore import QEvent
from qgis.PyQt.QtWidgets import QLabel


class StatusLabel(QLabel):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        parent.installEventFilter(self)

    def setText(self, text):
        super().setText(text)
        self.fit_message()

    def fit_message(self):
        self.ensurePolished()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        # Measure the full line first; only wrap when it exceeds available space.
        self.setWordWrap(False)
        width = min(self.sizeHint().width(), 380, self.parentWidget().width())
        self.setWordWrap(True)
        self.setFixedWidth(max(1, width))
        self.setFixedHeight(max(self.minimumSizeHint().height(), self.heightForWidth(width)))

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Resize, QEvent.Show):
            self.fit_message()
        return super().eventFilter(watched, event)
