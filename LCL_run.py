import sys,logging,os,time,argparse
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow
from LCL_ui import Ui_MainWindow
from PyQt5 import QtCore 
from PyQt5.QtCore import QThread
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from utils import screen_shooter,now,comment
from stage_controller import stage_controller
from laser_controller import laser_controller, attenuator_controller
import time
import threading
from PyQt5.QtWidgets import QInputDialog, QLineEdit
from autofocus import autofocuser
from localizer import Localizer
import matplotlib.pyplot as plt

class ShowVideo(QtCore.QObject):
		
	VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
	vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')
	reticle_and_center_signal = QtCore.pyqtSignal('PyQt_PyObject','PyQt_PyObject','PyQt_PyObject','PyQt_PyObject')

	def __init__(self, window_size, parent = None):
		super(ShowVideo, self).__init__(parent)
		self.run_video = True				
		self.window_size = window_size
		self.noise_removal = False
		camera_port = 2 + cv2.CAP_DSHOW
		self.camera = cv2.VideoCapture(camera_port)
		self.camera.set(3,1024)#*2) 
		self.camera.set(4,822)
		self.center_x = int(1024/2)
		self.center_y = int(822/2)
		self.reticle_x = int(self.center_x+28)
		self.reticle_y = int(self.center_y+118)

	def draw_reticle(self,image):		
		cv2.circle(image,(self.reticle_x,self.reticle_y),
			5 ,(0,0,0),-1)		
		cv2.circle(image,(self.center_x,self.center_y),5 ,(0,0,0),-1)

	@QtCore.pyqtSlot()
	def startVideo(self):		
		# camera_port = 1 
		#*2) 
		# self.camera.set(15,52.131)
		comment('video properties:')		
		for i in range(19):
			comment('property {}, value: {}'.format(i,
				self.camera.get(i)))
		while self.run_video:			
			ret, image = self.camera.read()
			# image = cv2.cvtColor(image,cv2.COLOR_RGB2BGR)
			self.vid_process_signal.emit(image.copy())			
			# print(cv2.Laplacian(image, cv2.CV_64F).var())
			self.draw_reticle(image)				
			if self.noise_removal == True:
				# print('denoising...')
				# self.camera.set(3,1024) 
				# self.camera.set(4,822) 
				# image = cv2.fastNlMeansDenoisingColored(image,None,3,7,7)
				lab= cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
				l, a, b = cv2.split(lab)
				clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
				cl = clahe.apply(l)
				limg = cv2.merge((cl,a,b))
				image = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
				# print('done denoising')
			color_swapped_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) 			
			height, width, _ = color_swapped_image.shape 
			qt_image = QtGui.QImage(color_swapped_image.data,
									width,
									height,
									color_swapped_image.strides[0],
									QtGui.QImage.Format_RGB888) 
			qt_image = qt_image.scaled(self.window_size)
			self.VideoSignal.emit(qt_image)		
		self.camera.release()
		comment('ending video')

class ImageViewer(QtWidgets.QWidget):
	click_move_signal = QtCore.pyqtSignal('PyQt_PyObject','PyQt_PyObject')

	def __init__(self, parent = None):
		super(ImageViewer, self).__init__(parent)
		self.image = QtGui.QImage()
		self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

	def paintEvent(self, event):
		painter = QtGui.QPainter(self)
		painter.drawImage(0,0, self.image)
		self.image = QtGui.QImage()
 
	@QtCore.pyqtSlot(QtGui.QImage)
	def setImage(self, image):
		if image.isNull():
			comment("Viewer Dropped frame!")		
		self.image = image
		self.update()

	def mousePressEvent(self, QMouseEvent):
		window_height,window_width = self.geometry().height(),self.geometry().width()
		# print(window_height,window_width)
		click_x,click_y = QMouseEvent.pos().x(),QMouseEvent.pos().y()
		# print('clicked: {} {}'.format(QMouseEvent.pos().x(),QMouseEvent.pos().y()))
		self.click_move_signal.emit(click_x,click_y)

