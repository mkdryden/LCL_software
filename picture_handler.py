import sys,os
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog, QLabel
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5 import QtCore, QtGui, QtWidgets 

class image_window(QWidget):
	 
	 def __init__(self):
		  super().__init__()
		  print('init image window')

	 def show_ui(self,image):
		  print('showing img window')
		  self.setObjectName('Fluorescence Image')
		  label = QLabel(self)
		  pixmap = QPixmap(image)
		  pixmap = pixmap.scaled(1280, 720, QtCore.Qt.KeepAspectRatio)
		  label.setPixmap(pixmap)
		  self.resize(pixmap.width(),pixmap.height())		 
		  self.show()
	
	 def mousePressEvent(self,QMouseEvent):
		  click_x,click_y = QMouseEvent.pos().x(),QMouseEvent.pos().y()
		  print(click_x,click_y)

	 def keyPressEvent(self,event):
		 print(event.key())		  

class file_dialog(QWidget):
	 image_loc_signal = QtCore.pyqtSignal('PyQt_PyObject')
	 
	 def __init__(self):
		  super().__init__()
		  self.title = 'Open Image'
		  self.left = 10
		  self.top = 10
		  self.width = 640
		  self.height = 480      
		  
	 def show_ui(self):
		  self.setWindowTitle(self.title)
		  self.setGeometry(self.left, self.top, self.width, self.height)
		  self.openFileNameDialog()
 
	 def openFileNameDialog(self):    
			options = QFileDialog.Options()
			fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)
			if fileName:
				print('emitting')
				self.image_loc_signal.emit(fileName)   

class image_based_movement_controller():
	'''
	correlates to two points on the image to two points
	on the stage and then allows for movement via the loaded
	image
	'''
	def __init__(self):
		self.stage_calibration_point1 = np.zeros(2)
		self.stage_calibration_point2 = np.zeros(2)
		self.image_calibration_point1 = np.zeros(2)
		self.image_calibration_point2 = np.zeros(2)

	def calibrate_point1(self):
		pass

	def calibrate_point2(self):
		pass

class picture_manager():

	def __init__(self):
		self.dialog = file_dialog()
		self.img = image_window()
		self.controller = image_based_movement_controller()

	def show_file_dialog(self):
		self.dialog.image_loc_signal.connect(self.file_image_slot)
		self.dialog.show_ui()      

	@QtCore.pyqtSlot('PyQt_PyObject')
	def file_image_slot(self,image):
		print(image)
		self.img.show_ui(image)








