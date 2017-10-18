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
		self.calibration = calibration_manager()
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
		response = str(self.send_receive('P'))
		x = int(response.split(',')[0].split('\'')[1])
		y = int(response.split(',')[1].split(',')[0])
		position = np.array([x,y])
		return position

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

	@QtCore.pyqtSlot()
	def calibrate_bottom_left(self):
		position = self.get_position()
		self.calibration.set_datum('bottom left',position)


	@QtCore.pyqtSlot()
	def calibrate_upper_left(self):
		self.calibration.set_datum('upper left',self.get_position())

	@QtCore.pyqtSlot()
	def calibrate_bottom_right(self):
		self.calibration.set_datum('bottom right',self.get_position())

class calibration_manager():
	
	def __init__(self):		
		self.datum = {
		'upper left':np.array([-1,-1]),
		'bottom left':np.array([-1,-1]),
		'bottom right':np.array([-1,-1])}

	def set_datum(self,datum,position):
		self.datum[datum] = position
		for value in self.datum.values():
			if  -1 in value: return
		if self.check_calibration:
			comment('fully calibrated {}'.format(self.datum)) 
		else:
			comment('calibration error.  need to re-calibrate')

	def check_calibration(self):
		# TODO implement this...
		return True

if __name__ == '__main__':
	stage = stage_controller()
	stage_controller.home_stage(stage)


