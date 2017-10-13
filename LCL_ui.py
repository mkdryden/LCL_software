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
        MainWindow.resize(619, 544)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(100, 0, 501, 411))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(-90, 200, 75, 23))
        self.pushButton.setObjectName("pushButton")
        self.target_screenshot_button = QtWidgets.QPushButton(self.centralwidget)
        self.target_screenshot_button.setGeometry(QtCore.QRect(10, 10, 81, 61))
        self.target_screenshot_button.setObjectName("target_screenshot_button")
        self.non_target_screenshot_button = QtWidgets.QPushButton(self.centralwidget)
        self.non_target_screenshot_button.setGeometry(QtCore.QRect(10, 70, 81, 61))
        self.non_target_screenshot_button.setObjectName("non_target_screenshot_button")
        self.misc_screenshot_button = QtWidgets.QPushButton(self.centralwidget)
        self.misc_screenshot_button.setGeometry(QtCore.QRect(10, 130, 81, 61))
        self.misc_screenshot_button.setObjectName("misc_screenshot_button")
        self.comment_box = QtWidgets.QTextEdit(self.centralwidget)
        self.comment_box.setGeometry(QtCore.QRect(240, 440, 161, 41))
        self.comment_box.setObjectName("comment_box")
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox.setGeometry(QtCore.QRect(420, 420, 171, 121))
        self.groupBox.setObjectName("groupBox")
        self.down_button = QtWidgets.QPushButton(self.groupBox)
        self.down_button.setGeometry(QtCore.QRect(40, 60, 90, 23))
        self.down_button.setObjectName("down_button")
        self.right_button = QtWidgets.QPushButton(self.groupBox)
        self.right_button.setGeometry(QtCore.QRect(80, 40, 75, 23))
        self.right_button.setObjectName("right_button")
        self.up_button = QtWidgets.QPushButton(self.groupBox)
        self.up_button.setGeometry(QtCore.QRect(40, 20, 90, 23))
        self.up_button.setObjectName("up_button")
        self.left_button = QtWidgets.QPushButton(self.groupBox)
        self.left_button.setGeometry(QtCore.QRect(10, 40, 75, 23))
        self.left_button.setObjectName("left_button")
        self.home_stage_button = QtWidgets.QPushButton(self.groupBox)
        self.home_stage_button.setGeometry(QtCore.QRect(7, 90, 75, 23))
        self.home_stage_button.setObjectName("home_stage_button")
        self.get_position_button = QtWidgets.QPushButton(self.groupBox)
        self.get_position_button.setGeometry(QtCore.QRect(87, 90, 75, 23))
        self.get_position_button.setObjectName("get_position_button")
        self.comment_box_label = QtWidgets.QLabel(self.centralwidget)
        self.comment_box_label.setGeometry(QtCore.QRect(240, 420, 71, 16))
        self.comment_box_label.setObjectName("comment_box_label")
        self.user_comment_button = QtWidgets.QPushButton(self.centralwidget)
        self.user_comment_button.setGeometry(QtCore.QRect(240, 490, 161, 23))
        self.user_comment_button.setObjectName("user_comment_button")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LCL System"))
        self.pushButton.setText(_translate("MainWindow", "PushButton"))
        self.target_screenshot_button.setText(_translate("MainWindow", "Target \n"
" Screenshot"))
        self.non_target_screenshot_button.setText(_translate("MainWindow", "Non-Target \n"
" Screenshot"))
        self.misc_screenshot_button.setText(_translate("MainWindow", "Miscellaneous \n"
" Screenshot"))
        self.groupBox.setTitle(_translate("MainWindow", "Stage Controls"))
        self.down_button.setText(_translate("MainWindow", "Down"))
        self.right_button.setText(_translate("MainWindow", "Right"))
        self.up_button.setText(_translate("MainWindow", "Up"))
        self.left_button.setText(_translate("MainWindow", "Left"))
        self.home_stage_button.setText(_translate("MainWindow", "Home Stage"))
        self.get_position_button.setText(_translate("MainWindow", "Get Position"))
        self.comment_box_label.setText(_translate("MainWindow", "Comment box"))
        self.user_comment_button.setText(_translate("MainWindow", "Add comment to log"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

