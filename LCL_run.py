import sys
import logging
import time
import argparse

import cv2
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import QtCore
from PyQt5.QtCore import QThread
from PyQt5 import QtGui
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from LCL_ui import Ui_MainWindow
from hardware.asi_controller import StageController
from hardware.fluorescence_controller import ExcitationController
from hardware.laser_controller import LaserController
from localizer import Localizer

from _pi_cffi import ffi, lib

from video import ImageViewer

# Setup Logging
to_log = ['__main__', 'hardware', 'utils', 'video']
loggers = [logging.getLogger(name) for name in to_log]
logger = loggers[0]

log_handler = logging.StreamHandler()
log_formatter = logging.Formatter(
                    fmt='%(asctime)s %(levelname)s: [%(name)s] %(message)s',
                    datefmt='%H:%M:%S'
                )
log_handler.setFormatter(log_formatter)

for log in loggers:
    log.setLevel(level=logging.INFO)
    log.addHandler(log_handler)

assert lib.tl_camera_sdk_dll_initialize() == 0
assert lib.tl_camera_open_sdk() == 0

SHIFT_AMT = np.array([4], dtype=np.uint8)
INITIAL_EXPOSURE = 2 * 1000
INITIAL_BRIGHTNESS = 20
INITIAL_GAIN = 45


def get_camera_ids():
    # returns a handle to a char array of all of the available cameras separated by spaces
    camera_ids = ffi.new('char[1024]')
    assert lib.tl_camera_discover_available_cameras(camera_ids, 1024) == 0
    return camera_ids


@ffi.def_extern()
def tl_camera_frame_available_callback(sender, image_buffer, frame_count, metadata, metadata_size_in_bytes, context):
    np_data = np.frombuffer(ffi.buffer(image_buffer, 2160 * 4096 * 2), dtype=np.uint16)
    np_data = np_data.reshape((2160, -1))
    try:
        window.vid.vid_process_signal.emit(np_data)
    except NameError:
        return
    np_data = np.right_shift(np_data, 4).astype(np.uint8)

    height, width = np_data.shape
    qt_image = QtGui.QPixmap(QtGui.QImage(np_data.data, width, height, QtGui.QImage.Format_Grayscale8
                            ).convertToFormat(QtGui.QImage.Format_RGB32))
    try:
        window.vid.VideoSignal.emit(qt_image)
    except NameError:
        pass


