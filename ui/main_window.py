import logging
import re
import time
import typing
from functools import partial

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QMainWindow, QInputDialog, QLineEdit, QMessageBox

from camera import ShowVideo
from localizer import Localizer
from ui.LCL_ui import Ui_MainWindow
from utils import ScreenShooter, AspectRatioWidget
from video import ImageViewer, MagnifiedImageViewer
from hardware.fluorescence_controller import wl_to_idx, idx_to_wl, ExcitationController
from hardware.laser_controller import LaserController
from hardware.asi_controller import StageController
from hardware.presets import SettingValue, PresetManager

logger = logging.getLogger(__name__)


def strip_letters(string: str) -> int:
    try:
        return int(re.sub(r"\D", "", string))
    except TypeError:
        return int(string)


class CatchKeys(QtCore.QObject):
    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.KeyRelease:
            return True
        else:
            return super(CatchKeys, self).eventFilter(obj, event)


class MainWindow(QMainWindow):
    start_video_signal = QtCore.pyqtSignal()
    qswitch_screenshot_signal = QtCore.pyqtSignal('PyQt_PyObject')
    start_focus_signal = QtCore.pyqtSignal()
    start_localization_signal = QtCore.pyqtSignal()
    settings_changed_signal = QtCore.pyqtSignal(dict)
    add_preset_signal = QtCore.pyqtSignal('PyQt_PyObject')
    modify_preset_signal = QtCore.pyqtSignal('PyQt_PyObject')
    remove_preset_signal = QtCore.pyqtSignal(str)
    start_tiling_signal = QtCore.pyqtSlot(list)

    def __init__(self, test_run: bool, asi_controller: StageController,
                 laser_controller: LaserController, excitation: ExcitationController,
                 preset_manager: PresetManager):
        super(MainWindow, self).__init__()
        self.preset_manager = preset_manager
        self.excitation = excitation
        self.laser = laser_controller
        self.asi_controller = asi_controller
        self.vid = ShowVideo()

        self.laser_enable = False
        # get our experiment variables
        if test_run is not True:
            self.get_experiment_variables()

        # Set up the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # set up the video classes
        self.screen_shooter = ScreenShooter()
        self.image_viewer = ImageViewer()

        self.zoom_window = QtWidgets.QDockWidget(parent=self)
        self.zoom_window.setMinimumSize(300, 300)
        self.zoom_window.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.zoom_window.setFloating(True)
        self.zoom_window.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable)
        self.zoom_window.setWindowTitle("100 %")
        self.zoom_image_viewer = MagnifiedImageViewer()
        self.zoom_image_viewer.setMinimumSize(300, 300)
        self.zoom_image_viewer.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.zoom_window.setWidget(self.zoom_image_viewer)
        self.addDockWidget(QtCore.Qt.DockWidgetArea(QtCore.Qt.LeftDockWidgetArea), self.zoom_window)

        # self.autofocuser = autofocuser()
        self.localizer = Localizer(vid_process_signal=self.vid.vid_process_signal,
                                   asi_controller=self.asi_controller)

        # add the viewer to our ui and let resize with image aspect
        aspect_widget = AspectRatioWidget(self.image_viewer)
        self.image_viewer.aspect_changed_signal.connect(aspect_widget.aspect_changed_slot)
        self.ui.main_layout.addWidget(aspect_widget)

        # create our extra threads
        self.vid_thread = QThread()
        self.vid_thread.start()
        self.vid.moveToThread(self.vid_thread)

        self.screenshooter_thread = QThread()
        self.screenshooter_thread.start()
        self.screen_shooter.moveToThread(self.screenshooter_thread)

        self.localizer_thread = QThread()
        self.localizer_thread.start()
        self.localizer.moveToThread(self.localizer_thread)

        # connect the outputs to our signals
        self.vid.VideoSignal.connect(self.image_viewer.set_image)
        self.vid.VideoSignal.connect(self.zoom_image_viewer.set_image)
        self.vid.vid_process_signal.connect(self.screen_shooter.screenshot_slot)
        self.ui.record_push_button.clicked.connect(self.screen_shooter.toggle_recording_slot)
        # self.vid.vid_process_signal.connect(self.autofocuser.vid_process_slot)
        # self.vid.vid_process_signal.connect(self.localizer.vid_process_slot)
        self.qswitch_screenshot_signal.connect(self.screen_shooter.save_qswitch_fire_slot)
        self.localizer.qswitch_screenshot_signal.connect(self.screen_shooter.save_qswitch_fire_slot)
        # self.start_focus_signal.connect(self.autofocuser.autofocus)
        # self.start_localization_signal.connect(self.localizer.localize)
        self.ui.tile_and_navigate_pushbutton.clicked.connect(self.start_tiling)
        # self.autofocuser.position_and_variance_signal.connect(self.plot_variance_and_position)
        self.image_viewer.click_move_signal.connect(self.asi_controller.click_move_slot)
        self.localizer.localizer_move_signal.connect(self.asi_controller.localizer_move_slot)
        self.localizer.ai_fire_qswitch_signal.connect(self.ai_fire_qswitch_slot)
        # self.vid.reticle_and_center_signal.connect(self.asi_controller.reticle_and_center_slot)
        # self.vid.reticle_and_center_signal.emit(self.vid.center_x, self.vid.center_y, self.vid.reticle_x,
        #                                         self.vid.reticle_y)

        # connect to the video thread and start the video
        self.start_video_signal.connect(self.vid.start_video)
        self.start_video_signal.emit()

        # Screenshot and comment buttons
        self.ui.misc_screenshot_button.clicked.connect(self.screen_shooter.save_misc_image)
        self.catchkeys = CatchKeys()
        self.ui.comment_box.installEventFilter(self.catchkeys)
        self.ui.user_comment_button.clicked.connect(self.send_user_comment)

        # Stage movement buttons
        self.ui.step_size_doublespin_box.valueChanged.connect(self.asi_controller.set_step_size)
        self.ui.repetition_rate_double_spin_box.valueChanged.connect(self.laser.set_pulse_frequency)
        self.ui.burst_count_double_spin_box.valueChanged.connect(self.laser.set_burst_counter)
        self.localizer.get_position_signal.connect(self.asi_controller.get_all_positions)
        self.asi_controller.position_return_signal.connect(self.localizer.position_return_slot)

        # Settings
        self.ui.autofocus_checkbox.stateChanged.connect(self.autofocus_toggle)
        self.ui.retract_objective_checkbox.setChecked(self.asi_controller.get_is_objective_retracted())
        self.ui.retract_objective_checkbox.stateChanged.connect(self.asi_controller.toggle_objective_retraction)
        self.ui.calibrate_af_pushbutton.clicked.connect(self.asi_controller.calibrate_af)

        # Preset Manager
        self.ui.save_preset_pushButton.clicked.connect(self.modify_preset)
        self.ui.add_preset_pushButton.clicked.connect(self.add_preset)
        self.add_preset_signal.connect(self.preset_manager.modify_preset)
        self.modify_preset_signal.connect(self.preset_manager.modify_preset)
        self.remove_preset_signal.connect(self.preset_manager.remove_preset)
        self.preset_model = QtGui.QStandardItemModel()
        self.ui.tile_preset_listView.setModel(self.preset_model)
        self.ui.remove_preset_pushButton.clicked.connect(self.remove_preset)
        self.localizer.localizer_stage_command_signal.connect(self.asi_controller.localizer_stage_command_slot)

        for i in [self.vid, self.asi_controller, self.laser, self.excitation]:
            for d in i.settings:
                self.preset_manager.add_setting(i.settings[d])

        self.setup_comboboxes()

        self.preset_manager.load_presets()
        self.show()

        logger.info('finished gui init')

    def setup_comboboxes(self):
        self.ui.excitation_lamp_on_combobox.addItems(wl_to_idx.keys())
        self.ui.excitation_lamp_on_combobox.activated.connect(
            partial(self.preset_manager.change_value, 'excitation'))

        self.ui.cube_position_combobox.addItems(['0', '1', '2', '3'])
        self.ui.cube_position_combobox.setCurrentIndex(self.preset_manager.get_values()['cube_position'])
        self.ui.cube_position_combobox.currentIndexChanged.connect(
            partial(self.preset_manager.change_value, 'cube_position'))
        self.ui.intensity_spin_box.valueChanged.connect(
            partial(self.preset_manager.change_value, 'intensity'))

        self.ui.magnification_combobox.addItems(['P1', '40x', 'P3', '60x', 'P5', '20x'])
        self.ui.magnification_combobox.setCurrentIndex(self.asi_controller.get_objective_position())
        self.ui.magnification_combobox.currentIndexChanged.connect(self.change_magnification)

        self.ui.cell_type_to_lyse_comboBox.addItems(['red', 'green'])
        # self.ui.cell_type_to_lyse_comboBox.currentIndexChanged.connect(self.localizer.change_type_to_lyse)

        self.ui.lysis_mode_comboBox.addItems(['direct', 'excision'])
        # self.ui.lysis_mode_comboBox.currentIndexChanged.connect(self.localizer.change_lysis_mode)

        self.ui.preset_comboBox.currentTextChanged.connect(self.preset_manager.set_preset)

        self.preset_manager.preset_loaded_signal.connect(self.update_settings)
        self.preset_manager.presets_changed_signal.connect(self.update_presets)

        self.ui.exposure_spin_box.valueChanged.connect(partial(self.preset_manager.change_value, 'exposure'))
        self.ui.gain_spin_box.valueChanged.connect(partial(self.preset_manager.change_value, 'gain'))
        self.ui.brightness_spin_box.valueChanged.connect(
            partial(self.preset_manager.change_value, 'brightness'))

    # @QtCore.pyqtSlot()
    # def get_settings_dict(self):
    #     self.settings_changed_signal.emit(
    #         {'exposure': strip_letters(self.ui.exposure_spin_box.value()),
    #          'brightness': strip_letters(self.ui.brightness_doublespin_box.value()),
    #          'gain': strip_letters(self.ui.gain_doublespin_box.value()),
    #          'cube_position': self.ui.cube_position_combobox.currentIndex() + 1,
    #          'intensity': strip_letters(self.ui.intensity_doublespin_box.value()),
    #          'excitation': self.ui.excitation_lamp_on_combobox.currentText(),
    #          'emission': strip_letters(self.ui.emission_doublespin_box.text())
    #          })

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: typing.Mapping[str, SettingValue]) -> None:
        self.ui.exposure_spin_box.setValue(settings['exposure'])
        self.ui.brightness_spin_box.setValue(settings['brightness'])
        self.ui.gain_spin_box.setValue(settings['gain'])
        self.ui.cube_position_combobox.setCurrentIndex(settings['cube_position'])
        self.ui.intensity_spin_box.setValue(settings['intensity'])
        self.ui.excitation_lamp_on_combobox.setCurrentIndex(settings['excitation'])
        self.ui.emission_spin_box.setValue(strip_letters(settings['emission']))

    @QtCore.pyqtSlot(list)
    def update_presets(self, presets: typing.Sequence):
        self.ui.preset_comboBox.clear()
        self.ui.preset_comboBox.addItems(presets)
        self.preset_model.clear()
        for name in presets:
            item = QtGui.QStandardItem(name)
            item.text()
            item.setCheckable(True)
            self.preset_model.appendRow(item)

    @QtCore.pyqtSlot()
    def add_preset(self):
        t = '''
        Enter the name for the new preset.\nAll Acquisition settings will be saved in this preset.
        '''
        name, ok_pressed = QInputDialog.getText(self, 'New Preset',
                                                t,
                                                QLineEdit.Normal, '')
        if not ok_pressed:
            return

        self.modify_preset_signal.emit(name)

    @QtCore.pyqtSlot()
    def modify_preset(self):
        self.modify_preset_signal.emit(None)

    @QtCore.pyqtSlot()
    def remove_preset(self):
        reply = QMessageBox.question(self, 'Remove Preset',
                                     'Are you sure you want to remove the currently selected preset?')
        if reply == 65536:
            return
        i = self.ui.preset_comboBox.currentIndex()
        name = self.ui.preset_comboBox.currentText()
        self.ui.preset_comboBox.setCurrentIndex(i - 1)
        self.ui.preset_comboBox.removeItem(i)
        self.remove_preset_signal.emit(name)

    def get_checked_presets(self) -> typing.Sequence[str]:
        return [self.preset_model.item(i).text()
                for i in range(self.preset_model.rowCount())
                if self.preset_model.item(i).checkState()]

    @QtCore.pyqtSlot()
    def start_tiling(self) -> None:
        checked = self.get_checked_presets()
        presets = self.preset_manager.presets
        self.start_tiling_signal.emit({k: presets[k] for k in checked if k in presets})

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.zoom_window.close()
        self.screenshooter_thread.quit()
        self.localizer_thread.quit()
        self.vid_thread.quit()

    def get_text(self, text_prompt):
        text, okPressed = QInputDialog.getText(self, 'Experiment Input', text_prompt, QLineEdit.Normal, "")
        if okPressed and text is not None:
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
                    logger.info('%s %s', key, user_input)
                    good_entry = True

    # def start_localization(self):
    #     self.start_localization_signal.emit()

    def autofocus_toggle(self):
        logger.info('toggling autofocus')
        self.autofocusing = not self.autofocusing
        if self.autofocusing:
            self.asi_controller.turn_on_autofocus()
        else:
            self.asi_controller.turn_off_autofocus()

    def send_user_comment(self):
        logger.info('user comment: %s', self.ui.comment_box.toPlainText())
        self.ui.comment_box.clear()

    def change_magnification(self, index):
        _ = QMessageBox.about(self, 'Notice', 'Wait for objective to reposition before continuing.')
        time.sleep(1)
        self.asi_controller.change_magnification(index)

    @QtCore.pyqtSlot()
    def qswitch_screenshot_slot(self):
        if self.laser_enable:
            self.qswitch_screenshot_signal.emit(30)
            logger.info("X:%s Y:%s Z:%s", *self.asi_controller.get_all_positions())
            self.laser.start_burst()

    def enable_laser_firing(self):
        if self.asi_controller.get_cube_position() == 1:
            _ = QMessageBox.about(self, 'Bad!', 'You are trying to fire the laser at the filter!')
            return
        self.asi_controller.move_rel_z(152)  # 283
        self.ui.laser_groupbox.setTitle('Laser - ARMED')
        self.laser_enable = True

    def disable_laser_firing(self):
        self.asi_controller.move_rel_z(-152)
        self.ui.laser_groupbox.setTitle('Laser')
        self.laser_enable = False

    @QtCore.pyqtSlot('PyQt_PyObject')
    def ai_fire_qswitch_slot(self, auto_fire):
        logger.info('automated firing from localizer!')
        # if auto_fire == True:
        #     laser.qswitch_auto()
        # else:
        #     laser.fire_qswitch()

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            # print('key pressed {}'.format(event.key()))
            key_control_dict = {
                87: self.asi_controller.move_up,
                65: self.asi_controller.move_left,
                83: self.asi_controller.move_down,
                68: self.asi_controller.move_right,
                66: self.asi_controller.move_last,
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
            # logger.info('key released: %s', event.key())
            key_control_dict = {
                16777249: self.disable_laser_firing,
                70: self.laser.stop_burst
            }
            if event.key() in key_control_dict.keys():
                key_control_dict[event.key()]()

