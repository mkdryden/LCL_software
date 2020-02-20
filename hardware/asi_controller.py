import time
import typing
import logging

import serial
from PyQt5 import QtCore

from controllers import BaseController, ResponseError
from presets import SettingValue


class StageController(BaseController):
    done_moving_signal = QtCore.pyqtSignal()
    af_status_signal = QtCore.pyqtSignal(str)

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
        self.af_status_timer = None

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
        self.serin_logger.info("\n".join(self.send_receive("N").splitlines()))
        self.send_receive("AFMOVE Y=1")  # Enable safe objective switching
        self.get_position()

        self.af_status_timer = QtCore.QTimer(self)
        self.af_status_timer.timeout.connect(self.poll_autofocus_status)
        self.af_status_timer.start(400)

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

    def get_cube_position(self):
        pos = self.send_receive('W S')
        pos = pos.split('A ')[1]
        return int(pos) - 1

    def turn_on_autofocus(self):
        self.set_af_state('lock')

    def turn_off_autofocus(self):
        self.set_af_state('ready')

    def calibrate_af(self):
        # to calibrate we want to go idle->ready->log_cal->dither
        # and then we want to display the error continuously on the gui
        self.set_af_state('idle')
        time.sleep(.2)
        self.set_af_state('ready')
        time.sleep(2)
        self.set_af_state('log_cal')
        time.sleep(2)
        self.set_af_state('dither')
        time.sleep(5)
        self.set_af_state('ready')

    @QtCore.pyqtSlot(str)
    def set_focus_state(self, state: str):
        state_dict = {'idle': 79,
                      'ready': 85,
                      'lock': 83,
                      'log_cal': 72,
                      'gain_cal': 67,
                      'dither': 102,
                      }
        self.logger.info('AF: Setting state to %s', state)
        self.send_receive(f'32LK F={state_dict[state]}')

    @QtCore.pyqtSlot()
    def poll_autofocus_status(self) -> str:
        msg = " --- ".join((self.send_receive("32EXTRA X?").strip(),
                        self.send_receive("32EXTRA Y?").strip()))
        self.af_status_signal.emit(msg)
        return msg


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
