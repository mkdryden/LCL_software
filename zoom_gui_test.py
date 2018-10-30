import numpy as np
import cv2
from PyQt5 import QtCore 

img_loc = r'C:\Users\Wheeler\Desktop\LCL_software\LCL_zoom_test\well_image___27_09_2018___14.10.52.062012.tif'


class Stitcher(QtCore.QObject):
	#inteface with main program
	zoom_and_move_signal = QtCore.pyqtSignal('PyQt_PyObject')
	
	def __init__(self, parent=None):
		super(Stitcher, self).__init__(parent)
		self.img = cv2.imread(img_loc)
		# self.stage.change_magnification(2)

		# the values we will use to resize the image at the end to fit the screen
		self.user_view_x = int(1024*.78)
		self.user_view_y = int(822*.78)

		# the center point of our image absolute to top left of screen
		self.x = int(self.img.shape[0]/2)
		self.y = int(self.img.shape[1]/2)
		self.prev_x = int(self.img.shape[0]/2)
		self.prev_y = int(self.img.shape[1]/2)

		# the number of pixels the image has (will be updated with zoom)
		self.px_x = int(self.img.shape[0])
		self.px_y = int(self.img.shape[1])

		# dimensions of original file in pixels (will not change with zoom)
		self.px_x_source = int(self.img.shape[0])
		self.px_y_source = int(self.img.shape[1])
		self.img_resized = cv2.resize(self.img,(self.user_view_x,self.user_view_y),cv2.INTER_AREA)

		cv2.imshow('Stitch',self.img_resized)
		cv2.createTrackbar('Zoom','Stitch',0,6,self.manage_zoom)
		cv2.setMouseCallback('Stitch', self.recenter)

		# cv2.waitKey(0)
		# cv2.destroyAllWindows()



	def zoom(self,amt):
		self.prev_x = self.x
		self.prev_y = self.y

		self.px_x = int(self.px_x_source/(amt+1)) 
		self.px_y = int(self.px_y_source/(amt+1))

		if(amt == 0):
			self.x = int(self.px_x_source/2)
			self.y = int(self.px_y_source/2)
		# now we need to update based on our location and the new unaltered img
		# values, centered still at center of image
		cropped_x_start = self.x-self.px_x//2
		cropped_x_end   = self.x+self.px_x//2 
		cropped_y_start = self.y-self.px_y//2
		cropped_y_end   = self.y+self.px_y//2 

		delta_x = 0
		delta_y = 0
		# make the window not leave the source image
		# important for zooming out, not necessary if amt>previous amt
		if(cropped_x_start <= 0):
			delta_x = 0-cropped_x_start
		elif(cropped_x_end >= self.px_x_source):
			delta_x = self.px_x_source - cropped_x_end
		if(cropped_y_start <= 0):
			delta_y = 0-cropped_y_start
		elif(cropped_y_end>= self.px_y_source):
			delta_y = self.px_y_source - cropped_y_end

		cropped_x_start += delta_x
		cropped_x_end += delta_x
		self.x += delta_x
		cropped_y_start += delta_y
		cropped_y_end += delta_y
		self.y += delta_y

		cropped_x = cropped_x_start, cropped_x_end
		cropped_y = cropped_y_start, cropped_y_end

		cropped_img = self.img[cropped_x[0]:cropped_x[1],cropped_y[0]:cropped_y[1]]

		img_resized = cv2.resize(cropped_img,
			(self.user_view_x,self.user_view_y),
		 	cv2.INTER_AREA)

		self.move_stage_emit() # move the stage
		self.draw_center_circle(img_resized)
		cv2.imshow('Stitch',img_resized)

	#recenter based on the mouse click location
	def recenter(self,event,x,y,flags,param):
		if event == cv2.EVENT_LBUTTONUP:
			self.prev_x = self.x
			self.prev_y = self.y

			# find x and y coordinates in original picture
			# might be a few pixels off
			source_x = self.x-self.px_x//2+int((y/self.user_view_y)*self.px_x)
			source_y = self.y-self.px_y//2+int((x/self.user_view_x)*self.px_y)

			cropped_x_start = source_x-self.px_x//2
			cropped_x_end   = source_x+self.px_x//2 
			cropped_y_start = source_y-self.px_y//2
			cropped_y_end   = source_y+self.px_y//2 

			delta_x = 0
			delta_y = 0
			# make the window not leave the source image
			if(cropped_x_start <= 0):
				delta_x = 0-cropped_x_start
			elif(cropped_x_end >= self.px_x_source):
				delta_x = self.px_x_source - cropped_x_end
			if(cropped_y_start <= 0):
				delta_y = 0-cropped_y_start
			elif(cropped_y_end>= self.px_y_source):
				delta_y = self.px_y_source - cropped_y_end

			cropped_x_start += delta_x
			cropped_x_end += delta_x
			source_x += delta_x
			cropped_y_start += delta_y
			cropped_y_end += delta_y
			source_y += delta_y

			cropped_x = cropped_x_start, cropped_x_end
			cropped_y = cropped_y_start, cropped_y_end

			recentered_img = self.img[cropped_x[0]:cropped_x[1],cropped_y[0]:cropped_y[1]]
			self.x = source_x
			self.y = source_y
			img_resized = cv2.resize(recentered_img,
				(self.user_view_x,self.user_view_y),
			 	cv2.INTER_AREA)

			#move and update the stage
			self.move_stage_emit()
			self.draw_center_circle(img_resized)
			cv2.imshow('Stitch',img_resized)

	
	def manage_zoom(self,pos):
		# print('trackbar at',pos)
		self.zoom(pos)

	#draw green circle at center of image
	def draw_center_circle(self, image):
		cv2.circle(image,(self.user_view_x//2, self.user_view_y//2), 5, (0,255,0), -1)

	@QtCore.pyqtSlot('PyQt_PyObject')
	def move_stage_emit(self):
		relative_move = [self.x-self.prev_x, self.y-self.prev_y]
		self.zoom_and_move_signal.emit(relative_move)

	# def move_stage(self):
	# 	#Find relative pixels to move stage by
	# 	relative_x = self.x-self.prev_x
	# 	relative_y = self.y-self.prev_y

	# 	if(relative_x == 0 and relative_y == 0):
	# 		return

	# 	pixel_move_vector = np.array([relative_y, relative_x])
	# 	step_move_vector = self.stage.scale_move_vector(pixel_move_vector)
	# 	# print(step_move_vector)
	# 	self.stage.move_relative(step_move_vector)


