import logging
import typing

from PyQt5 import QtCore
import numpy as np

from hardware import objectives, asi_controller, laser_controller, fluorescence_controller, presets, camera
from utils import wait_signal, ScreenShooter

logger = logging.getLogger(__name__)


class InstrumentSequencer(QtCore.QObject):
    done_init_signal = QtCore.pyqtSignal()
    tile_done_signal = QtCore.pyqtSignal(list, list)
    got_image_signal = QtCore.pyqtSignal()
    set_record_signal = QtCore.pyqtSignal(bool)

    def __init__(self, screenshooter: ScreenShooter, frameskip: int = 2):
        super(InstrumentSequencer, self).__init__()
        self.screenshooter = screenshooter
        self.presets = presets.PresetManager(parent=self)
        self.vol_settings = presets.SettingManager(parent=self)

        self.camera = camera.ShowVideo()
        self.camera_thread = QtCore.QThread()
        self.camera_thread.start()
        self.camera.moveToThread(self.camera_thread)
        self.excitation = fluorescence_controller.ExcitationController(parent=self)
        self.laser = laser_controller.LaserController(parent=self)
        self.stage = asi_controller.StageController(parent=self)
        self.objectives = None

        self.laser_armed = False
        self.laser_firing = False
        self.take_laser_image = False
        self.take_laser_video = False
        self.laser_z_offset = 0
        self.laser_last_filter_cube = None

        self.image = np.ndarray([0])
        self.frameskip = frameskip
        self.frame_count = 0

    @QtCore.pyqtSlot()
    def initialize_instruments(self):
        """
        Initialize instruments. Needs to be done in correct thread
        """
        self.stage.init_controller()
        self.objectives = self.stage.objectives
        self.objectives.load_yaml()
        self.laser.init_controller()
        self.excitation.init_controller()
        QtCore.QMetaObject.invokeMethod(self.camera, 'start_video')

        for i in [self.camera, self.stage, self.excitation]:
            for d in i.settings:
                self.presets.add_setting(i.settings[d])

        self.presets.load_presets()

        for i in [self.laser]:
            for j in i.vol_settings.values():
                self.vol_settings.add_setting(j)

        self.setup_signals()
        self.done_init_signal.emit()

    def setup_signals(self):
        self.tile_done_signal.connect(self.screenshooter.save_well_imgs)
        self.set_record_signal.connect(self.screenshooter.set_recording_state)

    @QtCore.pyqtSlot(np.ndarray)
    def _vid_process_slot(self, image):
        if self.frame_count > self.frameskip:
            return

        # TODO: Figure out why this slot gets called multiple times
        if self.frame_count == self.frameskip:
            try:
                self.camera.vid_process_signal.disconnect(self._vid_process_slot)
            except TypeError:
                pass
            self.image = image
            logger.info("Got new image")
            self.got_image_signal.emit()
            self.frame_count = 0
        else:
            self.frame_count += 1

    def _get_next_image(self) -> np.ndarray:
        with wait_signal(self.got_image_signal):
            self.camera.vid_process_signal.connect(self._vid_process_slot)
        return self.image

    def gather_all_channel_images(self, preset_list: typing.Sequence[str]) -> np.ndarray:
        images = []
        for preset in preset_list:
            if preset != self.presets.preset:
                logger.info("Cycling preset to %s", preset)
                self.presets.set_preset(preset)
            images.append(self._get_next_image())
        return np.dstack(images)

    @QtCore.pyqtSlot(float, float)
    def move_rel_frame(self, x: float = None, y: float = None) -> None:
        """
        Move relative to the current frame size.
        :param x: Multiple of current frame width to move
        :param y: Multiple of current frame height to move
        """
        logger.info("Relative move frames: %s %s", x, y)

        if x is not None:
            x_rel = round(x * self.camera.camera.image_width_pixels *
                          self.objectives.current_objective.scale)
        else:
            x_rel = None

        if y is not None:
            y_rel = round(y * self.camera.camera.image_height_pixels *
                          self.objectives.current_objective.scale)
        else:
            y_rel = None

        with wait_signal(self.stage.done_moving_signal):
            logger.info("Relative move µm: %s %s", x_rel/10, y_rel/10)
            self.stage.move_rel(x=x_rel, y=y_rel)

    @QtCore.pyqtSlot()
    def laser_arm(self):
        if self.laser_armed:
            return
        if self.laser.connected:
            self.laser_last_filter_cube = self.presets.get_values()['cube_position']
            if self.laser_last_filter_cube != 0:
                self.presets.change_value('cube_position', 0)
            self.laser_armed = True
        else:
            logger.warning("Cannot arm laser, controller not connected")

    @QtCore.pyqtSlot()
    def laser_disarm(self):
        if self.laser.connected:
            self.laser_stop()
            if self.laser_last_filter_cube != 0:
                self.presets.change_value('cube_position', self.laser_last_filter_cube)
        self.laser_armed = False

    @QtCore.pyqtSlot(bool, bool, int)
    def laser_fire(self, take_image: bool, take_video: bool, z_offset: int):
        if self.laser_firing:
            return
        if self.laser_armed:
            self.take_laser_image = take_image
            self.take_laser_video = take_video
            if take_image:
                self.screenshooter.requested_frames.appendleft("laser-before")
            if take_video:
                self.set_record_signal.emit(True)
            self.laser_firing = True
            if z_offset != 0:
                with wait_signal(self.stage.done_moving_signal):
                    self.stage.move_rel(z=z_offset)
                self.laser_z_offset = z_offset
            logger.info("Laser fired at coordinates: %s", self.stage.position)
            self.laser.start_burst()

    @QtCore.pyqtSlot()
    def laser_stop(self):
        if self.laser_firing:
            self.laser.stop_burst()
            if self.laser_z_offset != 0:
                with wait_signal(self.stage.done_moving_signal):
                    self.stage.move_rel(z=-self.laser_z_offset)
                self.laser_z_offset = 0
            if self.take_laser_image:
                self.screenshooter.requested_frames.appendleft("laser-after")
                self.take_laser_image = False
            if self.take_laser_video:
                self.set_record_signal.emit(False)
                self.take_laser_video = False
            self.laser_firing = False

    @QtCore.pyqtSlot(list, int, int)
    def tile(self, preset_list: typing.Sequence, columns: int = 3, rows: int = 3):
        start_preset = self.presets.preset
        start_x, start_y, _ = self.stage.get_position()

        x_grid = [x - (columns-1)/2. for x in range(columns)]
        y_grid = [y - (rows-1)/2. for y in range(rows)]

        pos_x = 0
        pos_y = 0

        output_images = [[None for _ in range(rows)] for _ in range(columns)]

        for n_x, x in enumerate(x_grid):
            for n_y, y in enumerate(y_grid):
                logger.info("Tile coordinates: %s %s", x, y)
                self.move_rel_frame(x - pos_x, y - pos_y)
                pos_x = x
                pos_y = y
                output_images[n_x][n_y] = self.gather_all_channel_images(preset_list)

        with wait_signal(self.stage.done_moving_signal):
            logger.info("Returning to start location")
            self.stage.move(x=start_x, y=start_y)

        self.presets.set_preset(start_preset)

        self.tile_done_signal.emit(output_images,
                                   [(preset, self.presets.presets[preset]['emission'])
                                    for preset in preset_list])

    @QtCore.pyqtSlot(int, int, int)
    def move_rel_fast(self, x: int = None, y: int = None, z: int = None):
        self.stage.move_rel(x, y, z, check_status=False)