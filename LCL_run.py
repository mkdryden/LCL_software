import sys,logging,os
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow
from LCL_ui import Ui_MainWindow
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from utils import screen_shooter,now,comment
from stage_controller import stage_controller
from image_movement_controller import image_based_movement_controller
from laser_controller import laser_controller, attenuator_controller

class ShowVideo(QtCore.QObject):
	camera_port = 1 
	# camera_port = 0 + cv2.CAP_DSHOW
	camera = cv2.VideoCapture(camera_port)
	VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
	screenshot_signal = QtCore.pyqtSignal('PyQt_PyObject')

	def __init__(self, parent = None):
		super(ShowVideo, self).__init__(parent)
		self.run_video = True
		
	@QtCore.pyqtSlot()
	def startVideo(self):		
		comment('video properties:')
		self.camera.set(3,1024) 
		self.camera.set(4,822) 
		self.camera.set(15,52.131)
		for i in range(19):
			comment('property {}, value: {}'.format(i,
				self.camera.get(i)))
		while self.run_video:
			ret, image = self.camera.read()
			image = cv2.cvtColor(image,cv2.COLOR_RGB2BGR)
			self.screenshot_signal.emit(image)			
			radius = 50
			y = int(image.shape[0]/2)
			x = int(image.shape[1]/2)
			cv2.line(image,(x-radius,y),(x+radius,y),(255,0,0),2)
			cv2.line(image,(x,y+radius),(x,y-radius),(255,0,0),2)
			color_swapped_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) 			
			height, width, _ = color_swapped_image.shape 
			qt_image = QtGui.QImage(color_swapped_image.data,
									width,
									height,
									color_swapped_image.strides[0],
									QtGui.QImage.Format_RGB888) 
			self.VideoSignal.emit(qt_image)			
			QApplication.processEvents()
		self.camera.release()
		comment('ending video')


class ImageViewer(QtWidgets.QWidget):
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
		self.image = self.resize_dynamically(image)
		self.update()
	
	def resize_dynamically(self,image):
		return image.scaled(window.ui.verticalLayoutWidget.size())

	def mousePressEvent(self, QMouseEvent):
		window_height,window_width = self.geometry().height(),self.geometry().width()
		click_x,click_y = QMouseEvent.pos().x(),QMouseEvent.pos().y()
		stage.click_move(window_width,window_height,click_x,click_y)

class main_window(QMainWindow):
	def __init__(self):
		super(main_window, self).__init__()

		# set up the video classes 
		self.vid = ShowVideo()
		self.image_viewer = ImageViewer()
		self.vid.VideoSignal.connect(self.image_viewer.setImage)
		self.screen_shooter = screen_shooter()
		self.vid.screenshot_signal.connect(self.screen_shooter.screenshot_slot)

		# Set up the user interface from Designer.
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)	

		# Make some local modifications.
		self.ui.verticalLayout.addWidget(self.image_viewer)

		# Screenshot and comment buttons
		self.ui.target_screenshot_button.clicked.connect(self.screen_shooter.save_target_image)			
		self.ui.non_target_screenshot_button.clicked.connect(self.screen_shooter.save_non_target_image)					
		self.ui.misc_screenshot_button.clicked.connect(self.screen_shooter.save_misc_image)
		self.ui.user_comment_button.clicked.connect(self.send_user_comment)
		# Stage movement buttons
		self.ui.left_button.clicked.connect(stage.move_left)
		self.ui.right_button.clicked.connect(stage.move_right)
		self.ui.down_button.clicked.connect(stage.move_down)
		self.ui.up_button.clicked.connect(stage.move_up)
		self.ui.get_position_button.clicked.connect(stage.get_position)
		self.ui.home_stage_button.clicked.connect(stage.home_stage)		
		self.ui.step_size_doublespin_box.valueChanged.connect(stage.set_step_size)
		self.ui.upper_left_calibration_button.clicked.connect(stage.calibrate_upper_left)
		self.ui.bottom_left_calibration_button.clicked.connect(stage.calibrate_bottom_left)
		self.ui.bottom_right_calibration_button.clicked.connect(stage.calibrate_bottom_right)
		self.setup_combobox()

		self.ui.load_image_pushbutton.clicked.connect(image_move_controller.show_file_dialog)

		self.ui.start_flashlamp_pushbutton.clicked.connect(laser.fire_auto)
		self.ui.stop_flashlamp_pushbutton.clicked.connect(laser.simmer)
		self.ui.fire_qswitch_pushbutton.clicked.connect(laser.fire_qswitch)
		# connect the fire qswitch button to the 'take shot screenshot'
		self.ui.fire_qswitch_pushbutton.clicked.connect(self.qswitch_screenshot_manager)
		self.ui.qswitch_delay_doublespin_box.valueChanged.connect(laser.set_delay)
		self.ui.attenuator_doublespin_box.valueChanged.connect(attenuator.set_attenuation)
		self.show()
		comment('finished gui init')	

	def setup_combobox(self):
		magnifications = [
		'4x',
		'20x',
		'40x',
		'60x',
		'100x']
		self.ui.magnification_combobox.addItems(magnifications)	
		self.ui.magnification_combobox.currentIndexChanged.connect(stage.change_magnification)

	def send_user_comment(self):
		comment('user comment:{}'.format(self.ui.comment_box.toPlainText()))
		self.ui.comment_box.clear()

	def qswitch_screenshot_manager(self):
		# we want to ensure that a screenshot is taken before and after each laser shot
		self.screen_shooter.save_before_qswitch_fire()		
		laser.fire_qswitch()
		self.screen_shooter.save_after_qswitch_fire()


	def keyPressEvent(self,event):
		print('key pressed {}'.format(event.key()))
		key_control_dict = {
		87:stage.move_up,
		65:stage.move_left,
		83:stage.move_down,
		68:stage.move_right,
		66:stage.move_last,
		16777249:laser.fire_auto,
		70:self.qswitch_screenshot_manager,
		81:laser.qswitch_auto
		}
		if event.key() in key_control_dict.keys():
			key_control_dict[event.key()]()

	def keyReleaseEvent(self,event):
		print('key released: {}'.format(event.key()))
		key_control_dict = {
		16777249:laser.stop_flash
		}
		if event.key() in key_control_dict.keys():
			key_control_dict[event.key()]()

	def closeEvent(self, event):
		self.vid.run_video = False	

if __name__ == '__main__':	
	app = QApplication(sys.argv)
	stage = stage_controller()
	image_move_controller = image_based_movement_controller()
	attenuator = attenuator_controller()
	laser = laser_controller()
	window = main_window()
	window.vid.startVideo()
	comment('exit with code: ' + str(app.exec_()))
	sys.exit()