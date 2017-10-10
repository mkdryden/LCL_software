from PyQt5 import QtCore
import time,os,datetime
import cv2
import logging

def now():
	return datetime.datetime.now().strftime('%d_%m_%Y___%H.%M.%S.%f')

def comment(text):
	'''
	prints to screen and logs simultaneously
	'''
	now_time = now()
	logging.info('{0}{1}{2}'.format(text,
		'.'*(80-(len(text)+len(now_time))),
		now_time))
	print(text)

class screen_shooter():
	'''
	handles the various different types of screenshots
	'''	
	@QtCore.pyqtSlot('PyQt_PyObject')
	def screenshot_slot(self,image):
		self.image = image

	@QtCore.pyqtSlot()
	def save_target_image(self):		
		comment('taking target picture')
		cv2.imwrite(os.path.join(experiment_folder_location,
			'target___{}.jpg'.format(now())),self.image)
	
	@QtCore.pyqtSlot()
	def save_non_target_image(self):
		comment('taking non target picture')
		cv2.imwrite(os.path.join(experiment_folder_location,
			'non_target___{}.jpg'.format(now())),self.image)

	@QtCore.pyqtSlot()
	def save_misc_image(self):
		comment('taking miscellaneous picture')
		cv2.imwrite(os.path.join(experiment_folder_location,
			'miscellaneous___{}.jpg'.format(now())),self.image)

experiment_name = 'experiment_{}'.format(now())
experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)),'Experiments',experiment_name) 
os.makedirs(experiment_folder_location)
logging.basicConfig(filename=os.path.join(experiment_folder_location,
	'{}.log'.format(experiment_name)), level=logging.INFO)