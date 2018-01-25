from Phidget22.PhidgetException import *
from Phidget22.Phidget import *
from Phidget22.Devices.Stepper import *
import time
from utils import comment
import matplotlib.pyplot as plt
from PyQt5 import QtCore
import threading,cv2,time
from PyQt5.QtWidgets import QApplication
from multiprocessing.pool import ThreadPool
import numpy as np


class autofocuser(QtCore.QObject):
	'''
	assumes that the stage is maxed out in the CCW direction at start
	which is the maxed out negative direction. therefore any of our
	steps in the positive direction will cause us to move from the 
	max position of the focus
	'''
	# TODO implement a property that prevents the motor from ever going outside of its range. 
	position_and_variance_signal = QtCore.pyqtSignal('PyQt_PyObject')
	def __init__(self, parent = None):
		super(autofocuser, self).__init__(parent)
		self.ch = Stepper()
		self.ch.openWaitForAttachment(5000)
		self.ch.setEngaged(True)
		self.full_scale = 27300
		self.position = self.ch.getTargetPosition()
		self.image_count = 0
		self.track_position = False
		self.pool = ThreadPool(processes=3)
		self.status_dict = {'current limit':self.ch.getCurrentLimit,
				'control mode': self.ch.getControlMode,
				# 'setting min position: ': self.ch.setMinPosition(0),
				'min position': self.ch.getMinPosition,
				# 'setting max position: ': self.ch.setMaxPosition(self.full_scale),
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
		# TODO check if the given position will make us exceed the range		
		self.ch.setTargetPosition(self.ch.getTargetPosition() + position)
		while self.ch.getIsMoving() == True:
			time.sleep(.1)
		# print(self.ch.getTargetPosition())

	def roll_forward(self):
		self.track_position = True
		self.ch.setControlMode(1)
		self.ch.setAcceleration(750)
		self.ch.setVelocityLimit(-5000)		
		res = self.pool.apply_async(self.position_tracker, (5000,750,-1))
		return res

	def roll_backward(self):
		self.track_position = True
		self.ch.setControlMode(1)
		self.ch.setAcceleration(750)
		self.ch.setVelocityLimit(5000)
		res = self.pool.apply_async(self.position_tracker, (5000,750,1))
		return res 

	def stop_roll(self):
		self.ch.setVelocityLimit(0)
		self.track_position = False
		self.ch.setControlMode(1)
		self.ch.setAcceleration(10000)
		comment('focus at {} steps'.format(self.get_position()))

	def swing_range(self):
		self.ch.setVelocityLimit(2000)
		self.ch.setTargetPosition(self.full_scale-2500)

	def get_velocity(self):
		try:
			vel = self.ch.getVelocity()
			return vel
		except:
			return None

	def position_tracker(self,max_velocity,a,direction,x):
		# always assume that initial velocity is 0		
		print('tracking')
		v = 0
		t0 = time.time()
		if direction == -1: a = -a
		i = 1
		positions = []
		self.track_position = True
		while self.ch.getIsMoving() == True:
			dt = (time.time()-t0)
			# check if we are at max velocity
			if v >= max_velocity:
				x += v*dt
			else:
				x += v*dt + 1/2*a*dt**2
				v += a*dt
				if v > max_velocity: v = max_velocity
			t0 += dt
			i += 1
			comment('position tracking x: {} v: {} a: {}'.format(
			x,v,a))
			positions.append(x)
			time.sleep(.1)
		return positions


	def change_magnification(self,index):
		print('changing mag')
		if index == 4:
			self.ch.setTargetPosition(16718)


	@QtCore.pyqtSlot()
	def autofocus(self):
		print(self.ch.getMaxVelocityLimit(),
				self.ch.getAcceleration(),
				1,0)
		# we want to roll the focus forward steadily and capture 
		# laplacian variances as we do so, until we find a max
		
		position_result = self.pool.apply_async(self.position_tracker,(2000,
				self.ch.getAcceleration(),
				1,0))
		self.pool.apply_async(self.swing_range)
		
		variances = []
		
		while self.ch.getIsMoving() == True:
			time.sleep(.01)
			QApplication.processEvents() 
			img = self.image[512:1536,411:1233]
			variance = cv2.Laplacian(img, cv2.CV_64F).var()
			comment('variance calculated {}'.format(variance))
			variances.append(variance)			
		positions = position_result.get()
		# positions = [p*.94 for p in positions]
		# now we want to find the point which corresponded to the highest 
		# VoL
		unit_scaled_location_of_highest_variance = variances.index(max(variances))/len(variances)
		print('location of highest variance: {}'.format(unit_scaled_location_of_highest_variance))
		closest_position = int(np.rint(len(positions)*unit_scaled_location_of_highest_variance))
		print('closest_position',closest_position)
		print('max variance of {} occurred at location {}'.format(
			max(variances),positions[closest_position]))
		self.ch.setTargetPosition(positions[closest_position])
		self.position_and_variance_signal.emit((positions,variances))
		# comment('focus at {} steps'.format(self.get_position()))
		while self.ch.getIsMoving() == True:
			time.sleep(.1)
		self.relative_focus()

	def relative_focus(self):
		# first get our initial variance
		img = self.image[512:1536,411:1233]
		variance = cv2.Laplacian(img, cv2.CV_64F).var()
		QApplication.processEvents() 
		# now move in each direction
		self.step_to_position(250)
		img = self.image[512:1536,411:1233]
		variance_backward = cv2.Laplacian(img, cv2.CV_64F).var()
		QApplication.processEvents() 
		self.step_to_position(-500)
		img = self.image[512:1536,411:1233]
		variance_forward = cv2.Laplacian(img, cv2.CV_64F).var()
		print('initial vairance: {} backward variance {} forward variance {}'.format(
			variance,variance_backward,variance_forward))
		if variance_backward > variance and variance_backward > variance_forward:
			print('moving backward')
			self.step_to_position(250)
		elif variance_forward > variance and variance_forward > variance_backward:
			print('moving forward')
			self.step_to_position(-250)
		elif variance > variance_forward and variance > variance_backward:
			print('max found, staying put')
			self.step_to_position(250)
		self.relative_focus()


if __name__ == '__main__':
	a = autofocuser()
	a.track_position = True
	a.autofocus()
	# time.sleep(4)
	# a.stop_roll()
	a.track_position = False
	# print(b.get())

