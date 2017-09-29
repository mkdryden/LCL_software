import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow
from LCL_ui import Ui_MainWindow
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui

class ShowVideo(QtCore.QObject):
 
	#initiating the built in camera
	camera_port = 0
	camera = cv2.VideoCapture(camera_port)
	VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
 
	def __init__(self, parent = None):
		super(ShowVideo, self).__init__(parent)
		

	@QtCore.pyqtSlot()
	def startVideo(self):		
		self.run_video = True
		print('starting video')
		while self.run_video:
			ret, image = self.camera.read()
 
			color_swapped_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
 
			height, width, _ = color_swapped_image.shape
 
			qt_image = QtGui.QImage(color_swapped_image.data,
									width,
									height,
									color_swapped_image.strides[0],
									QtGui.QImage.Format_RGB888)
 
			self.VideoSignal.emit(qt_image)
			QApplication.processEvents()
	
	@QtCore.pyqtSlot()
	def stop_video(self):
		print('stopping video')
		self.run_video = False

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
			print("Viewer Dropped frame!")
 
		self.image = image.scaled(221,171)
		# if image.size() != self.size():
		# 	self.setFixedSize(image.size())
		self.update()

class main_window(QMainWindow):
	def __init__(self):
		super(main_window, self).__init__()

		# set up the video classes and thread
		self.thread = QtCore.QThread()
		self.thread.start()
		self.vid = ShowVideo()
		self.vid.moveToThread(self.thread)
		self.image_viewer = ImageViewer()
		self.vid.VideoSignal.connect(self.image_viewer.setImage)

		# Set up the user interface from Designer.
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)	

		# Make some local modifications.
		self.ui.verticalLayout.addWidget(self.image_viewer)

		# Connect up the buttons.
		self.ui.left_button.clicked.connect(self.print_test)
		self.ui.right_button.clicked.connect(self.vid.startVideo)
		self.ui.down_button.clicked.connect(self.vid.stop_video)
		print('finished init')

	def print_test(self):
		print('test')


app = QApplication(sys.argv)
#############

#############
window = main_window()
window.show()
print('exit with code: ' + str(app.exec_()))
sys.exit()