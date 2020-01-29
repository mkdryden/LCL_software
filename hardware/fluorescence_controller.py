import logging

from PyQt5 import QtCore
import serial

from controllers import ResponseError, BaseController
from presets import SettingValue

DEFAULT_INTENSITY = 50

wavelengths = ["Off", "385 nm", "430 nm", "475 nm", "525 nm", "575 nm", "630 nm", "All"]
wl_to_idx = {i: n for n, i in enumerate(wavelengths)}
idx_to_wl = {n: i for n, i in enumerate(wavelengths)}


class ExcitationController(BaseController):
    position_return_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.serout_logger = logging.getLogger("{}.SER-OUT".format(__name__))
        self.serin_logger = logging.getLogger("{}.SER-IN".format(__name__))
        self.lamp_index = None
        self.current_intensity = None
        self.ser_url = "hwgrep://X-Cite.*"
        self.ser_settings = {'baudrate': 19200,
                             'timeout': .1,
                             'parity': serial.PARITY_NONE}
        self.command_delimiter = '\r'

    def setup(self):
        settings = [SettingValue("excitation",
                                 default_value=0,
                                 changed_call=self.change_fluorescence),
                    SettingValue("emission",
                                 default_value=0),
                    SettingValue("intensity",
                                 default_value=0,
                                 changed_call=self.change_intensity)
                    ]
        self.settings = {i.name: i for i in settings}

    def start_controller(self):
        self.send_receive('lh?')
        self.send_receive('ip=' + ','.join(['500'] * 6))
        self.lamp_index = 0
        self.current_intensity = DEFAULT_INTENSITY
        self.turn_all_off()
        
    def test_connection(self, connection):
        connection.write('co\r'.encode('utf-8'))
        response = connection.readline()
        self.serin_logger.debug(response)
        connection.write('sn?\r'.encode('utf-8'))
        response = connection.readline()
        self.serin_logger.debug(response)
        if response == b'223\r':
            self.logger.info('Fluorescence controller found at %s', connection.port)
        else:
            raise ResponseError(repr(b'223\r'), repr(response))

    def turn_led_on(self, led):
        self.send_receive('on=' + str(led))
        self.send_receive('on?')
        self.send_receive('ip?')

    def turn_all_off(self):
        self.send_receive('of=a')
        self.send_receive('on?')

    def change_fluorescence(self, index):
        self.turn_all_off()
        self.lamp_index = index
        self.change_intensity(self.current_intensity)
        if self.lamp_index == 0:
            self.turn_all_off()
        elif self.lamp_index in range(1, 7):
            self.turn_led_on(self.lamp_index)
        elif self.lamp_index == 7:
            self.turn_all_on()

    def change_intensity(self, intensity):
        self.current_intensity = intensity
        if self.lamp_index == 0: return
        intensity *= 10
        cmd_string = 'ip=' + ',' * (self.lamp_index - 1) + str(int(intensity))
        self.send_receive(cmd_string)
        self.send_receive('ip?')

    def turn_all_on(self):
        self.send_receive('ip=' + ','.join([str(self.current_intensity) for _ in range(6)]))
        self.send_receive('on=a')
        self.send_receive('on?')


if __name__ == '__main__':
    fluor = ExcitationController()
    fluor.init_controller()
    fluor.turn_all_off()
    # fluor.turn_led_on(3)
    # fluor.send_receive('0,1,0,0,0,0,0')
    # fluor.send_receive('sn?\r')
