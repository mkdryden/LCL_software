from Phidget22.PhidgetException import *
from Phidget22.Phidget import *
from Phidget22.Devices.Stepper import *
import time
from utils import comment


class autofocuser():

	def __init__(self):
		self.ch = Stepper()
		self.ch.openWaitForAttachment(5000)
		self.ch.setEngaged(True)
		self.full_scale = 32300
		status_dict = {'current limit':self.ch.getCurrentLimit,
				'control mode': self.ch.getControlMode,
				'min position': self.ch.getMinPosition,
				'max position': self.ch.getMaxPosition,
				'rescale factor': self.ch.getRescaleFactor,
				'target position': self.ch.getTargetPosition,
				'acceleration': self.ch.getAcceleration,
				'engaged?': self.ch.getEngaged}
		for k,v in status_dict.items():
				comment('{}: {}'.format(k,v()))			
		# self.step_to_position(-self.full_scale)

	def step_to_position(self,position):
		self.ch.setTargetPosition(self.ch.getTargetPosition() + position)
		while self.ch.getIsMoving() == True:
			time.sleep(.1)
		print(self.ch.getTargetPosition())

	def roll_forward(self):
		self.ch.setControlMode(1)
		self.ch.setVelocityLimit(-1000)		

	def roll_backward(self):
		self.ch.setControlMode(1)
		self.ch.setVelocityLimit(1000)

	def stop_roll(self):
		self.ch.setVelocityLimit(0)
		self.ch.setControlMode(1)

if __name__ == '__main__':
	a = autofocuser()
	a.step_to_position(10000)

