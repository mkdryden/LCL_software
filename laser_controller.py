import sys
import serial
import numpy as np
from utils import comment
from PyQt5 import QtCore


class LaserController:

    def __init__(self):
        self.ser = self.get_connection()
        self.ser.flushInput()
        self.ser.flushOutput()
        self.ready_to_fire = False
        self.send_receive('d')
        #     set triggering to internal
        self.send_receive('0x')
        #     stop burst
        self.send_receive('d')
        self.set_pulse_frequency(50)
        self.set_burst_counter(50)

    def get_connection(self):
        possible_coms = range(0,5)
        for com in possible_coms:
            try:
                com = '/dev/ttyUSB{}'.format(com)
                parity = serial.PARITY_NONE
                ser = serial.Serial(com, 921600, timeout=.25,
                                         parity=parity)
                ser.write('n'.encode('utf-8'))
                response = ser.readline()
                if response == b'18247\r\n':
                    comment('laser found on {}'.format(com))
                    return ser
            except Exception as e:
                comment('laser not on COM ' + com)
        comment('could not connect to laser. exiting...')
        sys.exit(1)

    def issue_command(self, command, suppress_msg=False):
        if (not suppress_msg):
            comment('sending command to laser:{}'.format(command))
        self.ser.write(command.encode('utf-8'))

    def get_response(self):
        response = ''
        while '\n' not in response:
            piece = self.ser.read()
            if piece != b'':
                response += piece.decode('utf-8')
        comment('response received from laser:{}'.format(response))
        return response

    def send_receive(self, command, suppress_msg=False):
        self.issue_command(command, suppress_msg)
        response = self.get_response()
        return response

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
    laser.send_receive('s')
    laser.set_burst_counter(20)
    laser.set_pulse_frequency(5)
    laser.start_burst()
