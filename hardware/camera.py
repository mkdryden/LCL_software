import typing
import logging

import numpy as np
from PyQt5 import QtGui, QtCore
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

from hardware.presets import SettingValue

logger = logging.getLogger(__name__)


class ShowVideo(QtCore.QObject):
    VideoSignal = QtCore.pyqtSignal(QtGui.QPixmap)
    vid_process_signal = QtCore.pyqtSignal(np.ndarray)

    def __init__(self):
        super(ShowVideo, self).__init__(None)
        self.timer = QtCore.QTimer(self)
        self.sdk = None
        self.camera = None

        settings = [SettingValue("gain", default_value=0,
                                 changed_call=self.change_gain),
                    SettingValue("exposure", default_value=10,
                                 changed_call=self.change_exposure_ms)
                    ]
        self.settings = {i.name: i for i in settings}

    @QtCore.pyqtSlot()
    def start_video(self):
        self.sdk = TLCameraSDK()
        available_cameras = self.sdk.discover_available_cameras()
        if len(available_cameras) < 1:
            logger.warning("no cameras detected")
            return

        self.camera = self.sdk.open_camera(available_cameras[0])
        self.camera.frames_per_trigger_zero_for_unlimited = 0  # start camera in continuous mode
        self.camera.image_poll_timeout_ms = 0
        self.camera.exposure_time_us = 11000  # set exposure to 11 ms

        self.camera.arm(2)
        self.camera.issue_software_trigger()
        self.timer.timeout.connect(self.get_frame)
        self.timer.start()

    @QtCore.pyqtSlot()
    def get_frame(self):
        frame = self.camera.get_pending_frame_or_null()
        if frame is not None:
            np_data = np.copy(frame.image_buffer)
            try:
                self.vid_process_signal.emit(np_data)
            except NameError:
                return
            np_data = np.right_shift(np_data, 4).astype(np.uint8)  # Convert to 8-bit

            height, width = np_data.shape
            qt_image = QtGui.QPixmap(QtGui.QImage(np_data.data, width, height, QtGui.QImage.Format_Grayscale8
                                                  ).convertToFormat(QtGui.QImage.Format_RGB32))
            try:
                self.VideoSignal.emit(qt_image)
            except NameError:
                pass

    @QtCore.pyqtSlot()
    def stop_video(self):
        self.timer.timeout.disconnect(self.get_frame)

    @QtCore.pyqtSlot('int')
    def change_exposure_ms(self, ms: typing.SupportsInt):
        """
        Sets camera exposure in ms
        :param ms: Exposure time in ms
        """
        self.camera.exposure_time_us = int(ms * 1000)

    @QtCore.pyqtSlot()
    def change_gain(self, gain: typing.SupportsInt):
        """
        Sets camera gain.
        :param gain: gain
        """
        self.camera.gain = int(gain)

    def deleteLater(self) -> None:
        self.destroyed()
        super(ShowVideo, self).deleteLater()
    
    def destroyed(self, object: typing.Optional['QObject'] = ...) -> None:
        try:
            self.camera.dispose()
            self.sdk.dispose()
        except AttributeError:
            pass

