import serial, sys
import numpy as np
from utils import comment
from PyQt5 import QtCore
import time

DEFAULT_INTENSITY = 50


class ExcitationController(QtCore.QObject):
    position_return_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(ExcitationController, self).__init__(parent)
        self.ser = self.get_connection()
        comment(self.send_receive('lh?'))
        comment(self.send_receive(('ip=' + ','.join(['500' for i in range(6)]))))
        self.lamp_index = 0
        self.current_intensity = DEFAULT_INTENSITY
        self.turn_all_off()

    def get_connection(self):
        possible_coms = range(0, 5)
        for com in possible_coms:
            try:
                com = '/dev/ttyACM{}'.format(com)
                parity = serial.PARITY_NONE
                ser = serial.Serial(com, 19200, timeout=.25,
                                    parity=parity)
                ser.write('co\r'.encode('utf-8'))
                response = ser.readline()
                print('response:', response)
                ser.write('sn?\r'.encode('utf-8'))
                response = ser.readline()
                if response == b'223\r':
                    comment('fluorescence controller found on {}'.format(com))
                    return ser
            except Exception as e:
                print(e)
                comment('fluorescence controller not on COM ' + com)
        comment('could not connect to fluorescence controller. exiting...')
        sys.exit(1)

    def get_response(self):
        response = ''
        while '\r' not in response:
            piece = self.ser.read()
            if piece != b'':
                response += piece.decode('utf-8')
        comment('response received from excitation lamp:{}'.format(response))
        return response

    def issue_command(self, command, suppress_msg=False):
        command_string = '{}\r'.format(command)
        if (not suppress_msg):
            comment('sending command to excitation lamp:{}'.format(command_string))
        self.ser.write(command_string.encode('utf-8'))

    def send_receive(self, command, suppress_msg=False):
        self.issue_command(command, suppress_msg)
        response = self.get_response()
        return response

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
        if index == 0:
            self.turn_all_off()
        elif index in range(1, 7):
            self.turn_led_on(index)
        elif index == 7:
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
    fluor.turn_all_off()
    # fluor.turn_led_on(3)
    # fluor.send_receive('0,1,0,0,0,0,0')
    # fluor.send_receive('sn?\r')
