import sys
import time
import logging

import serial
import numpy as np
from PyQt5 import QtCore

from controllers import BaseController, ResponseError
from utils import comment


logger = logging.getLogger(__name__)
serout_logger = logging.getLogger("{}.SER-OUT".format(__name__))
serin_logger = logging.getLogger("{}.SER-IN".format(__name__))


class StageController(BaseController):
    position_return_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.serout_logger = serout_logger
        self.serin_logger = serin_logger
        self.ser_url = "hwgrep://CP2102 USB to UART Bridge Controller"
        self.ser_settings = {'baudrate': 115200,
                             'timeout': .25,
                             'parity': serial.PARITY_NONE}
        self.command_delimiter = '\r'

        self.step_size = 500
        self.reverse_move_vector = np.zeros(2)
        self.return_from_dmf_vector = np.zeros(2)
        self.microns_per_pixel = 100 / 34
        self.calibration_factor = 1.20 * 4
        self.steps_between_wells = 4400
        self.down = False
        self.objective_retracted = None
        self.previous_z = None
        self.current_magnification = None
        self.previous_magnification = None
        self.objective_slots = {
            1: 'None',
            2: 40,
            3: 'None',
            4: 60,
            5: 'None',
            6: 20
        }
        self.objective_calibration_factors = {
            20: 1,
            40: 0.51,
            60: .36,
            100: 0.205}

    def start_controller(self):
        self.send_receive('B X=0 Y=0')  # turn off backlash compensation on XY
        self.send_receive('7TTL Y=0')  # set TTL low
        self.current_magnification = self.objective_slots[self.get_objective_position() + 1]

    def test_connection(self, connection):
        connection.write('BU\r'.encode('utf-8'))
        self.serout_logger.debug(repr('BU\r'))
        response = connection.readline()
        self.serin_logger.debug(repr(response))
        if response == b'TIGER_COMM\r\n':
            self.logger.info('ASI controller found at %s', connection.port)
        else:
            raise ResponseError(repr(b'TIGER_COMM\r\n'), repr(response))
        connection.flushInput()
        connection.flushOutput()

    @QtCore.pyqtSlot()
    def get_all_positions(self):
        positions = self.send_receive('W X Y Z')
        cleaned = positions.replace('\r', '').split(' ')[1:-1]
        self.x, self.y, self.z = [int(x) for x in cleaned]
        self.position_return_signal.emit(np.array([self.x, self.y]))
        return self.x, self.y, self.z

    def move(self, x=None, y=None, z=None):
        cmd_string = 'M'
        for direction, var in zip(['X', 'Y', 'Z'], [x, y, z]):
            if var is not None:
                cmd_string += f' {direction}={var}'
        self.send_receive(cmd_string)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def localizer_stage_command_slot(self, command):
        self.send_receive(command)

    def get_is_objective_retracted(self):
        pos = int(self.send_receive('W Z').split(':A ')[1])
        # up is negative. ~95000 is in focus for 20x
        if pos > -30000:
            comment('objective is retracted')
            self.objective_retracted = True
            return True
        elif pos < -30000:
            comment('objective is down')
            self.objective_retracted = False
            return False

    def toggle_objective_retraction(self):
        if self.objective_retracted:
            self.set_objective_down()
        elif not self.objective_retracted:
            self.pull_objective_up()
        self.objective_retracted = not self.objective_retracted

    def pull_objective_up(self):
        _, _, self.previous_z = self.get_all_positions()
        self.move(z=0)
        while 'N' not in self.send_receive('STATUS'):
            time.sleep(.5)

    def set_objective_down(self, ):
        # IF Z is zero at the top of travel:
        # 60x in focus at -69996
        # 40x in focus at -126151
        # 20x in focus at -126151
        focus_dict = {20: -126151,
                      40: -124000,
                      60: -69996}
        self.move(z=focus_dict[self.current_magnification])

    def change_magnification(self, index):
        self.previous_magnification = self.current_magnification
        self.current_magnification = self.objective_slots[index + 1]
        self.compensate_for_objective_offsets(self.previous_magnification, self.current_magnification)
        up = self.get_is_objective_retracted()
        # if we are up, stay up, if we are down, pull up, change, then go down
        if up:
            self.send_receive('MOVE O={}'.format(index + 1))
        else:
            self.pull_objective_up()
            self.send_receive('MOVE O={}'.format(index + 1))
            self.set_objective_down()
        comment(f'magnification changed to: {self.current_magnification}')

    @QtCore.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
    def reticle_and_center_slot(self, center_x, center_y, reticle_x, reticle_y):
        self.center_x = center_x
        self.center_y = center_y
        self.reticle_x = reticle_x
        self.reticle_y = reticle_y

    def change_cube_position(self, index):
        self.send_receive('MOVE S={}'.format(index + 1))

    def compensate_for_objective_offsets(self, present_mag, future_mag):
        # from 20 to 40: X=132.192 Y=717.264
        # X=1157.76 Y=260.928 + X=1157.76 Y=260.928 + X=-77.76 Y=596.16
        compensation_dict = {
            20: np.zeros(2),
            40: np.array([849, -335]),
            60: np.array([2897, 75]),
        }
        # get back to 4 first
        move = -1 * compensation_dict[present_mag]
        # now compensate for offsets from 4
        move = move + compensation_dict[future_mag]
        comment('objective offset correction: {}'.format(move))
        self.move_relative(move)

    def set_step_size(self, step_size):
        comment('step size changed to: {}'.format(step_size))
        self.step_size = step_size * 10

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

    def move_rel_z(self, z):
        return self.send_receive(f'R Z={z}')

    def move_last(self):
        return self.move_relative(self.reverse_move_vector)

    def scale_move_vector(self, vector):
        default_calibration = 4.8
        return np.round(vector * default_calibration * self.objective_calibration_factors[self.current_magnification],
                        4)

    def click_move_slot(self, click_x, click_y):
        # center movement:
        window_center = np.array([1352 / 2, 712 / 2])
        # # reticle movement:
        # window_center = np.array([self.reticle_x * 1352 / 4096, self.reticle_y * 712 / 2160])
        mouse_click_location = np.array([click_x, click_y])
        pixel_move_vector = mouse_click_location - window_center
        step_move_vector = self.scale_move_vector(pixel_move_vector)
        return self.move_relative(step_move_vector)

    @QtCore.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
    def localizer_move_slot(self, move_vector, goto_reticle=False, move_relative=True, scale_vector=True):
        if move_relative is True and scale_vector == True:
            if goto_reticle == True:
                center = np.array([self.center_x, self.center_y])
                reticle = np.array([self.reticle_x, self.reticle_y])
                center_to_reticle = center - reticle
                move_vector += center_to_reticle
            move_vector = self.scale_move_vector(move_vector)
            self.move_relative(move_vector)
        elif move_relative is False and scale_vector is False:
            print('MOVING')
            self.move(x=move_vector[0], y=move_vector[1])
        elif move_relative is False and scale_vector is True:
            move_vector = self.scale_move_vector(move_vector)
            self.move(x=move_vector[0], y=move_vector[1])
        elif move_relative is True and scale_vector is False:
            self.move_relative(move_vector)

    # zoom and recenter gui signals
    @QtCore.pyqtSlot('PyQt_PyObject')
    def zoom_and_move_slot(self, move_vector):
        if move_vector[0] == 0 and move_vector[1] == 0:
            return
        pixel_move_vector = np.array([move_vector[0], move_vector[1]])
        step_move_vector = self.scale_move_vector(pixel_move_vector)
        self.move_relative(step_move_vector)

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

    def turn_on_autofocus(self):
        self.set_focus_state('lock')

    def turn_off_autofocus(self):
        self.set_focus_state('ready')

    def calibrate_af(self):
        # to calibrate we want to go idle->ready->log_cal->dither
        # and then we want to display the error continuously on the gui
        self.set_focus_state('idle')
        time.sleep(.2)
        self.set_focus_state('ready')
        time.sleep(2)
        self.set_focus_state('log_cal')
        time.sleep(2)
        self.set_focus_state('dither')
        time.sleep(5)
        self.set_focus_state('ready')

    def send_ttl_pulse(self):
        comment(self.send_receive('7TTL Y=1'))
        comment(self.send_receive('7TTL Y=0'))

    def set_focus_state(self, state):
        state_dict = {'idle': 79,
                      'ready': 85,
                      'lock': 83,
                      'log_cal': 72,
                      'dither': 102,
                      }
        comment('setting focus state:{}'.format(state))
        self.send_receive('LK F={}'.format(state_dict[state]))


if __name__ == '__main__':
    stage = StageController()
    stage.get_all_positions()
    # stage.send_receive('P X? Y? Z?')
    # stage.send_receive('HERE Z')
