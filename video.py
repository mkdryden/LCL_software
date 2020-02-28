from PyQt5 import QtWidgets, QtCore, QtGui

import time
import logging

from hardware.objectives import Objectives, Objective

logger = logging.getLogger(__name__)


class ImageViewer(QtWidgets.QWidget):
    click_move_signal = QtCore.pyqtSignal(float, float)
    click_move_pix_signal = QtCore.pyqtSignal(int, int)
    aspect_changed_signal = QtCore.pyqtSignal(float)

    def __init__(self, parent=None, objectives: Objectives = None):
        super(ImageViewer, self).__init__(parent)
        self.objectives = objectives
        self._temp_obj = Objective("temp", 1)
        self.image = QtGui.QPixmap()
        self.image_drawn = False
        self.aspect = 1
        self.scale = 1
        self.modifiers = None

        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    @property
    def objective(self) -> Objective:
        try:
            return self.objectives.current_objective
        except AttributeError:
            return self._temp_obj

    def paintEvent(self, event):
        try:
            if self.image.isNull():
                return
        except AttributeError:
            return
        painter = QtGui.QPainter(self)
        width = painter.device().width()
        height = painter.device().height()
        painter.drawPixmap(0, 0, self.image.scaled(
            width, height, aspectRatioMode=QtCore.Qt.KeepAspectRatio))
        self.scale = width / self.image.width()
        painter.drawRect(int(width // 2 - 150 * self.scale),
                         int(height // 2 - 150 * self.scale),
                         int(300 * self.scale),
                         int(300 * self.scale))

        # Laser Reticle
        painter.setPen(QtGui.QPen(QtCore.Qt.cyan, 3))
        painter.drawEllipse(QtCore.QPointF(self.objective.laser_x * self.scale,  # Center
                                           self.objective.laser_y * self.scale),
                            self.objective.laser_r * self.scale,  # rx
                            self.objective.laser_r * self.scale)  # ry
        laser_spot = QtCore.QPointF(self.objective.laser_spot_x, self.objective.laser_spot_y)
        laser_spot *= self.scale
        lines = [QtCore.QLineF(-10, -10, 10, 10).translated(laser_spot),
                 QtCore.QLineF(10, -10, -10, 10).translated(laser_spot)]
        painter.setPen(QtGui.QPen(QtCore.Qt.red, 2))
        painter.drawLines(lines)

        self.image_drawn = True

    @QtCore.pyqtSlot(QtGui.QPixmap)
    def set_image(self, image: QtGui.QPixmap):
        if not self.image_drawn:
            pass
            # logger.debug("Viewer Dropped frame!")  # Very noisy logger
        self.image = image
        if self.image is None:
            return
        self.image_drawn = False
        aspect = self.image.width() / self.image.height()
        if aspect != self.aspect:
            self.aspect = aspect
            self.aspect_changed_signal.emit(self.aspect)
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """
        Emits click_move_signal with relative mouse position to centre of window and
        click_move_pix_signal with absolute mouse position in camera pixels.
        """
        self.modifiers = event.modifiers()
        click_x, click_y = event.pos().x(), event.pos().y()

        if self.modifiers == QtCore.Qt.ControlModifier:
            self.objective.laser_x = click_x / self.scale
            self.objective.laser_y = click_y / self.scale
        elif self.modifiers == QtCore.Qt.ShiftModifier:
            self.objective.laser_spot_x = click_x / self.scale
            self.objective.laser_spot_y = click_y / self.scale
        else:
            self.click_move_signal.emit(click_x/self.width() - 0.5, click_y/self.height() - 0.5)
            self.click_move_pix_signal.emit(click_x // self.scale,
                                            click_y // self.scale)

        self.update()

    def mouseMoveEvent(self, event):
        click_x, click_y = event.pos().x(), event.pos().y()

        if self.modifiers == QtCore.Qt.ControlModifier:
            center = QtCore.QLineF(self.objective.laser_x, self.objective.laser_y,
                                   click_x / self.scale, click_y / self.scale)
            self.objective.laser_r = center.length()
            self.update()
        elif self.modifiers == QtCore.Qt.ShiftModifier:
            self.objective.laser_spot_x = click_x / self.scale
            self.objective.laser_spot_y = click_y / self.scale
            self.update()

    def mouseReleaseEvent(self, event):
        self.mouseMoveEvent(event)
        if self.modifiers == QtCore.Qt.ControlModifier or self.modifiers == QtCore.Qt.ShiftModifier:
            self.objectives.save_yaml()
        self.modifiers = None


class MagnifiedImageViewer(ImageViewer):
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
        painter.drawPixmap(0, 0, self.image,
                           self.image.width()//2 - width//2, self.image.height()//2 - height//2,
                           width, height)
        # logger.debug("Painter drawtime: %s", time.perf_counter() - drawtime)
        self.image = None