class main_window(QMainWindow):
	start_video_signal = QtCore.pyqtSignal()
	qswitch_screenshot_signal = QtCore.pyqtSignal('PyQt_PyObject')
	start_focus_signal = QtCore.pyqtSignal()
	start_localization_signal = QtCore.pyqtSignal()

	def __init__(self,test_run):
		super(main_window, self).__init__()
		self.lysing = True
		# get our experiment variables
		if test_run != 'True':
			self.get_experiment_variables()
			
		# Set up the user interface 
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)	

		# set up the video classes 
		self.vid = ShowVideo(self.ui.verticalLayoutWidget.size())
		self.screen_shooter = screen_shooter()
		self.image_viewer = ImageViewer()
		# self.autofocuser = autofocuser()
		self.localizer = Localizer()		

		# add the viewer to our ui
		self.ui.verticalLayout.addWidget(self.image_viewer)

		# create our extra threads
		self.screenshooter_thread = QThread()
		self.screenshooter_thread.start()
		self.screen_shooter.moveToThread(self.screenshooter_thread)		

		# self.autofocuser_thread = QThread()
		# self.autofocuser_thread.start()
		# self.autofocuser.moveToThread(self.autofocuser_thread)		

		self.localizer_thread = QThread()
		self.localizer_thread.start()
		self.localizer.moveToThread(self.localizer_thread)

		self.video_input_thread = QThread()
		self.video_input_thread.start()
		self.vid.moveToThread(self.video_input_thread)

		# connect the outputs to our signals
		self.vid.VideoSignal.connect(self.image_viewer.setImage)		
		self.vid.vid_process_signal.connect(self.screen_shooter.screenshot_slot)		
		# self.vid.vid_process_signal.connect(self.autofocuser.vid_process_slot)
		self.vid.vid_process_signal.connect(self.localizer.vid_process_slot)
		self.qswitch_screenshot_signal.connect(self.screen_shooter.save_qswitch_fire_slot)
		# self.start_focus_signal.connect(self.autofocuser.autofocus)
		self.start_localization_signal.connect(self.localizer.localize)
		# self.autofocuser.position_and_variance_signal.connect(self.plot_variance_and_position)
		self.image_viewer.click_move_signal.connect(stage.click_move_slot)
		self.localizer.localizer_move_signal.connect(stage.localizer_move_slot)
		self.localizer.ai_fire_qswitch_signal.connect(self.ai_fire_qswitch_slot)
		self.localizer.start_laser_flash_signal.connect(self.start_laser_flash_slot)
		self.localizer.stop_laser_flash_signal.connect(self.stop_laser_flash_slot)
		self.vid.reticle_and_center_signal.connect(stage.reticle_and_center_slot)
		self.vid.reticle_and_center_signal.emit(self.vid.center_x,self.vid.center_y,self.vid.reticle_x,self.vid.reticle_y)

		# connect to the video thread and start the video
		self.start_video_signal.connect(self.vid.startVideo)
		self.start_video_signal.emit()		
		
		# Screenshot and comment buttons
		self.ui.misc_screenshot_button.clicked.connect(self.screen_shooter.save_misc_image)
		self.ui.user_comment_button.clicked.connect(self.send_user_comment)
		self.ui.noise_filter_checkbox.stateChanged.connect(self.noise_filter_check_changed)

		# Stage movement buttons
		self.ui.step_size_doublespin_box.valueChanged.connect(stage.set_step_size)
		self.setup_combobox()
		self.localizer.get_position_signal.connect(stage.get_position_slot)
		stage.position_return_signal.connect(self.localizer.position_return_slot)

		# Laser control buttons		
		self.ui.qswitch_delay_doublespin_box.valueChanged.connect(laser.set_delay)
		self.ui.attenuator_doublespin_box.valueChanged.connect(attenuator.set_attenuation)

		self.ui.cells_to_lyse_doublespin_box.valueChanged.connect(self.localizer.set_cells_to_lyse)
		self.ui.process_well_pushButton.clicked.connect(self.start_localization)
		self.show()		
		comment('finished gui init')	

	def get_text(self,text_prompt):
		text, okPressed = QInputDialog.getText(self, "Experiment Input",text_prompt, QLineEdit.Normal, "")
		if okPressed and text != None:
			return text

	def get_experiment_variables(self):
		var_dict = {'stain(s) used:':'Enter the stain(s) used',
		'cell line:':'Enter the cell line',
		'fixative used:': 'Enter the fixative used'}
		nums = range(10)
		checks = ['a','e','i','o','u'] + [str(num) for num in nums]
		for key, value in var_dict.items():
			good_entry = False
			while good_entry != True:				
				user_input = self.get_text(var_dict[key])
				val = user_input.lower()
				if any(vowel in val for vowel in checks):
					comment('{} {}'.format(key,user_input))
					good_entry = True

	def start_autofocus(self):
		self.start_focus_signal.emit()

	def start_localization(self):
		self.start_localization_signal.emit()

	def noise_filter_check_changed(self,int):
		if self.ui.noise_filter_checkbox.isChecked():
			self.vid.noise_removal = True
		else:
			self.vid.noise_removal = False

	def setup_combobox(self):
		magnifications = [
		'4x',
		'20x',
		'40x',
		'60x',
		'100x']
		self.ui.magnification_combobox.addItems(magnifications)	
		self.ui.magnification_combobox.currentIndexChanged.connect(stage.change_magnification)
		self.ui.cell_type_to_lyse_comboBox.addItems(['red','green'])
		self.ui.cell_type_to_lyse_comboBox.currentIndexChanged.connect(self.localizer.change_type_to_lyse)
		self.ui.lysis_mode_comboBox.addItems(['direct','excision'])	
		self.ui.lysis_mode_comboBox.currentIndexChanged.connect(self.localizer.change_lysis_mode)

	def send_user_comment(self):
		comment('user comment:{}'.format(self.ui.comment_box.toPlainText()))
		self.ui.comment_box.clear()

	@QtCore.pyqtSlot()
	def qswitch_screenshot_slot(self):
		self.qswitch_screenshot_signal.emit(15)
		comment('stage position during qswitch: {}'.format(stage.get_position_slot()))
		laser.fire_qswitch()		
	
	@QtCore.pyqtSlot('PyQt_PyObject')
	def ai_fire_qswitch_slot(self,num_frames):	
		self.qswitch_screenshot_signal.emit(num_frames)
		comment('automated firing from localizer!')
		laser.fire_qswitch()
	
	@QtCore.pyqtSlot()		
	def start_laser_flash_slot(self):
		laser.fire_auto()

	@QtCore.pyqtSlot()
	def stop_laser_flash_slot(self):
		laser.stop_flash()

		
	# def toggle_dmf_or_lysis(self):
	# 	# we want to get our objective out of the way first
	# 	if self.lysing == True: 
	# 		ret = self.autofocuser.retract_objective()			
	# 		if ret == True:
	# 			stage.go_to_dmf_location()
	# 	elif self.lysing == False:
	# 		stage.go_to_lysing_loc()
	# 		self.autofocuser.return_objective_to_focus()	
	# 	self.lysing = not self.lysing		

	def keyPressEvent(self,event):
		if not event.isAutoRepeat():
			print('key pressed {}'.format(event.key()))
			key_control_dict = {
			87:stage.move_up,
			65:stage.move_left,
			83:stage.move_down,
			68:stage.move_right,
			66:stage.move_last,
			16777249:laser.fire_auto,
			70:self.qswitch_screenshot_slot,
			81:laser.qswitch_auto,
			# 73:self.autofocuser.roll_forward,
			# 75:self.autofocuser.roll_backward,
			79:self.start_autofocus,
			# 71:self.toggle_dmf_or_lysis,
			84:stage.move_left_one_well_slot,
			89:stage.move_right_one_well_slot,
			96:self.screen_shooter.save_target_image
			}
			if event.key() in key_control_dict.keys():
				key_control_dict[event.key()]()

	def keyReleaseEvent(self,event):
		if not event.isAutoRepeat():
			# print('key released: {}'.format(event.key()))
			key_control_dict = {
			16777249:laser.stop_flash,
			# 73:self.autofocuser.stop_roll,
			# 75:self.autofocuser.stop_roll
			}
			if event.key() in key_control_dict.keys():
				key_control_dict[event.key()]()

	def closeEvent(self, event):
		self.vid.run_video = False	

	@QtCore.pyqtSlot('PyQt_PyObject')
	def plot_variance_and_position(self,ituple):
		positions = ituple[0]
		variances = ituple[1]
		plt.plot(positions)
		plt.plot(variances)
		plt.legend(['Variance of Laplacian','AF Network Output'])
		plt.xlabel('Position')
		plt.ylabel('Focus Metric Comparison')
		plt.show()

if __name__ == '__main__':	
	parser = argparse.ArgumentParser()
	parser.add_argument('test_run')
	args = parser.parse_args()
	app = QApplication(sys.argv)
	stage = stage_controller()
	attenuator = attenuator_controller()
	laser = laser_controller()	
	window = main_window(args.test_run)	
	comment('exit with code: ' + str(app.exec_()))
	