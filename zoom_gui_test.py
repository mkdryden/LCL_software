import numpy
import cv2

img_loc = r'C:\Users\Wheeler\Desktop\LCL_software\well_images\well_image___20_09_2018___12.18.52.033870.tif'


class Stitcher():

	def __init__(self):
		self.img = cv2.imread(img_loc)

		# the values we will use to resize the image at the end to fit the screen
		self.user_view_x = int(1024*.78)
		self.user_view_y = int(822*.78)

		# the center point of our image (will be updated when we move along the image)
		self.x = int(self.img.shape[0]/2)
		self.y = int(self.img.shape[1]/2)

		# the number of pixels the unaltered image has (will be updated with zoom)
		self.px_x = int(self.img.shape[0])
		self.px_y = int(self.img.shape[1])
		


		self.img_resized = cv2.resize(self.img,(self.user_view_x,self.user_view_y),cv2.INTER_AREA)
		cv2.imshow('Stitch',self.img_resized)
		cv2.createTrackbar('Zoom','Stitch',0,6,self.manage_zoom)
		cv2.waitKey(0)
		cv2.destroyAllWindows()


	def zoom(self,amt):
		if amt != 0:
			self.px_x = int(self.px_x/amt) 
			self.px_y = int(self.px_y/amt)
			# now we need to update based on our location and the new unaltered img
			# values
			cropped_img = self.img[self.x:self.px_x,self.y:self.px_y]
			img_resized = cv2.resize(cropped_img,
				(self.user_view_x,self.user_view_y),
				cv2.INTER_AREA)
			cv2.imshow('Stitch',img_resized)
	
	def manage_zoom(self,pos):
		print('trackbar at',pos)
		self.zoom(pos)

s = Stitcher()




