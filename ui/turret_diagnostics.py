import logging
from typing import Callable

from PyQt5 import QtCore, QtWidgets

from ui.turret_diagnostics_ui import Ui_TurretCalDockWidget

logger = logging.getLogger(__name__)


class TurretCal(QtCore.QObject):
    goto_position_signal = QtCore.pyqtSignal(int)
    set_index_signal = QtCore.pyqtSignal(int)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super(TurretCal, self).__init__(parent=parent)
        self.widget = QtWidgets.QDockWidget(parent=parent)
        self.ui = Ui_TurretCalDockWidget()
        self.ui.setupUi(self.widget)

        self.ui.goto_button.clicked.connect(self._goto_position)
        self.ui.index_button.clicked.connect(self._set_index)

    def setup_signals(self, mm_mode: Callable, goto_position: Callable,
                      set_index: Callable, status_out: QtCore.pyqtBoundSignal):
        self.ui.mm_mode_button.clicked.connect(mm_mode)
        self.goto_position_signal.connect(goto_position)
        self.set_index_signal.connect(set_index)
        status_out.connect(self._set_status)

    def _goto_position(self):
        self.goto_position_signal.emit(int(self.ui.position_edit.text()))

    def _set_index(self):
        self.set_index_signal.emit(int(self.ui.index_edit.text()))

    def _set_status(self, position: int):
        self.ui.turretstatus_label.setText(f"Position: {position}")
