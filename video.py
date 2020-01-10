from PyQt5 import QtWidgets, QtCore, QtGui

import time
import logging

logger = logging.getLogger(__name__)


class ImageViewer(QtWidgets.QWidget):
    click_move_signal = QtCore.pyqtSignal('PyQt_PyObject', 'PyQt_PyObject')
    aspect_changed_signal = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QPixmap()
        self.aspect = 1
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        try:
            if self.image.isNull():
                return
        except AttributeError:
            return
        painter = QtGui.QPainter(self)
        width = painter.device().width()
        height = painter.device().height()
        # drawtime = time.perf_counter()
        painter.drawPixmap(0, 0, self.image.scaled(width, height, aspectRatioMode=QtCore.Qt.KeepAspectRatio))
        # logger.debug("Painter drawtime: %s", time.perf_counter() - drawtime)
        painter.drawEllipse(width // 2, height // 2, height // 30, height // 30)
        self.image = None

    @QtCore.pyqtSlot(QtGui.QPixmap)
    def set_image(self, image: QtGui.QPixmap):
        if self.image is not None:
            logger.warning("Viewer Dropped frame!")
        self.image = image
        if self.image is None:
            return
        aspect = self.image.width() / self.image.height()
        if aspect != self.aspect:
            self.aspect = aspect
            self.aspect_changed_signal.emit(self.aspect)
        self.update()

    def mousePressEvent(self, QMouseEvent):
        click_x, click_y = QMouseEvent.pos().x(), QMouseEvent.pos().y()
        self.click_move_signal.emit(click_x, click_y)
