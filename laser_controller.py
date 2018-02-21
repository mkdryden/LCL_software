import serial
import numpy as np
from utils import comment
from PyQt5 import QtCore

class laser_controller():

	def __init__(self):
		com = 'COM10'
		baud = 9600
		parity = serial.PARITY_NONE
		self.ser = serial.Serial(com, baud, timeout=.25,
			parity=parity)
		self.ser.flushInput()
		self.ser.flushOutput()
		# we want to start simmering immediately if not already
		self.ser.readline()
		self.simmer()
		self.set_delay(200)
		self.ready_to_fire = False

	def issue_command(self,command):
		command_string = '{}\r\n'.format(command)
		comment('sending command to laser:{}'.format(command_string.split('\r')[0]))
		self.ser.write(command_string.encode('utf-8'))
	
	def get_response(self):
		response = ''
		while '\r\n' not in response:
			piece = self.ser.read()
			if piece != b'':
				response += piece.decode('utf-8')
		comment('response received from laser:{}'.format(response))
		return response

	def send_receive(self,command):
		self.issue_command(command)
		response = self.get_response()
		return response		

	def simmer(self):
		return self.send_receive('M')

	def stop_flash(self):
		self.ready_to_fire = False
		return self.send_receive('S')

	def fire_auto(self):
		self.ready_to_fire = True
		return self.send_receive('A')

	def fire_qswitch(self):
		if self.ready_to_fire: return self.send_receive('OP')

	def set_delay(self,delay):
		if str(delay) != '':
			self.send_receive('W {}'.format(delay))

	def qswitch_auto(self):
		if self.ready_to_fire: return self.send_receive('CC')


class attenuator_controller():

	def __init__(self):
		com = 'COM8'
		baud = 19200
		parity = serial.PARITY_NONE
		self.ser = serial.Serial(com, baud, timeout=.25,
			parity=parity)
		self.ser.flushInput()
		self.ser.flushOutput()
		# we always want the attenuator to be at 0.6
		self.set_attenuation(0.6)

	def issue_command(self,command):
		command_string = ';AT:{}\n'.format(command)
		comment('sending command to attenuator:{}'.format(command_string.split('\n')[0]))
		self.ser.write(command_string.encode('utf-8'))
	
	def get_response(self):
		response = ''
		while '\r' not in response:
			piece = self.ser.read()
			if piece != b'':
				response += piece.decode('utf-8')
		comment('response received from attenuator:{}'.format(response))
		return response

	def send_receive(self,command):
		self.issue_command(command)
		response = self.get_response()		
		return response		

	def set_attenuation(self,attenuation):
		if str(attenuation) != '':
			self.send_receive('TF {}'.format(attenuation))

if __name__ == '__main__':
	# laser = laser_controller()
	# laser.simmer()
	# laser.send_receive('')
	attenuator = attenuator_controller()
	attenuator.send_receive('TF?')
# 