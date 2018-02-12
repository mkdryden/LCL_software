import serial
import numpy as np
from utils import comment
from PyQt5 import QtCore
import matplotlib.pyplot as plt

class stage_controller():
	def __init__(self):
		'''
		open the serial port and check the status of the stage  
		'''
		com = 'COM9'
		baud = 9600
		parity = serial.PARITY_NONE
		self.ser = serial.Serial(com, baud, timeout=.25,
			parity=parity)
		self.step_size = 20
		self.reverse_move_vector = np.zeros(2)
		self.return_from_dmf_vector = np.zeros(2)
		self.magnification = 4
		self.microns_per_pixel = 50/14.5
		self.calibration_factor = 1.25*4
		self.send_receive('SAS 50')
		self.lysing_loc = self.get_position()
		self.lysing = True
		self.dmf_position = np.array([115175,14228])

	def change_magnification(self,index):
		map_dict = {
		0:4,
		1:20,
		2:40,
		3:60,
		4:100
		}
		comment('magnification changed to: {}'.format(map_dict[index]))
		self.compensate_for_objective_offsets(self.magnification,map_dict[index])

	def compensate_for_objective_offsets(self,present_mag,future_mag):
		compensation_dict ={
		4:np.zeros(2),
		20:np.array([-67,-115]),
		40:np.array([-78,-124]),
		60:np.array([-74,-132]),
		100:np.array([-79,-139])
		}
		# get back to 4 first
		move = -1*compensation_dict[present_mag]
		# now compensate for offsets from 4
		move = move + compensation_dict[future_mag]
		comment('objective offset correction: {}'.format(move))
		self.move_relative(move)
		self.magnification = future_mag


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

	def get_response(self):
		response = ''
		while '\r' not in response:
			piece = self.ser.read()
			if piece != b'':
				response += piece.decode('utf-8')
		comment('response received from stage:{}'.format(response))
		return response

	def send_receive(self,command):
		self.issue_command(command)
		response = self.get_response()		
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
		response = str(self.send_receive('P'))
		x = int(response.split(',')[0])			
		y = int(response.split(',')[1].split(',')[0])
		position = np.array([x,y])
		return position

	def go_to_position(self,position_vector):
		x = position_vector[0]
		y = position_vector[1]
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
		self.reverse_move_vector = -1*move_vector
		return self.send_receive('GR,{},{}'.format(move_vector[0],move_vector[1]))

	def move_last(self):
		return self.move_relative(self.reverse_move_vector)

	def click_move(self,window_width,window_height,click_x,click_y):
		window_center = np.array([window_width/2,window_height/2])
		mouse_click_location = np.array([click_x,click_y])
		pixel_move_vector = mouse_click_location - window_center
		step_move_vector = pixel_move_vector/self.magnification * self.microns_per_pixel * self.calibration_factor
		step_move_vector = step_move_vector.astype(int)
		comment('click move vector: {}'.format(step_move_vector))
		return self.move_relative(step_move_vector)

	def go_to_dmf_location(self):
		self.lysing_loc = self.get_position()
		self.go_to_position(self.dmf_position)
		self.lysing = False

	def go_to_lysing_loc(self):
		self.go_to_position(self.lysing_loc)
		self.lysing = True

	def toggle_between_dmf_and_lysis(self):
		if self.lysing == True: 
			self.go_to_dmf_location()
		elif self.lysing == False:
			self.go_to_lysing_loc()

if __name__ == '__main__':
	stage = stage_controller()
	print(stage.get_position())

