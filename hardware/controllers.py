import serial
from PyQt5 import QtCore
import logging


class ResponseError(Exception):
    """Exception raised for errors in response received from a controller.

    Attributes:
         expected: The expected response.
         response: The response received.
         message: The message to print.
    """

    def __init__(self, expected, response):
        """

        :param expected: The expected response.
        :param response: The response received.
        """
        self.expected = expected
        self.response = response
        self.message = "Invalid response. Expected: {} Received: {}".format(self.expected, self.response)


class BaseController(QtCore.QObject):
    """
    Base class for serial-driven controllers.
    """
    changed_setting_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(BaseController, self).__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.serout_logger = logging.getLogger("{}.SER-OUT".format(__name__))
        self.serin_logger = logging.getLogger("{}.SER-IN".format(__name__))
        self.ser = None
        self.connected = False
        self.ser_url = None
        self.ser_settings = {'baudrate': 19200,
                             'timeout': .25,
                             'parity': serial.PARITY_NONE}
        self.command_delimiter = "\n"
        self.settings = {}
        self.nonpreset_settings = {}
        self.setup()

    def setup(self):
        pass

    # def connect_to_signal(self, slot: QtCore.pyqtSlot):
    #     self.changed_setting_signal

    def start_controller(self):
        pass

    def init_controller(self):
        self.connected = self.get_connection()
        if self.connected:
            self.start_controller()

    def test_connection(self, connection):
        pass

    def get_connection(self):
        self.logger.info("Trying to connect...")
        if self.ser is not None:
            self.ser.close()
        try:
            ser = serial.serial_for_url(self.ser_url)
            ser.apply_settings(self.ser_settings)
            self.test_connection(ser)
            self.ser = ser
            return True
        except serial.SerialException as e:
            self.logger.warning("Could not open connection: %s", e)
            return False
        except ResponseError as e:
            self.logger.warning(e.message)

    def get_response(self, log: bool = True):
        response = ""
        for line in self.ser:
            response += line.decode("ascii")
        if log:
            self.serin_logger.debug(repr(response))
        return response

    def send_receive(self, command, log: bool = True):
        command_string = command + self.command_delimiter
        if log:
            self.serout_logger.debug(repr(command_string))
        self.ser.write(command_string.encode('utf-8'))
        return self.get_response(log)
