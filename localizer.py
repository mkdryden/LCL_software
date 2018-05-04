import time
from utils import comment
from keras.models import load_model
import os
from PyQt5 import QtCore 
import cv2
import numpy as np
import tensorflow as tf
global graph
graph = tf.get_default_graph()

experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)),'models')

class Localizer(QtCore.QObject):
	vector_move_signal = QtCore.pyqtSignal('PyQt_PyObject')

	def __init__(self, parent = None):
		super(Localizer, self).__init__(parent)
		self.localizer_model = load_model(os.path.join(experiment_folder_location,'resnet_fcn_localizer2.hdf5'))
		self.localizer_model._make_predict_function()

	@QtCore.pyqtSlot('PyQt_PyObject')
	def vid_process_slot(self,image):
		self.image = image
		
	def get_network_output(self,img):
		img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		img = cv2.resize(img, (500, 500))
		img = np.expand_dims(img,axis = 4) 
		img = np.expand_dims(img,axis = 0) 
		with graph.as_default():
			segmented_image = self.localizer_model.predict(img,batch_size = 1)			
		return segmented_image

	@QtCore.pyqtSlot()
	def localize(self):
		segmented_image = self.get_network_output(self.image)
		print('returned shape',segmented_image.shape)
		_,confidence_image = cv2.threshold(segmented_image[0,:,:,0],.9,1,cv2.THRESH_BINARY)		
		_, contours, _ = cv2.findContours(np.uint8(confidence_image), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
		cell_image = np.zeros((500,500))
		cell_contours = []
		cell_centers = []
		for contour in contours:
			print(cv2.contourArea(contour))
			if cv2.contourArea(contour) > 3000:
				(x,y),radius = cv2.minEnclosingCircle(contour)
				center = (int(x),int(y))
				cell_contours.append(contour)				
				cv2.circle(cell_image,center,2 ,(255,0,0),-1)
				center = np.array(center)
				cell_centers.append(center)
		# cv2.drawContours(cell_image, cell_contours, -1, (255,255,255), 3)
		# cv2.imshow('Cell Outlines and Centers',cell_image)
		window_center = np.array([250,250])
		old_center = cell_centers[0]
		self.hit_target(old_center-window_center)
		time.sleep(.5)
		if len(cell_centers) > 1:
			for i in range(1,len(cell_centers)):
				self.hit_target(-old_center + cell_centers[i])
				old_center = cell_centers[i]
				time.sleep(.5)


	def hit_target(self,center):
		# we need to scale our centers up to the proper resolution and then 
		# send it to the stage
		x = center[0]*851/500
		y = center[1]*681/500		
		self.vector_move_signal.emit(np.array([x,y]))


