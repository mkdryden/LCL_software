import serial
import numpy as np
from utils import comment
from PyQt5 import QtCore
import time


# sudo chmod o+rw /dev/ttyUSB0
class stage_controller(QtCore.QObject):
    position_return_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        '''
        open the serial port and check the status of the stage
        '''
        super(stage_controller, self).__init__(parent)
        com = '/dev/ttyUSB0'
        baud = 115200
        parity = serial.PARITY_NONE
        self.ser = serial.Serial(com, baud, timeout=.25,
                                 parity=parity)
        self.step_size = 5
        self.reverse_move_vector = np.zeros(2)
        self.return_from_dmf_vector = np.zeros(2)
        self.magnification = 4
        self.microns_per_pixel = 100 / 34
        self.calibration_factor = 1.20 * 4
        self.lysing_loc = self.get_position_slot()
        self.lysing = True
        self.send_receive('B X=0 Y=0 Z=0')
        self.steps_between_wells = 4400
        self.down = False

    @QtCore.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
    def reticle_and_center_slot(self, center_x, center_y, reticle_x, reticle_y):
        self.center_x = center_x
        self.center_y = center_y
        self.reticle_x = reticle_x
        self.reticle_y = reticle_y

    def change_magnification(self, index):
        map_dict = {
            1: 20,
            2: 40,
            3: 60,
        }
        self.pull_objective_up()
        self.send_receive('MOVE O={}'.format(index + 1))
        self.set_objective_down()
        comment('magnification changed to: {}'.format(map_dict[index + 1]))
        self.compensate_for_objective_offsets(self.magnification, map_dict[index + 1])

    def change_cube_position(self, index):
        self.send_receive('MOVE S={}'.format(index + 1))

    def compensate_for_objective_offsets(self, present_mag, future_mag):
        compensation_dict = {
            4: np.zeros(2),
            20: np.array([-67, -115]),
            40: np.array([-78, -124]),
            60: np.array([-74, -132]),
            100: np.array([-79, -139])
        }
        # get back to 4 first
        move = -1 * compensation_dict[present_mag]
        # now compensate for offsets from 4
        move = move + compensation_dict[future_mag]
        comment('objective offset correction: {}'.format(move))
        self.move_relative(move)
        self.magnification = future_mag

    def set_step_size(self, step_size):
        comment('step size changed to: {}'.format(step_size))
        self.step_size = step_size

    def issue_command(self, command, suppress_msg=False):
        '''
        sends command and handles any errors from stage
        '''
        command_string = '{}\r'.format(command)
        if (not suppress_msg):
            comment('sending command to stage:{}'.format(command_string))
        self.ser.write(command_string.encode('utf-8'))

    def get_response(self):
        response = ''
        while '\r' not in response:
            piece = self.ser.read()
            if piece != b'':
                response += piece.decode('utf-8')
        comment('response received from stage:{}'.format(response))
        return response

    def send_receive(self, command, suppress_msg=False):
        self.issue_command(command, suppress_msg)
        response = self.get_response()
        return response

    def get_status(self):
        response = self.send_receive('STATUS')
        return response

    def home_stage(self):
        # hits the limit switches and then returns to last known location
        return self.send_receive('HOME')

    @QtCore.pyqtSlot()
    def get_position_slot(self):
        x = str(self.send_receive('W X')).split('A ')[1].split('\r')[0]
        y = str(self.send_receive('W Y')).split('A ')[1].split('\r')[0]
        position = np.array([int(x), int(y)])
        self.position_return_signal.emit(position)
        return position

    def go_to_position(self, position_vector):
        x = position_vector[0]
        y = position_vector[1]
        return self.send_receive('MOVE X={} Y={}'.format(x, y))

    def move_up(self):
        return self.send_receive('R Y=-{}'.format(self.step_size))

    def move_down(self):
        return self.send_receive('R Y={}'.format(self.step_size))

    def move_right(self):
        return self.send_receive('R X={}'.format(self.step_size))

    def move_left(self):
        return self.send_receive('R X=-{}'.format(self.step_size))

    def move_relative(self, move_vector):
        self.reverse_move_vector = -1 * move_vector
        return self.send_receive('R X={} Y={}'.format(move_vector[0], move_vector[1]))

    def move_last(self):
        return self.move_relative(self.reverse_move_vector)

    def remove_calibrated_error(self, x, y):
        # an attempt to calibrate out some error...
        if self.magnification == 4:
            x_error = -.036 * x + 5.5586
            x += x_error
            y_error = -.0573 * y - 5.1509
            y += y_error
        # elif sel

        return np.array([int(x), int(y)])

    def scale_move_vector(self, vector):
        return vector / self.magnification * self.microns_per_pixel * self.calibration_factor

    def click_move_slot(self, click_x, click_y):
        # center movement:
        # window_center = np.array([851/2,681/2])
        # reticle movement:
        window_center = np.array([self.reticle_x * 851 / 1024, self.reticle_y * 681 / 822])
        mouse_click_location = np.array([click_x, click_y])
        pixel_move_vector = mouse_click_location - window_center
        step_move_vector = self.scale_move_vector(pixel_move_vector)
        step_move_vector = self.remove_calibrated_error(step_move_vector[0], step_move_vector[1])
        comment('click move vector: {}'.format(step_move_vector))
        return self.move_relative(step_move_vector)

    @QtCore.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
    def localizer_move_slot(self, move_vector, goto_reticle=False, move_relative=True, scale_vector=True):
        if move_relative == True and scale_vector == True:
            if goto_reticle == True:
                center = np.array([self.center_x, self.center_y])
                reticle = np.array([self.reticle_x, self.reticle_y])
                center_to_reticle = center - reticle
                move_vector += center_to_reticle
            move_vector = self.scale_move_vector(move_vector)
            self.move_relative(move_vector)
        elif move_relative == False and scale_vector == False:
            # print(move_vector)
            self.go_to_position(move_vector)
        elif move_relative == True and scale_vector == False:
            self.move_relative(move_vector)

    # zoom and recenter gui signals
    @QtCore.pyqtSlot('PyQt_PyObject')
    def zoom_and_move_slot(self, move_vector):
        if move_vector[0] == 0 and move_vector[1] == 0:
            return
        pixel_move_vector = np.array([move_vector[0], move_vector[1]])
        step_move_vector = self.scale_move_vector(pixel_move_vector)
        self.move_relative(step_move_vector)

    def go_to_dmf_location(self):
        self.lysing_loc = self.get_position_slot()
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

    def move_right_one_well_slot(self):
        self.move_relative(np.array([self.steps_between_wells, 0]))

    def move_left_one_well_slot(self):
        self.move_relative(np.array([-self.steps_between_wells, 0]))

    def get_objective_position(self):
        pos = self.send_receive('W O')
        pos = pos.split('A ')[1]
        return int(pos) - 1

    def get_cube_position(self):
        pos = self.send_receive('W S')
        pos = pos.split('A ')[1]
        return int(pos) - 1

    def pull_objective_up(self):
        self.send_receive('R Z=50000')
        while 'N' not in self.send_receive('STATUS'):
            time.sleep(1)

    def set_objective_down(self):
        self.send_receive('R Z=-50000')

    def turn_on_autofocus(self):
        self.send_receive('LK F=72')
        self.send_receive('LK F=102')
        self.send_receive('LK F=67')
        # self.send_receive('LK F=79')
        self.send_receive('LK F=83')
        # time.sleep(5)
        # self.send_receive('LK F=67')

    def turn_off_autofocus(self):
        self.send_receive('LK F=85')



if __name__ == '__main__':
    stage = stage_controller()
    # print(stage.send_receive('R Z=100000'))
    # print(stage.send_receive('LK F=102'))
    print(stage.send_receive('LK F=97'))
    # print(stage.get_objective_position())