class PresetManager(QtCore.QObject):
    number_of_checked_presets_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(PresetManager, self).__init__(parent)
        self.presets = pd.read_csv(preset_loc, index_col='name')
        print(self.presets)
        wavelengths = ['Off', '385nm', '430nm', '475nm', '525nm', '575nm', '630nm', 'All']
        self.wv_dict = dict(zip(wavelengths, range(len(wavelengths))))
        self.values = None
        self.saving = False
        self.model = None
        self.checked_names = []
        self.current_channel = 0
        self.number_of_channels = 0

    def select_preset(self, index):
        if self.saving is True:
            self.saving = not self.saving
            return
        name = window.ui.preset_comboBox.currentText()
        window.ui.exposure_doublespin_box.setValue(self.presets['exposure'][name])
        window.ui.brightness_doublespin_box.setValue(self.presets['brightness'][name])
        window.ui.gain_doublespin_box.setValue(self.presets['gain'][name])
        window.ui.cube_position_combobox.setCurrentIndex(self.presets['cube_position'][name] - 1)
        window.ui.intensity_doublespin_box.setValue(self.presets['intensity'][name])
        window.ui.excitation_lamp_on_combobox.setCurrentIndex(self.wv_dict[(str(self.presets['excitation'][name]))])
        emission = self.presets['emission'][name]
        if emission == '0' or emission == '0nm':
            emission = 0
        else:
            emission = emission[:-2]
        window.ui.emission_doublespin_box.setValue(int(emission))

    def get_all_current_values(self):
        self.values = []
        self.values.append(int(window.ui.exposure_doublespin_box.value()))
        self.values.append(int(window.ui.brightness_doublespin_box.value()))
        self.values.append(int(window.ui.gain_doublespin_box.value()))
        self.values.append(window.ui.cube_position_combobox.currentIndex() + 1)
        self.values.append(int(window.ui.intensity_doublespin_box.value()))
        self.values.append(window.ui.excitation_lamp_on_combobox.currentText())
        self.values.append(window.ui.emission_doublespin_box.text())

    def change_preset(self):
        name = window.ui.preset_comboBox.currentText()
        self.get_all_current_values()
        self.presets['exposure'][name] = self.values[0]
        self.presets['brightness'][name] = self.values[1]
        self.presets['gain'][name] = self.values[2]
        self.presets['cube_position'][name] = self.values[3]
        self.presets['intensity'][name] = self.values[4]
        self.presets['excitation'][name] = window.ui.excitation_lamp_on_combobox.currentText()
        self.presets['emission'][name] = window.ui.emission_doublespin_box.text()
        self.presets.to_csv(preset_loc, index=True)
        _ = QMessageBox.about(window, 'Notice', f'{name} preset has been saved.')

    def add_preset(self):
        t = '''
        Enter the name for the new preset.\nAll Acquisition settings will be saved in this preset.
        '''
        name, ok_pressed = QInputDialog.getText(window, 'New Preset',
                                                t,
                                                QLineEdit.Normal, '')
        if not ok_pressed: return
        self.saving = True
        self.get_all_current_values()
        # i = self.presets.__len__() + 1 # adding below
        self.presets.loc[name] = self.values
        self.presets.to_csv(preset_loc, index=True)
        window.ui.preset_comboBox.addItem(name)
        window.ui.preset_comboBox.setCurrentText(name)
        self.setup_tile_preset_list(window)

    def remove_preset(self):
        reply = QMessageBox.question(window, 'Remove Preset',
                                     'Are you sure you want to remove the currently selected preset?')
        if reply == 65536:
            return
        i = window.ui.preset_comboBox.currentIndex()
        name = window.ui.preset_comboBox.currentText()
        window.ui.preset_comboBox.setCurrentIndex(i - 1)
        window.ui.preset_comboBox.removeItem(i)
        self.presets = self.presets.drop(name)
        self.presets.to_csv(preset_loc, index=True)
        self.setup_tile_preset_list(window)

    def setup_tile_preset_list(self, window):
        self.model = QtGui.QStandardItemModel()
        for name in self.presets.index:
            item = QtGui.QStandardItem(name)
            item.text()
            # item.setCheckState(check)
            item.setCheckable(True)
            self.model.appendRow(item)
        window.ui.tile_preset_listView.setModel(self.model)
        self.model.itemChanged.connect(self.manage_checked_presets)

    def manage_checked_presets(self, item):
        self.checked_names = []
        i = 0
        while self.model.item(i):
            if self.model.item(i).checkState():
                self.checked_names.append(self.model.item(i).text())
            i += 1
        # print(self.checked_names)
        self.number_of_channels = len(self.checked_names)

    @QtCore.pyqtSlot()
    def return_number_of_presets_slot(self):
        self.number_of_checked_presets_signal.emit(self.presets.loc[self.checked_names])

    @QtCore.pyqtSlot()
    def cycle_image_channel_slot(self):
        # each time this is called, we advance to the next checked channel, until all currently checked channels
        # have been cycled through. then we repeat
        self.current_channel += 1
        if self.current_channel == self.number_of_channels: self.current_channel = 0
        window.ui.preset_comboBox.setCurrentText(self.checked_names[self.current_channel])


