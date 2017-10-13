import serial
import numpy as np
from utils import comment
from PyQt5 import QtCore

class stage_controller():
	def __init__(self):
		'''
		open the serial port and check the status of the stage 
		'''
		com = 'COM4'
		baud = 9600
		parity = serial.PARITY_NONE
		self.ser = serial.Serial(com, baud, timeout=.25,
			parity=parity)
		self.step_size = 1000
		self.last_move_vector = np.zeros(2)
		self.magnification = 4
		self.microns_per_pixel = 50/14.5
		self.calibration_factor = 1.45*4
		self.key_control_dict = {
		87:self.move_up,
		65:self.move_left,
		83:self.move_down,
		68:self.move_right,
		66:self.move_last}

	def change_magnification(self,index):
		# TODO fix this stupid conversion
		map_dict = {
		0:4,
		1:20,
		2:40,
		3:60,
		4:100
		}
		comment('magnification changed to: {}'.format(map_dict[index]))
		self.magnification = map_dict[index]

	def set_step_size(self,step_size):
		comment('step size changed to: {}'.format(step_size))
		self.step_size = step_size

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
		return self.send_receive('GR,0,-{}'.format(self.step_size))

	@QtCore.pyqtSlot()
	def move_down(self):
		return self.send_receive('GR,0,{}'.format(self.step_size))

	@QtCore.pyqtSlot()
	def move_right(self):
		return self.send_receive('GR,{},0'.format(self.step_size))

	@QtCore.pyqtSlot()
	def move_left(self):
		return self.send_receive('GR,-{},0'.format(self.step_size))

	def move_relative(self,move_vector):
		self.last_move_vector = -1*move_vector
		return self.send_receive('GR,{},{}'.format(move_vector[0],move_vector[1]))

	def move_last(self):
		return self.move_relative(self.last_move_vector)

	def click_move(self,window_width,window_height,click_x,click_y):
		window_center = np.array([window_width/2,window_height/2])
		mouse_click_location = np.array([click_x,click_y])
		pixel_move_vector = mouse_click_location - window_center
		step_move_vector = pixel_move_vector/self.magnification * self.microns_per_pixel * self.calibration_factor
		step_move_vector = step_move_vector.astype(int)
		comment('click move vector: {}'.format(step_move_vector))
		return self.move_relative(step_move_vector)

	def handle_keypress(self,key):
		if key in self.key_control_dict.keys():
			self.key_control_dict[key]()

if __name__ == '__main__':
	stage = stage_controller()
	stage_controller.home_stage(stage)


