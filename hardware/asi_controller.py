import time
import typing
import logging

import serial
import numpy as np
from PyQt5 import QtCore

from controllers import BaseController, ResponseError
from presets import SettingValue
from utils import comment


class StageController(BaseController):
    position_return_signal = QtCore.pyqtSignal('PyQt_PyObject')
    done_moving_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.serout_logger = logging.getLogger("{}.SER-OUT".format(__name__))
        self.serin_logger = logging.getLogger("{}.SER-IN".format(__name__))
        self.ser_url = "hwgrep://CP2102 USB to UART Bridge Controller"
        self.ser_settings = {'baudrate': 115200,
                             'timeout': .25,
                             'parity': serial.PARITY_NONE}
        self.command_delimiter = '\r'

        self.position = None
        self.status_timer = None

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

    def setup(self):
        settings = [SettingValue("brightness", default_value=10,
                                 changed_call=self.change_brightness),
                    SettingValue("cube_position", default_value=1,
                                 changed_call=self.change_cube_position,
                                 change_done_signal=self.done_moving_signal)
                    ]
        self.settings = {i.name: i for i in settings}

    def start_controller(self):
        self.status_timer = QtCore.QTimer(self)
        self.status_timer.timeout.connect(self.is_moving)

        self.send_receive('B X=0 Y=0')  # turn off backlash compensation on XY
        self.send_receive('7TTL Y=0')  # set TTL low
        self.serin_logger.info(self.send_receive("AFMOVE Y=1"))  # Enable safe objective switching
        self.get_position()

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
    def get_position(self) -> typing.Tuple[int, int, int]:
        positions = self.send_receive('W X Y Z')
        cleaned = positions.replace('\r', '').split(' ')[1:-1]
        self.position = tuple(int(x) for x in cleaned)
        self.position_return_signal.emit(self.position)
        return self.position

    def is_moving(self):
        reply = self.send_receive('/').strip()
        if reply == 'B':
            return True
        elif reply == 'N':
            self.logger.info("Done move")
            self.status_timer.stop()
            self.get_position()
            self.done_moving_signal.emit()
            return False
        else:
            self.logger.error("Received invalid STATUS response: %s", reply)
            return None

    def move(self, x: int = None, y: int = None, z: int = None, check_status: bool = True):
        """
        Move to absolute coordinates in tenths of um.
        :param x: x position
        :param y: y position
        :param z: z position
        :param check_status: If True, will call is_moving to check controller status.
        :return:
        """
        cmd_string = 'M'
        for direction, var in zip(['X', 'Y', 'Z'], [x, y, z]):
            if var is not None:
                cmd_string += f' {direction}={var}'
        self.send_receive(cmd_string)
        if check_status:
            self.status_timer.start(100)

    def move_rel(self, x: int = None, y: int = None, z: int = None, check_status: bool = True):
        """
        Move to relative coordinates in tenths of um.
        :param x: x position
        :param y: y position
        :param z: z position
        :param check_status: If True, will call is_moving to check controller status.
        :return:
        """
        cmd_string = 'R'
        for direction, var in zip(['X', 'Y', 'Z'], [x, y, z]):
            if var is not None:
                cmd_string += f' {direction}={var}'
        self.send_receive(cmd_string)
        if check_status:
            self.status_timer.start(100)

    def set_objective_position(self, index: int):
        """
        Set objective by index (0-indexed)
        :param index: 0-indexed objective position
        """
        self.send_receive('M O={}'.format(index + 1))
        self.status_timer.start(100)

    def get_objective_position(self) -> int:
        """
        Returns 0-indexed objective position
        :return: 0-indexed objective position
        """
        pos = self.send_receive('W O')
        pos = pos.split('A ')[1]
        return int(pos) - 1

    def change_cube_position(self, index):
        self.send_receive('MOVE S={}'.format(index + 1))
        self.status_timer.start(100)

    def change_brightness(self, value):
        self.logger.info('setting brightness to %s', value)
        self.send_receive('7LED X={}'.format(value))

    @QtCore.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
    def localizer_move_slot(self, move_vector, goto_reticle=False, move_relative=True, scale_vector=True):
        if move_relative and scale_vector:
            if goto_reticle:
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
    root_logger = logging.getLogger()
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    log_handlers = [logging.StreamHandler()]
    log_formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s: [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    for handler in log_handlers:
        handler.setFormatter(log_formatter)
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    stage = StageController()
    stage.init_controller()
    stage.get_position()
    stage.send_receive('HERE S=0 O=0')  # Zeros objective and filter cube to position 1
    # stage.send_receive('P X? Y? Z?')
    # stage.send_receive('HERE Z')
