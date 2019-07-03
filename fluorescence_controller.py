import serial
import numpy as np
from utils import comment
from PyQt5 import QtCore
import time

DEFAULT_INTENSITY = 50

class ExcitationController(QtCore.QObject):
    position_return_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        '''
        open the serial port and check the status of the stage
        '''
        super(ExcitationController, self).__init__(parent)
        com = '/dev/ttyACM0'
        baud = 19200
        parity = serial.PARITY_NONE
        self.ser = serial.Serial(com, baud, timeout=.25,
                                 parity=parity)
        comment(self.send_receive('co'))
        comment(self.send_receive('lh?'))
        comment(self.send_receive(('ip=' + ','.join(['500' for i in range(6)]))))
        comment(self.send_receive('lh?'))
        self.lamp_index = 0
        self.current_intensity = DEFAULT_INTENSITY
        self.turn_all_off()
        # comment(self.send_receive('sv?'))
        # dictionary containing tuples in the form: (cube_position, led_position)


    def get_response(self):
        response = ''
        while '\r' not in response:
            piece = self.ser.read()
            if piece != b'':
                response += piece.decode('utf-8')
        comment('response received from excitation lamp:{}'.format(response))
        return response

    def issue_command(self, command, suppress_msg=False):
        '''
        sends command and handles any errors from excitation lamp
        '''
        command_string = '{}\r'.format(command)
        if (not suppress_msg):
            comment('sending command to excitation lamp:{}'.format(command_string))
        self.ser.write(command_string.encode('utf-8'))

    def send_receive(self, command, suppress_msg=False):
        self.issue_command(command, suppress_msg)
        response = self.get_response()
        return response

    def turn_led_on(self, led):
        self.send_receive('on='+str(led))
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
        cmd_string = 'ip=' + ',' * (self.lamp_index-1) + str(int(intensity))
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
    fluor.send_receive('ip?')