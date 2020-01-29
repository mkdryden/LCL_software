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

    def __init__(self, screenshooter: ScreenShooter, frameskip: int = 2):
        super(InstrumentSequencer, self).__init__()
        self.screenshooter = screenshooter
        self.presets = presets.PresetManager(parent=self)
        self.camera = camera.ShowVideo()
        self.camera_thread = QtCore.QThread()
        self.camera_thread.start()
        self.camera.moveToThread(self.camera_thread)

        self.excitation = fluorescence_controller.ExcitationController(parent=self)
        self.laser = laser_controller.LaserController(parent=self)
        self.stage = asi_controller.StageController(parent=self)
        self.objectives = None

        self.image = np.ndarray([0])
        self.frameskip = frameskip
        self.frame_count = 0

    @QtCore.pyqtSlot()
    def initialize_instruments(self):
        """
        Initialize instruments. Needs to be done in correct thread
        """
        self.stage.init_controller()
        self.objectives = objectives.Objectives(self.stage)
        self.laser.init_controller()
        self.excitation.init_controller()
        QtCore.QMetaObject.invokeMethod(self.camera, 'start_video')

        for i in [self.camera, self.stage, self.laser, self.excitation]:
            for d in i.settings:
                self.presets.add_setting(i.settings[d])

        self.presets.load_presets()

        self.setup_signals()
        self.done_init_signal.emit()

    def setup_signals(self):
        self.tile_done_signal.connect(self.screenshooter.save_well_imgs)

    @QtCore.pyqtSlot(np.ndarray)
    def vid_process_slot(self, image):
        if self.frame_count > self.frameskip:
            self.camera.vid_process_signal.disconnect(self.vid_process_slot)
            self.image = image
            logger.info("Got new image")
            self.got_image_signal.emit()
            self.frame_count = 0
        else:
            self.frame_count += 1

    def get_next_image(self) -> np.ndarray:
        with wait_signal(self.got_image_signal):
            self.camera.vid_process_signal.connect(self.vid_process_slot)
        return self.image

    def gather_all_channel_images(self, preset_list: typing.Sequence[str]) -> np.ndarray:
        images = []
        for preset in preset_list:
            if preset != self.presets.preset:
                logger.info("Cycling preset to %s", preset)
                self.presets.set_preset(preset)
            images.append(self.get_next_image())
        return np.dstack(images)

    @QtCore.pyqtSlot(float, float)
    def move_rel_frame(self, x: typing.SupportsFloat = None, y: typing.SupportsFloat = None) -> None:
        """
        Move relative to the current frame size.
        :param x: Multiple of current frame width to move
        :param y: Multiple of current frame height to move
        """
        logger.info("Relative move frames: %s %s", x, y)

        if x is not None:
            x_rel = round(x * self.objectives.current_objective.field_dimx)
        else:
            x_rel = None

        if y is not None:
            y_rel = round(y * self.objectives.current_objective.field_dimy)
        else:
            y_rel = None

        with wait_signal(self.stage.done_moving_signal):
            logger.info("Relative move µm: %s %s", x_rel/10, y_rel/10)
            self.stage.move_rel(x=x_rel, y=y_rel)

    @QtCore.pyqtSlot(list, int, int)
    def tile(self, preset_list: typing.Sequence, columns: int = 3, rows: int = 3):
        start_x, start_y, _ = self.stage.get_position()

        x_grid = [x - (columns-1)/2. for x in range(columns)]
        y_grid = [y - (rows-1)/2. for y in range(rows)]

        pos_x = 0
        pos_y = 0

        output_images = [[None for _ in range(rows)] for _ in range(columns)]

        for n_x, x in enumerate(x_grid):
            for n_y, y in enumerate(y_grid):
                logger.info("Target rel: %s %s", x, y)
                self.move_rel_frame(x - pos_x, y - pos_y)
                pos_x = x
                pos_y = y
                output_images[n_x][n_y] = self.gather_all_channel_images(preset_list)

        with wait_signal(self.stage.done_moving_signal):
            logger.info("Returning to start location")
            self.stage.move(x=start_x, y=start_y)

        self.tile_done_signal.emit(output_images,
                                   [(preset, self.presets.presets[preset]['emission'])
                                    for preset in preset_list])
