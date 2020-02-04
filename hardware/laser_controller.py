import serial
import logging

from controllers import ResponseError, BaseController
from presets import SettingValue


class LaserController(BaseController):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.serout_logger = logging.getLogger("{}.SER-OUT".format(__name__))
        self.serin_logger = logging.getLogger("{}.SER-IN".format(__name__))
        self.ready_to_fire = None
        self.ser_url = "hwgrep://FT232R USB UART.*"
        self.ser_settings = {'baudrate': 921600,
                             'timeout': .25,
                             'parity': serial.PARITY_NONE}
        self.command_delimiter = ''

    def setup(self):
        settings = [SettingValue("laser_rep", default_value=1,
                                 changed_call=self.set_pulse_frequency),
                    SettingValue("laser_burst", default_value=1,
                                 changed_call=self.set_burst_counter)
                    ]
        self.vol_settings = {i.name: i for i in settings}

    def start_controller(self):
        self.ser.flushInput()
        self.ser.flushOutput()
        self.ready_to_fire = False
        self.send_receive('d')
        #     set triggering to internal
        self.send_receive('0x')
        #     stop burst
        self.send_receive('d')
        self.send_receive('s')
        self.set_pulse_frequency(1000)
        self.set_burst_counter(1)

    def test_connection(self, connection):
        connection.write('n'.encode('utf-8'))
        self.serout_logger.debug(repr('n'))
        response = connection.readline()
        self.serin_logger.debug(repr(response))
        if response == b'18247\r\n':
            self.logger.info('Laser found at %s', connection.port)
        else:
            raise ResponseError(repr(b'18247\r\n'), repr(response))
        connection.flushInput()
        connection.flushOutput()

    def set_burst_counter(self, count):
        self.send_receive('{}h'.format(int(count)))

    def set_pulse_frequency(self, frequency):
        self.send_receive('{}f'.format(int(frequency)))

    def start_burst(self):
        self.send_receive('e')

    def stop_burst(self):
        self.send_receive('d')


if __name__ == '__main__':
    laser = LaserController()
    laser.init_controller()
    laser.send_receive('s')
    laser.set_burst_counter(20)
    laser.set_pulse_frequency(5)
    laser.start_burst()
