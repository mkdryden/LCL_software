from Phidget22.PhidgetException import *
from Phidget22.Phidget import *
from Phidget22.Devices.Stepper import *
import time
from utils import comment
import matplotlib.pyplot as plt
from PyQt5 import QtCore
import threading,cv2
from PyQt5.QtWidgets import QApplication

class autofocuser(QtCore.QObject):
	'''
	assumes that the stage is maxed out in the CCW direction at start
	which is the maxed out negative direction. therefore any of our
	steps in the positive direction will cause us to move from the 
	max position of the focus
	'''
	# TODO implement a property that prevents the motor from ever going outside of its range. 
	def __init__(self, parent = None):
		super(autofocuser, self).__init__(parent)
		self.ch = Stepper()
		self.ch.openWaitForAttachment(5000)
		self.ch.setEngaged(True)
		self.full_scale = 27300
		self.position = self.ch.getTargetPosition()
		self.image_count = 0
		self.status_dict = {'current limit':self.ch.getCurrentLimit,
				'control mode': self.ch.getControlMode,
				'min position': self.ch.getMinPosition,
				'max position': self.ch.getMaxPosition,
				'rescale factor': self.ch.getRescaleFactor,
				'target position': self.ch.getTargetPosition,
				'acceleration': self.ch.getAcceleration,
				'engaged?': self.ch.getEngaged,
				'max velocity:': self.ch.getMaxVelocityLimit}
		for k,v in self.status_dict.items():
				comment('{}: {}'.format(k,v()))			
		# self.step_to_position(self.full_scale)
		# self.autofocus()

	@QtCore.pyqtSlot('PyQt_PyObject')
	def vid_process_slot(self,image):
		self.image = image
		self.image_count += 1
		# print('image received in autofocus')

	def get_position(self):
		self.position = self.ch.getPosition()
		return self.position

	def step_to_position(self,position):
		self.ch.setTargetPosition(self.ch.getTargetPosition() + position)
		while self.ch.getIsMoving() == True:
			time.sleep(.1)
		# print(self.ch.getTargetPosition())

	def roll_forward(self):
		self.ch.setControlMode(1)
		self.ch.setAcceleration(750)
		self.ch.setVelocityLimit(-5000)		

	def roll_backward(self):
		self.ch.setControlMode(1)
		self.ch.setAcceleration(750)
		self.ch.setVelocityLimit(5000)

	def stop_roll(self):
		self.ch.setVelocityLimit(0)
		self.ch.setControlMode(1)
		self.ch.setAcceleration(10000)
		comment('focus at {} steps'.format(self.get_position()))

	def swing_range(self):
		self.ch.setVelocityLimit(5000)
		self.ch.setTargetPosition(self.full_scale)

	# def calculate_position(self,previous_position,velocity,acceleration):
	# 	if velocity == self.status_dict['max velocity']:
	# 		new_position = 

	@QtCore.pyqtSlot()
	def autofocus(self):
		# we want to roll the focus forward steadily and capture 
		# laplacian variances as we do so, until we find a max
		t = threading.Thread(target=self.swing_range)
		t.start()
		variances = []
		# positions = []
		while self.ch.getIsMoving() == True:
			# positions.append(self.get_position())
			QApplication.processEvents() 
			variance = cv2.Laplacian(self.image, cv2.CV_64F).var()
			comment('variance calculated {}'.format(variance))
			variances.append(variance)			
		# now let's walk it back until it is near our max
		desired_max = max(variances)
		comment('max variance found: {}'.format(desired_max))
		t = threading.Thread(target=self.roll_forward)
		t.start()
		while desired_max > variance:
			variance = cv2.Laplacian(self.image, cv2.CV_64F).var()
			comment('finding max..variance calculated {}'.format(variance))
			QApplication.processEvents() 
		self.stop_roll()

if __name__ == '__main__':
	a = autofocuser()
	a.step_to_position(10000)

