from PyQt5 import QtCore
import time,os,datetime
import cv2
import logging
import time
import numpy as np
from PyQt5.QtCore import QThread
import threading

def now():
	return datetime.datetime.now().strftime('%d_%m_%Y___%H.%M.%S.%f')

def comment(text):
	'''
	prints to screen and logs simultaneously
	'''
	splits = text.split()
	text = ''
	for split in splits:
		text = text + split + ' ' 
	now_time = now()
	logging.info('{0}{1}{2}'.format(text,
		'.'*(80-(len(text)+len(now_time))),
		now_time))
	print(text,threading.current_thread())	

class screen_shooter(QtCore.QObject):
	'''
	handles the various different types of screenshots
	'''	
	def __init__(self, parent = None):
		super(screen_shooter, self).__init__(parent)
		self.requested_frames = 0
		self.image_count = 0
		self.image_title = ''

	@QtCore.pyqtSlot('PyQt_PyObject')
	def screenshot_slot(self,image):
		self.image = image
		self.image_count += 1
		if self.requested_frames > 0:			
			cv2.imwrite(os.path.join(experiment_folder_location,
				'{}___{}.tif'.format(self.image_title,now())),self.image)
			self.requested_frames -= 1			
			print('writing frame {} to disk'.format(self.image_count))

	@QtCore.pyqtSlot()
	def save_target_image(self):		
		comment('taking target picture')
		self.image_title = 'target'
		self.requested_frames += 1	
	
	@QtCore.pyqtSlot()
	def save_non_target_image(self):
		comment('taking non-target picture')
		self.image_title = 'non_target'
		self.requested_frames += 1	

	@QtCore.pyqtSlot()
	def save_misc_image(self):
		comment('taking miscellaneous picture')
		self.image_title = 'miscellaneous'
		self.requested_frames += 1		

	@QtCore.pyqtSlot()
	def save_lysed_screenshot(self):
		comment('taking lysed picture')
		self.image_title = 'lysed'
		self.requested_frames += 1

	@QtCore.pyqtSlot()
	def save_qswitch_fire_slot(self):
		'''
		takes an initial screenshot of the current frame (before firing)
		and then queues up 4 more pictures to be taken during the firing
		'''
		comment('taking qswitch fire pictures')
		print('writing frame {} to disk'.format(self.image_count))
		cv2.imwrite(os.path.join(experiment_folder_location,
				'before_qswitch___{}.tif'.format(now())),self.image)
		self.image_title = 'during_qswitch_fire'
		self.requested_frames += 15

experiment_name = 'experiment_{}'.format(now())	
experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)),'Experiments',experiment_name) 		
log = logging.getLogger(__name__)
os.makedirs(experiment_folder_location)
fn = os.path.join(experiment_folder_location,'{}.log'.format(experiment_name))
logging.basicConfig(filename=fn, level=logging.INFO)	