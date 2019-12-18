from PyQt5 import QtWidgets, QtCore, QtGui

import time
import logging


logger = logging.getLogger(__name__)


class ImageViewer(QtWidgets.QWidget):
    click_move_signal = QtCore.pyqtSignal('PyQt_PyObject', 'PyQt_PyObject')

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QPixmap()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        width = painter.device().width()
        height = painter.device().height()
        # drawtime = time.perf_counter()
        painter.drawPixmap(0, 0, self.image.scaled(width, height, aspectRatioMode=QtCore.Qt.KeepAspectRatio))
        # logger.debug("Painter drawtime: %s", time.perf_counter() - drawtime)
        painter.drawEllipse(width//2, height//2, height//30, height//30)

    @QtCore.pyqtSlot(QtGui.QPixmap)
    def set_image(self, image):
        if image.isNull():
            logger.warning("Viewer Dropped frame!")
            return
        self.image = image
        self.update()

    def mousePressEvent(self, QMouseEvent):
        click_x, click_y = QMouseEvent.pos().x(), QMouseEvent.pos().y()
        self.click_move_signal.emit(click_x, click_y)