class ShowVideo(QtCore.QObject):
    VideoSignal = QtCore.pyqtSignal(QtGui.QPixmap)
    vid_process_signal = QtCore.pyqtSignal(np.ndarray)
    reticle_and_center_signal = QtCore.pyqtSignal('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')

    def __init__(self, window_size, parent=None):
        super(ShowVideo, self).__init__(parent)
        self.run_video = True
        self.window_size = window_size
        self.center_x = int(1351 / 2)
        self.center_y = int(711 / 2)
        self.reticle_x = int(self.center_x + 6)
        self.reticle_y = int(self.center_y + 115)
        self.camera_handle = None

    def draw_reticle(self, image):
        # cv2.circle(image, (self.reticle_x, self.reticle_y),
        #            5, (0, 0, 0), -1)
        cv2.circle(image, (self.center_x, self.center_y), 50, (250, 0, 0), -1)
        cv2.circle(image, (self.center_x - 50, self.center_y - 50), 50, (250, 0, 0), -1)

    # @staticmethod
    @QtCore.pyqtSlot()
    def startVideo(self):
        camera_ids = get_camera_ids()
        camera_handle_pointer = ffi.new('void **')
        print('opening camera...', lib.tl_camera_open_camera(camera_ids, camera_handle_pointer))
        self.camera_handle = camera_handle_pointer[0]
        function_pointer = lib.tl_camera_frame_available_callback
        print('setting frame available callback...',
              lib.tl_camera_set_frame_available_callback(self.camera_handle, function_pointer, ffi.new('int*', 0)))
        print('setting exposure...', lib.tl_camera_set_exposure_time(self.camera_handle, INITIAL_EXPOSURE))
        print('setting frames per trigger...',
              lib.tl_camera_set_frames_per_trigger_zero_for_unlimited(self.camera_handle, 0))
        print('arming camera...', lib.tl_camera_arm(self.camera_handle, 1))
        print('triggering camera...', lib.tl_camera_issue_software_trigger(self.camera_handle))
        print('setting brightness...', asi_controller.send_receive('7LED X={}'.format(INITIAL_BRIGHTNESS)))
        print('setting gain...', self.change_gain(INITIAL_GAIN))

    def change_exposure(self, value):
        comment(f'setting exposure to {value}')
        lib.tl_camera_set_exposure_time(self.camera_handle, int(value * 1000))

    def change_gain(self, value):
        comment(f'setting gain to {value}')
        lib.tl_camera_set_gain(self.camera_handle, int(value))

    def change_brightness(self, value):
        comment('setting brightness to {}'.format(value))
        asi_controller.send_receive('7LED X={}'.format(value))


