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
        MainWindow.resize(520, 353)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.up_button = QtWidgets.QPushButton(self.centralwidget)
        self.up_button.setGeometry(QtCore.QRect(210, 220, 90, 23))
        self.up_button.setObjectName("up_button")
        self.right_button = QtWidgets.QPushButton(self.centralwidget)
        self.right_button.setGeometry(QtCore.QRect(250, 240, 75, 23))
        self.right_button.setObjectName("right_button")
        self.left_button = QtWidgets.QPushButton(self.centralwidget)
        self.left_button.setGeometry(QtCore.QRect(180, 240, 75, 23))
        self.left_button.setObjectName("left_button")
        self.down_button = QtWidgets.QPushButton(self.centralwidget)
        self.down_button.setGeometry(QtCore.QRect(210, 260, 90, 23))
        self.down_button.setObjectName("down_button")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(130, 0, 261, 201))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(-90, 200, 75, 23))
        self.pushButton.setObjectName("pushButton")
        self.target_screenshot_button = QtWidgets.QPushButton(self.centralwidget)
        self.target_screenshot_button.setGeometry(QtCore.QRect(40, 10, 81, 61))
        self.target_screenshot_button.setObjectName("target_screenshot_button")
        self.non_target_screenshot_button = QtWidgets.QPushButton(self.centralwidget)
        self.non_target_screenshot_button.setGeometry(QtCore.QRect(40, 70, 81, 61))
        self.non_target_screenshot_button.setObjectName("non_target_screenshot_button")
        self.misc_screenshot = QtWidgets.QPushButton(self.centralwidget)
        self.misc_screenshot.setGeometry(QtCore.QRect(40, 130, 81, 61))
        self.misc_screenshot.setObjectName("misc_screenshot")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 520, 21))
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
        self.pushButton.setText(_translate("MainWindow", "PushButton"))
        self.target_screenshot_button.setText(_translate("MainWindow", "Target \n"
" Screenshot"))
        self.non_target_screenshot_button.setText(_translate("MainWindow", "Non-Target \n"
" Screenshot"))
        self.misc_screenshot.setText(_translate("MainWindow", "Miscellaneous \n"
" Screenshot"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

