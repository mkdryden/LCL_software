# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'LCL.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(376, 315)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.up_button = QtWidgets.QPushButton(self.centralwidget)
        self.up_button.setGeometry(QtCore.QRect(150, 200, 90, 23))
        self.up_button.setObjectName("up_button")
        self.right_button = QtWidgets.QPushButton(self.centralwidget)
        self.right_button.setGeometry(QtCore.QRect(190, 220, 75, 23))
        self.right_button.setObjectName("right_button")
        self.left_button = QtWidgets.QPushButton(self.centralwidget)
        self.left_button.setGeometry(QtCore.QRect(120, 220, 75, 23))
        self.left_button.setObjectName("left_button")
        self.down_button = QtWidgets.QPushButton(self.centralwidget)
        self.down_button.setGeometry(QtCore.QRect(150, 240, 90, 23))
        self.down_button.setObjectName("down_button")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(80, 20, 221, 171))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 376, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LCL System"))
        self.up_button.setText(_translate("MainWindow", "Up"))
        self.right_button.setText(_translate("MainWindow", "Right"))
        self.left_button.setText(_translate("MainWindow", "Left"))
        self.down_button.setText(_translate("MainWindow", "Down"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

