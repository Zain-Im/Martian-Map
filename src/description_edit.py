"""Scrollable plain-text description editor with a hard character limit."""

from qgis.PyQt.QtWidgets import QPlainTextEdit
from qgis.PyQt.QtGui import QTextCursor


class DescriptionEdit(QPlainTextEdit):
    LIMIT = 250

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self.setMaximumHeight(160)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.textChanged.connect(self._enforce_limit)

    def _remaining(self):
        cursor = self.textCursor()
        return max(0, self.LIMIT - len(self.toPlainText()) + len(cursor.selectedText()))

    def insertFromMimeData(self, source):
        if not self.isReadOnly():
            self.insertPlainText(source.text()[:self._remaining()])

    def keyPressEvent(self, event):
        text = event.text()
        if text and (text.isprintable() or text in ("\r", "\n", "\t")):
            if len(text) > self._remaining():
                event.accept()
                return
        super().keyPressEvent(event)

    def _enforce_limit(self):
        # Also cover input methods, drag/drop, and programmatic insertion.
        text = self.toPlainText()
        if len(text) > self.LIMIT:
            cursor = self.textCursor()
            position = cursor.position()
            previous = self.blockSignals(True)
            trim = self.textCursor()
            trim.movePosition(QTextCursor.End)
            # Qt cursor positions use UTF-16 units, not Python character counts.
            boundary = len(text[:self.LIMIT].encode("utf-16-le")) // 2
            trim.setPosition(boundary, QTextCursor.KeepAnchor)
            trim.removeSelectedText()
            cursor.setPosition(min(position, boundary))
            self.setTextCursor(cursor)
            self.blockSignals(previous)
