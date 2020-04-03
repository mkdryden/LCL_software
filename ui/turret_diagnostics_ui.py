# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/mdryden/src/LCL_software/ui/turret_diagnostics.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TurretCalDockWidget(object):
    def setupUi(self, TurretCalDockWidget):
        TurretCalDockWidget.setObjectName("TurretCalDockWidget")
        TurretCalDockWidget.resize(250, 172)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(TurretCalDockWidget.sizePolicy().hasHeightForWidth())
        TurretCalDockWidget.setSizePolicy(sizePolicy)
        TurretCalDockWidget.setMinimumSize(QtCore.QSize(250, 172))
        TurretCalDockWidget.setFloating(True)
        TurretCalDockWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.dockWidgetContents = QtWidgets.QWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dockWidgetContents.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents.setSizePolicy(sizePolicy)
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.turretstatus_label = QtWidgets.QLabel(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.turretstatus_label.sizePolicy().hasHeightForWidth())
        self.turretstatus_label.setSizePolicy(sizePolicy)
        self.turretstatus_label.setText("")
        self.turretstatus_label.setTextFormat(QtCore.Qt.PlainText)
        self.turretstatus_label.setObjectName("turretstatus_label")
        self.gridLayout.addWidget(self.turretstatus_label, 0, 0, 1, 2)
        self.mm_mode_button = QtWidgets.QPushButton(self.dockWidgetContents)
        self.mm_mode_button.setCheckable(True)
        self.mm_mode_button.setChecked(False)
        self.mm_mode_button.setAutoDefault(False)
        self.mm_mode_button.setDefault(False)
        self.mm_mode_button.setFlat(False)
        self.mm_mode_button.setObjectName("mm_mode_button")
        self.gridLayout.addWidget(self.mm_mode_button, 1, 0, 1, 2)
        self.position_edit = QtWidgets.QLineEdit(self.dockWidgetContents)
        self.position_edit.setObjectName("position_edit")
        self.gridLayout.addWidget(self.position_edit, 2, 0, 1, 1)
        self.goto_button = QtWidgets.QPushButton(self.dockWidgetContents)
        self.goto_button.setObjectName("goto_button")
        self.gridLayout.addWidget(self.goto_button, 2, 1, 1, 1)
        self.index_edit = QtWidgets.QLineEdit(self.dockWidgetContents)
        self.index_edit.setObjectName("index_edit")
        self.gridLayout.addWidget(self.index_edit, 3, 0, 1, 1)
        self.index_button = QtWidgets.QPushButton(self.dockWidgetContents)
        self.index_button.setObjectName("index_button")
        self.gridLayout.addWidget(self.index_button, 3, 1, 1, 1)
        TurretCalDockWidget.setWidget(self.dockWidgetContents)

        self.retranslateUi(TurretCalDockWidget)
        QtCore.QMetaObject.connectSlotsByName(TurretCalDockWidget)

    def retranslateUi(self, TurretCalDockWidget):
        _translate = QtCore.QCoreApplication.translate
        TurretCalDockWidget.setWindowTitle(_translate("TurretCalDockWidget", "Turret Diagnostics"))
        self.mm_mode_button.setText(_translate("TurretCalDockWidget", "Activate mm mode"))
        self.goto_button.setText(_translate("TurretCalDockWidget", "Go to position"))
        self.index_button.setText(_translate("TurretCalDockWidget", "Set index"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    TurretCalDockWidget = QtWidgets.QDockWidget()
    ui = Ui_TurretCalDockWidget()
    ui.setupUi(TurretCalDockWidget)
    TurretCalDockWidget.show()
    sys.exit(app.exec_())

