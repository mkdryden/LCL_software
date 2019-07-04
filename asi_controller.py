import future
import serial, sys
import numpy as np
from utils import comment
from PyQt5 import QtCore
import time


# sudo chmod o+rw /dev/ttyUSB0
class StageController(QtCore.QObject):
    position_return_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        '''
        open the serial port and check the status of the stage
        '''
        super(StageController, self).__init__(parent)
        self.ser = self.get_connection()
        self.step_size = 500
        self.reverse_move_vector = np.zeros(2)
        self.return_from_dmf_vector = np.zeros(2)
        self.magnification = 4
        self.microns_per_pixel = 100 / 34
        self.calibration_factor = 1.20 * 4
        # self.lysing_loc = self.get_position_slot()
        self.lysing = True
        # turning off backlash
        comment(self.send_receive('B X=0 Y=0 Z=0'))
        # setting TTL low
        comment(self.send_receive('7TTL Y=0'))
        self.steps_between_wells = 4400
        self.down = False
        self.objective_retracted = None
        self.previous_z = None
        self.objective_slots = {
            1: 20,
            2: 40,
            3: 100,
            4: 'None',
            5: 'None'
        }
        self.objective_calibration_factors = {
            20: 1,
            40: 0.51,
            100: 0.205}
        self.current_magnification = self.objective_slots[self.get_objective_position() + 1]

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

    def get_is_objective_retracted(self):
        pos = int(self.send_receive('W Z').split(':A ')[1])
        # up is negative. ~95000 is in focus for 20x
        if pos > -80000:
            comment('objective is retracted on startup')
            self.objective_retracted = True
            return True
        elif pos < -80000:
            comment('objective is down on startup')
            self.objective_retracted = False
            return False

    def toggle_objective_retraction(self):
        if self.objective_retracted:
            self.set_objective_down()
        elif not self.objective_retracted:
            self.pull_objective_up()
        self.objective_retracted = not self.objective_retracted

    def get_connection(self):
        possible_coms = range(0, 5)
        for com in possible_coms:
            try:
                com = '/dev/ttyUSB{}'.format(com)
                parity = serial.PARITY_NONE
                ser = serial.Serial(com, 115200, timeout=.25,
                                    parity=parity)
                ser.write('BU\r'.encode('utf-8'))
                response = ser.readline()
                if response == b'TIGER_COMM\r\n':
                    comment('asi controller found on {}'.format(com))
                    return ser
            except Exception as e:
                print(e)
                comment('asi controller not on COM ' + com)
        comment('could not connect to asi controller. exiting...')
        sys.exit(1)

    @QtCore.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
    def reticle_and_center_slot(self, center_x, center_y, reticle_x, reticle_y):
        self.center_x = center_x
        self.center_y = center_y
        self.reticle_x = reticle_x
        self.reticle_y = reticle_y

    def change_magnification(self, index):
        self.pull_objective_up()
        self.send_receive('MOVE O={}'.format(index + 1))
        self.set_objective_down()
        self.current_magnification = self.objective_slots[index + 1]
        comment(f'magnification changed to: {self.current_magnification}')
        # self.compensate_for_objective_offsets(self.magnification, map_dict[index + 1])

    def change_cube_position(self, index):
        self.send_receive('MOVE S={}'.format(index + 1))

    # def compensate_for_objective_offsets(self, present_mag, future_mag):
    #     compensation_dict = {
    #         4: np.zeros(2),
    #         20: np.array([-67, -115]),
    #         40: np.array([-78, -124]),
    #         60: np.array([-74, -132]),
    #         100: np.array([-79, -139])
    #     }
    #     # get back to 4 first
    #     move = -1 * compensation_dict[present_mag]
    #     # now compensate for offsets from 4
    #     move = move + compensation_dict[future_mag]
    #     comment('objective offset correction: {}'.format(move))
    #     self.move_relative(move)
    #     self.magnification = future_mag

    def set_step_size(self, step_size):
        comment('step size changed to: {}'.format(step_size))
        self.step_size = step_size * 10

    def issue_command(self, command, suppress_msg=False):
        command_string = '{}\r'.format(command)
        if not suppress_msg:
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

    # @QtCore.pyqtSlot()
    # def get_position_slot(self):
    #     x = str(self.send_receive('W X')).split('A ')[1].split('\r')[0]
    #     y = str(self.send_receive('W Y')).split('A ')[1].split('\r')[0]
    #     position = np.array([int(x), int(y)])
    #     self.position_return_signal.emit(position)
    #     return position

    # def go_to_position(self, position_vector):
    #     x = position_vector[0]
    #     y = position_vector[1]
    #     return self.send_receive('MOVE X={} Y={}'.format(x, y))

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
            # print(move_vector)
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

    def pull_objective_up(self):
        _, _, self.previous_z = self.get_all_positions()
        self.move(z=0)
        while 'N' not in self.send_receive('STATUS'):
            time.sleep(.5)

    def set_objective_down(self):
        self.move(z=self.previous_z)

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
