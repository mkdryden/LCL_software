import time
from utils import comment
from keras.models import load_model
import os
from PyQt5 import QtCore 
import cv2
import numpy as np
import tensorflow as tf
global graph
from PyQt5.QtWidgets import QApplication
graph = tf.get_default_graph()

experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)),'models')

class Localizer(QtCore.QObject):
	localizer_move_signal = QtCore.pyqtSignal('PyQt_PyObject','PyQt_PyObject','PyQt_PyObject','PyQt_PyObject')
	get_position_signal = QtCore.pyqtSignal()
	fire_qswitch_signal = QtCore.pyqtSignal()
	stop_laser_flash_signal = QtCore.pyqtSignal()
	ai_fire_qswitch_signal = QtCore.pyqtSignal()
	start_laser_flash_signal = QtCore.pyqtSignal()
	qswitch_screenshot_signal = QtCore.pyqtSignal()

	def __init__(self, parent = None):
		super(Localizer, self).__init__(parent)
		self.localizer_model = load_model(os.path.join(experiment_folder_location,'multiclass_localizer8.hdf5'))
		# self.localizer_model = load_model(os.path.join(experiment_folder_location,'binary_localizer6.hdf5'))
		self.localizer_model._make_predict_function()
		self.position = np.zeros((1,2))

	@QtCore.pyqtSlot('PyQt_PyObject')
	def vid_process_slot(self,image):
		self.image = image
		
	def get_network_output(self,img,mode):
		img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		img = cv2.resize(img, (125, 125))
		img = np.expand_dims(img,axis = 4) 
		img = np.expand_dims(img,axis = 0) 
		with graph.as_default():
			segmented_image = self.localizer_model.predict(img,batch_size = 1)	
		if mode == 'multi':
			return_img = np.zeros((125,125,3))
			#red cell
			return_img[:,:,2] = segmented_image[0,:,:,1]			
			#green cell
			return_img[:,:,1] = segmented_image[0,:,:,2]			
		elif mode == 'binary':
			return_img = segmented_image
		return return_img

	# def continuous_extermination(self):
	# 	'''
	# 	function to run the network in a loop until everything on the screen 
	# 	is destroyed
	# 	'''
	# 	cell_found = True
	# 	while cell_found == True:

	@QtCore.pyqtSlot('PyQt_PyObject')
	def position_return_slot(self,position):
		# we need to get the position from the stage and store it
		self.position = position
		print('GOT POSITION',position)

	def move_frame(self,direction,relative=True):
		frame_dir_dict = {
		'u': np.array([0,95]),
		'd': np.array([0,95]),
		'l': np.array([-95,0]),
		'r': np.array([95,0])
		}
		if relative == True:
			self.localizer_move_signal.emit(frame_dir_dict[direction],False,True,False)
		else:
			self.localizer_move_signal.emit(self.position,False,False,False)

	@QtCore.pyqtSlot()
	def localize(self):
		'''
		function to scan an entire well, and lyse the number of cells desired by the user,
		using the method of lysis that the user selects, then returns to the original
		position (the center of the well)
		'''
		# first get our position
		self.get_position_signal.emit()		 
		
		# localizer_move_slot(self, move_vector, goto_reticle = False,move_relative = True,scale_vector = True):
		self.move_frame('l')
		time.sleep(1)
		QApplication.processEvents()
		self.move_frame('r')
		time.sleep(1)		
		self.get_position_signal.emit()

	@QtCore.pyqtSlot()
	def localize_real(self):
		self.start_laser_flash_signal.emit()
		# segmented_image = self.get_network_output(self.image,'binary')
		segmented_image = self.get_network_output(self.image,'multi')
		cv2.imshow('Cell Outlines and Centers',segmented_image)
		# this retrieves the green cells
		# _,confidence_image = cv2.threshold(segmented_image[:,:,1],.5,1,cv2.THRESH_BINARY)
		# binary localization 
		_,confidence_image = cv2.threshold(segmented_image,.5,1,cv2.THRESH_BINARY)
		_, contours, _ = cv2.findContours(np.uint8(confidence_image), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
		cell_image = np.zeros((125,125))
		cell_contours = []
		cell_centers = []
		for contour in contours:
			print(cv2.contourArea(contour))
			if cv2.contourArea(contour) > 20:
				(x,y),radius = cv2.minEnclosingCircle(contour)
				center = (int(x),int(y))
				cell_contours.append(contour)				
				cv2.circle(cell_image,center,2 ,(255,0,0),-1)
				center = np.array(center)
				cell_centers.append(center)
				# print('contour:',contour,type(contour),contour.shape)
		cv2.drawContours(cell_image, contours, -1, (255,255,255), 1)
		cv2.imshow('Cell Outlines and Centers',cell_image)
		######## DIRECT SHOT LYSIS
		# if len(cell_centers) != 0:			
		# 	print('centers:',cell_centers)
		# 	window_center = np.array([125./2,125./2])
		# 	old_center = cell_centers[0]
		# 	self.hit_target(old_center-window_center,True)
		# 	time.sleep(.25)
		# 	if len(cell_centers) > 1:
		# 		for i in range(1,len(cell_centers)):
		# 			self.hit_target(-old_center + cell_centers[i])
		# 			old_center = cell_centers[i]
		# 			time.sleep(.25)			
		# else:
		# 	print('no cells found!')
		######### EXCISION
		# if len(cell_contours) != 0:			
		# 	window_center = np.array([125./2,125./2])
		# 	# for each contour we want to trace it
		# 	for i in range(len(contours)):			
		# 		contour = contours[i]
		# 		point_number = contour.shape[0] 
		# 		old_center = contour[0].reshape(2)
		# 		self.hit_target(old_center-window_center,True)
		# 		time.sleep(.25)
		# 		for j in range(1,point_number):		
		# 			new_center = contour[j].reshape(2)		
		# 			move_vec = -old_center + new_center
		# 			scaled_move_vec = move_vec*1.5
		# 			self.hit_target(scaled_move_vec)
		# 			old_center = new_center
		# 			time.sleep(.25)			
		# else:
		# 	print('no cells found!')
		self.stop_laser_flash_signal.emit()	

	def hit_target(self,center,goto_reticle = False):
		# we need to scale our centers up to the proper resolution and then 
		# send it to the stage
		x = center[0]*851/125
		y = center[1]*681/125		
		self.localizer_move_signal.emit(np.array([x,y]),goto_reticle,False)
		self.ai_fire_qswitch_signal.emit()
		# for i in range(1):
			# self.ai_fire_qswitch_signal.emit()
		# 	time.sleep(.1)
		
		# for i in range(num_shots):
		# 	time.sleep(.1)
		# 	self.fire_qswitch_signal.emit()

