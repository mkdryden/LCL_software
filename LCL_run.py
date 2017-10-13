import sys,logging,os
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow
from LCL_ui import Ui_MainWindow
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from utils import screen_shooter,now,comment
from stage_controller import stage_controller

class ShowVideo(QtCore.QObject):
	camera_port = 1 + cv2.CAP_DSHOW
	# camera_port = 0 + cv2.CAP_DSHOW
	camera = cv2.VideoCapture(camera_port)
	VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
	screenshot_signal = QtCore.pyqtSignal('PyQt_PyObject')

	def __init__(self, parent = None):
		super(ShowVideo, self).__init__(parent)
		self.run_video = True
		
	@QtCore.pyqtSlot()
	def startVideo(self):		
		comment('video properties:')
		self.camera.set(12,128) 
		self.camera.set(17,3000) 
		for i in range(19):
			comment('property {}, value: {}'.format(i,
				self.camera.get(i)))
		while self.run_video:
			ret, image = self.camera.read()
			self.screenshot_signal.emit(image)
			color_swapped_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) 			
			height, width, _ = color_swapped_image.shape 
			qt_image = QtGui.QImage(color_swapped_image.data,
									width,
									height,
									color_swapped_image.strides[0],
									QtGui.QImage.Format_RGB888) 
			self.VideoSignal.emit(qt_image)			
			QApplication.processEvents()
		self.camera.release()
		comment('ending video')


class ImageViewer(QtWidgets.QWidget):
	def __init__(self, parent = None):
		super(ImageViewer, self).__init__(parent)
		self.image = QtGui.QImage()
		self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

	def paintEvent(self, event):
		painter = QtGui.QPainter(self)
		painter.drawImage(0,0, self.image)
		self.image = QtGui.QImage()
 
	@QtCore.pyqtSlot(QtGui.QImage)
	def setImage(self, image):
		if image.isNull():
			comment("Viewer Dropped frame!")		
		self.image = self.resize_dynamically(image)
		self.update()
	
	def resize_dynamically(self,image):
		return image.scaled(window.ui.verticalLayoutWidget.size())

	def mousePressEvent(self, QMouseEvent):
		print(QMouseEvent.pos())

class main_window(QMainWindow):
	def __init__(self):
		super(main_window, self).__init__()

		# set up the video classes 
		self.vid = ShowVideo()
		self.image_viewer = ImageViewer()
		self.vid.VideoSignal.connect(self.image_viewer.setImage)
		self.screen_shooter = screen_shooter()
		self.vid.screenshot_signal.connect(self.screen_shooter.screenshot_slot)

		# Set up the user interface from Designer.
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)	

		# Make some local modifications.
		self.ui.verticalLayout.addWidget(self.image_viewer)

		# Screenshot and comment buttons
		self.ui.target_screenshot_button.clicked.connect(self.screen_shooter.save_target_image)			
		self.ui.non_target_screenshot_button.clicked.connect(self.screen_shooter.save_non_target_image)					
		self.ui.misc_screenshot_button.clicked.connect(self.screen_shooter.save_misc_image)
		self.ui.user_comment_button.clicked.connect(self.send_user_comment)
		# Stage movement buttons
		self.ui.left_button.clicked.connect(stage.move_left)
		self.ui.right_button.clicked.connect(stage.move_right)
		self.ui.down_button.clicked.connect(stage.move_down)
		self.ui.up_button.clicked.connect(stage.move_up)
		self.ui.get_position_button.clicked.connect(stage.get_position)
		self.ui.home_stage_button.clicked.connect(stage.home_stage)		
		self.show()
		comment('finished init')	

	def send_user_comment(self):
		comment('user comment:{}'.format(self.ui.comment_box.toPlainText()))
		self.ui.comment_box.clear()

	def keyPressEvent(self,event):
		stage.handle_keypress(event.key())

	def closeEvent(self, event):
		self.vid.run_video = False

if __name__ == '__main__':	
	app = QApplication(sys.argv)
	stage = stage_controller()
	window = main_window()
	window.vid.startVideo()
	comment('exit with code: ' + str(app.exec_()))
	sys.exit()