class MainWindow(QMainWindow):
    start_video_signal = QtCore.pyqtSignal()
    qswitch_screenshot_signal = QtCore.pyqtSignal('PyQt_PyObject')
    start_focus_signal = QtCore.pyqtSignal()
    start_localization_signal = QtCore.pyqtSignal()

    def __init__(self, test_run):
        super(MainWindow, self).__init__()

        self.laser_enable = False
        # get our experiment variables
        if test_run != 'True':
            self.get_experiment_variables()

        # Set up the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # set up the video classes
        self.vid = ShowVideo(self.ui.verticalLayoutWidget.size())
        self.screen_shooter = screen_shooter()
        self.image_viewer = ImageViewer()
        # self.autofocuser = autofocuser()
        self.localizer = Localizer()

        # add the viewer to our ui
        self.ui.verticalLayout.addWidget(self.image_viewer)

        # create our extra threads
        self.screenshooter_thread = QThread()
        self.screenshooter_thread.start()
        self.screen_shooter.moveToThread(self.screenshooter_thread)

        self.localizer_thread = QThread()
        self.localizer_thread.start()
        self.localizer.moveToThread(self.localizer_thread)

        # connect the outputs to our signals
        self.vid.VideoSignal.connect(self.image_viewer.set_image)
        self.vid.vid_process_signal.connect(self.screen_shooter.screenshot_slot)
        self.ui.record_push_button.clicked.connect(self.screen_shooter.toggle_recording_slot)
        # self.vid.vid_process_signal.connect(self.autofocuser.vid_process_slot)
        self.vid.vid_process_signal.connect(self.localizer.vid_process_slot)
        self.qswitch_screenshot_signal.connect(self.screen_shooter.save_qswitch_fire_slot)
        self.localizer.qswitch_screenshot_signal.connect(self.screen_shooter.save_qswitch_fire_slot)
        # self.start_focus_signal.connect(self.autofocuser.autofocus)
        # self.start_localization_signal.connect(self.localizer.localize)
        self.ui.tile_and_navigate_pushbutton.clicked.connect(self.localizer.tile_slot)
        # self.autofocuser.position_and_variance_signal.connect(self.plot_variance_and_position)
        self.image_viewer.click_move_signal.connect(asi_controller.click_move_slot)
        self.localizer.localizer_move_signal.connect(asi_controller.localizer_move_slot)
        self.localizer.ai_fire_qswitch_signal.connect(self.ai_fire_qswitch_slot)
        self.vid.reticle_and_center_signal.connect(asi_controller.reticle_and_center_slot)
        self.vid.reticle_and_center_signal.emit(self.vid.center_x, self.vid.center_y, self.vid.reticle_x,
                                                self.vid.reticle_y)

        # connect to the video thread and start the video
        self.start_video_signal.connect(self.vid.startVideo)
        self.start_video_signal.emit()
        self.ui.exposure_doublespin_box.valueChanged.connect(self.vid.change_exposure)
        self.ui.gain_doublespin_box.valueChanged.connect(self.vid.change_gain)
        self.ui.brightness_doublespin_box.valueChanged.connect(self.vid.change_brightness)

        # Screenshot and comment buttons
        self.ui.misc_screenshot_button.clicked.connect(self.screen_shooter.save_misc_image)
        self.ui.user_comment_button.clicked.connect(self.send_user_comment)

        # Stage movement buttons
        self.ui.step_size_doublespin_box.valueChanged.connect(asi_controller.set_step_size)
        self.ui.repetition_rate_double_spin_box.valueChanged.connect(laser.set_pulse_frequency)
        self.ui.burst_count_double_spin_box.valueChanged.connect(laser.set_burst_counter)
        self.setup_comboboxes()
        self.localizer.get_position_signal.connect(asi_controller.get_all_positions)
        asi_controller.position_return_signal.connect(self.localizer.position_return_slot)
        self.ui.autofocus_checkbox.stateChanged.connect(self.autofocus_toggle)
        self.ui.retract_objective_checkbox.setChecked(asi_controller.get_is_objective_retracted())
        self.ui.retract_objective_checkbox.stateChanged.connect(asi_controller.toggle_objective_retraction)
        self.ui.calibrate_af_pushbutton.clicked.connect(asi_controller.calibrate_af)
        self.ui.intensity_doublespin_box.valueChanged.connect(excitation.change_intensity)
        self.ui.save_preset_pushButton.clicked.connect(preset_manager.change_preset)
        self.ui.add_preset_pushButton.clicked.connect(preset_manager.add_preset)
        self.ui.remove_preset_pushButton.clicked.connect(preset_manager.remove_preset)
        self.localizer.localizer_stage_command_signal.connect(asi_controller.localizer_stage_command_slot)

        # signals for getting the number of presets:
        self.localizer.get_number_of_presets_signal.connect(preset_manager.return_number_of_presets_slot)
        preset_manager.number_of_checked_presets_signal.connect(self.localizer.number_of_presets_slot)
        self.localizer.cycle_image_channel_signal.connect(preset_manager.cycle_image_channel_slot)
        # self.ui.cells_to_lyse_doublespin_box.valueChanged.connect(self.localizer.set_cells_to_lyse)
        # self.ui.process_well_pushButton.clicked.connect(self.start_localization)

        preset_manager.setup_tile_preset_list(self)
        self.show()
        # print('WIDTH:', self.ui.verticalLayoutWidget.frameGeometry().width())
        # print('HEIGHT:', self.ui.verticalLayoutWidget.frameGeometry().height())
        comment('finished gui init')

    def get_text(self, text_prompt):
        text, okPressed = QInputDialog.getText(self, 'Experiment Input', text_prompt, QLineEdit.Normal, "")
        if okPressed and text != None:
            return text

    def get_experiment_variables(self):
        var_dict = {'stain(s) used:': 'Enter the stain(s) used',
                    'cell line:': 'Enter the cell line',
                    'fixative used:': 'Enter the fixative used'}
        nums = range(10)
        checks = ['a', 'e', 'i', 'o', 'u'] + [str(num) for num in nums]
        for key, value in var_dict.items():
            good_entry = False
            while good_entry is not True:
                user_input = self.get_text(var_dict[key])
                val = user_input.lower()
                if any(vowel in val for vowel in checks):
                    comment('{} {}'.format(key, user_input))
                    good_entry = True

    # def start_localization(self):
    #     self.start_localization_signal.emit()

    def autofocus_toggle(self):
        comment('toggling autofocus')
        self.autofocusing = not self.autofocusing
        if self.autofocusing:
            asi_controller.turn_on_autofocus()
        else:
            asi_controller.turn_off_autofocus()

    def setup_comboboxes(self):
        self.ui.excitation_lamp_on_combobox.addItems(
            ['Off', '385nm', '430nm', '475nm', '525nm', '575nm', '630nm', 'All'])
        self.ui.excitation_lamp_on_combobox.currentIndexChanged.connect(excitation.change_fluorescence)

        self.ui.cube_position_combobox.addItems(['1', '2', '3', '4'])
        self.ui.cube_position_combobox.setCurrentIndex(asi_controller.get_cube_position())
        self.ui.cube_position_combobox.currentIndexChanged.connect(asi_controller.change_cube_position)

        self.ui.magnification_combobox.addItems(['P1', '40x', 'P3', '60x', 'P5', '20x'])
        self.ui.magnification_combobox.setCurrentIndex(asi_controller.get_objective_position())
        self.ui.magnification_combobox.currentIndexChanged.connect(self.change_magnification)

        self.ui.cell_type_to_lyse_comboBox.addItems(['red', 'green'])
        # self.ui.cell_type_to_lyse_comboBox.currentIndexChanged.connect(self.localizer.change_type_to_lyse)

        self.ui.lysis_mode_comboBox.addItems(['direct', 'excision'])
        # self.ui.lysis_mode_comboBox.currentIndexChanged.connect(self.localizer.change_lysis_mode)

        self.ui.preset_comboBox.addItems(preset_manager.presets.index)
        self.ui.preset_comboBox.currentIndexChanged.connect(preset_manager.select_preset)

    def send_user_comment(self):
        comment('user comment:{}'.format(self.ui.comment_box.toPlainText()))
        self.ui.comment_box.clear()

    def change_magnification(self, index):
        _ = QMessageBox.about(self, 'Notice', 'Wait for objective to reposition before continuing.')
        time.sleep(1)
        asi_controller.change_magnification(index)

    @QtCore.pyqtSlot()
    def qswitch_screenshot_slot(self):
        if self.laser_enable:
            self.qswitch_screenshot_signal.emit(30)
            logger.info("X:%s Y:%s Z:%s", *asi_controller.get_all_positions())
            laser.start_burst()

    def enable_laser_firing(self):
        if asi_controller.get_cube_position() == 1:
            _ = QMessageBox.about(self, 'Bad!', 'You are trying to fire the laser at the filter!')
            return
        asi_controller.move_rel_z(283)
        self.ui.laser_groupbox.setTitle('Laser - ARMED')
        self.laser_enable = True

    def disable_laser_firing(self):
        asi_controller.move_rel_z(-283)
        self.ui.laser_groupbox.setTitle('Laser')
        self.laser_enable = False

    @QtCore.pyqtSlot('PyQt_PyObject')
    def ai_fire_qswitch_slot(self, auto_fire):
        comment('automated firing from localizer!')
        # if auto_fire == True:
        #     laser.qswitch_auto()
        # else:
        #     laser.fire_qswitch()

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            # print('key pressed {}'.format(event.key()))
            key_control_dict = {
                87: asi_controller.move_up,
                65: asi_controller.move_left,
                83: asi_controller.move_down,
                68: asi_controller.move_right,
                66: asi_controller.move_last,
                16777249: self.enable_laser_firing,
                70: self.qswitch_screenshot_slot,
                # 81: laser.qswitch_auto,
                # 73: stage.start_roll_down,
                # 75:self.autofocuser.roll_backward,
                # 79:self.start_autofocus,
                # 71:self.toggle_dmf_or_lysis,
                # 84: stage.move_left_one_well_slot,
                # 89: stage.move_right_one_well_slot,
                96: self.screen_shooter.save_target_image,
                # 16777216: self.localizer.stop_auto_mode
            }
            if event.key() in key_control_dict.keys():
                key_control_dict[event.key()]()

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            # print('key released: {}'.format(event.key()))
            key_control_dict = {
                16777249: self.disable_laser_firing,
                70: laser.stop_burst
            }
            if event.key() in key_control_dict.keys():
                key_control_dict[event.key()]()


if __name__ == '__main__':
    # TODO refactor so the gui runs on separate process from "stage"
    parser = argparse.ArgumentParser()
    parser.add_argument('test_run')
    args = parser.parse_args()
    app = QApplication(sys.argv)
    asi_controller = StageController()
    asi_controller.init_controller()
    excitation = ExcitationController()
    excitation.init_controller()
    laser = LaserController()
    laser.init_controller()
    preset_manager = PresetManager()
    window = MainWindow(args.test_run)
    comment('exit with code: ' + str(app.exec_()))
    sys.exit()
