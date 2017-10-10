import serial
from utils import comment
from PyQt5 import QtCore

class stage_controller():
	def __init__(self):
		'''
		open the serial port and check the status of the stage 
		'''
		com = 'COM3'
		baud = 9600
		parity = serial.PARITY_NONE
		self.ser = serial.Serial(com, baud, timeout=0,
			parity=parity)

	def issue_command(self,command):
		'''
		sends command and handles any errors from stage
		'''
		command_string = '{}\r'.format(command)
		comment('sending command to stage:{}'.format(command_string))
		self.ser.write(command_string.encode('utf-8'))

	def get_response(self):		
		response = ''
		while 'END' not in response:
			piece = self.ser.read()
			if piece != b'':
				response += piece.decode('utf-8')
		comment('response received from stage:{}'.format(response))
		return response

	def get_status(self):
		self.issue_command('?')
		return self.get_response()

	@QtCore.pyqtSlot()
	def move_left(self):
		print('test')

	@QtCore.pyqtSlot()
	def move_right(self):
		pass

	@QtCore.pyqtSlot()
	def move_down(self):
		pass

	@QtCore.pyqtSlot()
	def move_up(self):
		pass

if __name__ == '__main__':
	stage = stage_controller()
	stage_controller.get_status(stage)

