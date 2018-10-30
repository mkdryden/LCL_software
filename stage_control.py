#just a test for stage_controller

import serial
from PyQt5 import QtCore
from utils import comment

class stage_control (QtCore.QObject):

	def __init__(self,parent = None):
		super(stage_control, self).__init__(parent)

		com = 'COM9'
		baud = 9600
		parity = serial.PARITY_NONE
		self.ser = serial.Serial(com, baud, timeout=.25,
			parity=parity)
		self.step_size = 5
		self.send_receive('SAS 50')
		self.send_receive('BLSH 0')

		self.magnification = 4
		self.microns_per_pixel = 100/34
		self.calibration_factor = 1.20*4
		

	def issue_command(self,command):
		'''
		sends command and handles any errors from stage
		'''
		command_string = '{}\r'.format(command)
		#comment('sending command to stage:{}'.format(command_string))
		self.ser.write(command_string.encode('utf-8'))

	def get_response(self):
		response = ''
		while '\r' not in response:
			piece = self.ser.read()
			if piece != b'':
				response += piece.decode('utf-8')
		# comment('response received from stage:{}'.format(response))
		return response

	def send_receive(self,command):
		self.issue_command(command)
		response = self.get_response()		
		return response


	def update_mov(self):
		print("moving")
		return self.send_receive('GR,-{},0'.format(100*self.step_size))




if __name__ == '__main__':
	stage = stage_control()
	stage.update_mov()