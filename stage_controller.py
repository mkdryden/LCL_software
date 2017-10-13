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
		self.ser = serial.Serial(com, baud, timeout=.25,
			parity=parity)
		self.standard_move_size = 1000
		self.key_control_dict = {
		87:self.move_up,
		65:self.move_left,
		83:self.move_down,
		68:self.move_right}

	def issue_command(self,command):
		'''
		sends command and handles any errors from stage
		'''
		command_string = '{}\r'.format(command)
		comment('sending command to stage:{}'.format(command_string))
		self.ser.write(command_string.encode('utf-8'))

	def get_long_response(self):		
		response = ''
		while 'END' not in response:
			piece = self.ser.read()
			if piece != b'':
				response += piece.decode('utf-8')
		comment('response received from stage:{}'.format(response))
		return response

	def send_receive(self,command):
		self.issue_command(command)
		response = self.ser.readline()
		comment('response received from stage:{}'.format(response))
		return response

	def get_status(self):	
		self.issue_command('?')	
		return self.get_long_response()

	@QtCore.pyqtSlot()
	def home_stage(self):
		# hits the limit switches and then returns to last known location
		return self.send_receive('RIS')

	@QtCore.pyqtSlot()
	def get_position(self):
		return self.send_receive('P')

	def go_to_position(self,x,y):
		return self.send_receive('G,{},{}'.format(x,y))

	@QtCore.pyqtSlot()
	def move_up(self):
		return self.send_receive('GR,0,-{}'.format(self.standard_move_size))

	@QtCore.pyqtSlot()
	def move_down(self):
		return self.send_receive('GR,0,{}'.format(self.standard_move_size))

	@QtCore.pyqtSlot()
	def move_right(self):
		return self.send_receive('GR,{},0'.format(self.standard_move_size))

	@QtCore.pyqtSlot()
	def move_left(self):
		return self.send_receive('GR,-{},0'.format(self.standard_move_size))

	def handle_keypress(self,key):
		if key in self.key_control_dict.keys():
			self.key_control_dict[key]()


if __name__ == '__main__':
	stage = stage_controller()
	stage_controller.home_stage(stage)


