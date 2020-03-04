import logging
import re
import time
import typing
from functools import partial

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QMainWindow, QInputDialog, QLineEdit, QMessageBox
import numpy as np

from ui.LCL_ui import Ui_MainWindow
from utils import ScreenShooter, AspectRatioWidget, wait_signal
from video import ImageViewer, MagnifiedImageViewer
from hardware.fluorescence_controller import wl_to_idx
from hardware.settings import SettingValue
from instrument_sequencer import InstrumentSequencer

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
    start_sequencer_signal = QtCore.pyqtSignal()
    start_video_signal = QtCore.pyqtSignal()
    laser_arm_signal = QtCore.pyqtSignal()
    laser_disarm_signal = QtCore.pyqtSignal()
    laser_fire_signal = QtCore.pyqtSignal(bool, bool, int)
    laser_stop_signal = QtCore.pyqtSignal()
    start_localization_signal = QtCore.pyqtSignal()
    setting_changed_signal = QtCore.pyqtSignal(str, 'PyQt_PyObject')
    nvsetting_changed_signal = QtCore.pyqtSignal(str, 'PyQt_PyObject')
    settings_save_signal = QtCore.pyqtSignal(str)
    add_preset_signal = QtCore.pyqtSignal('PyQt_PyObject')
    modify_preset_signal = QtCore.pyqtSignal('PyQt_PyObject')
    remove_preset_signal = QtCore.pyqtSignal(str)
    start_tiling_signal = QtCore.pyqtSignal(list, int, int)
    stage_fast_moverel_signal = QtCore.pyqtSignal(int, int, int)
    stage_get_pos_signal = QtCore.pyqtSignal()
    af_mode_signal = QtCore.pyqtSignal(str)

    def __init__(self, test_run: bool):
        super(MainWindow, self).__init__()
        # get our experiment variables
        if test_run is not True:
            self.get_experiment_variables()

        # Set up the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # set up the video classes
        self.screen_shooter = ScreenShooter()

        self.sequencer = InstrumentSequencer(screenshooter=self.screen_shooter)
        # Add ui-only settings
        self.sequencer.settings.add_setting(SettingValue('stage_step_um',
                                                         default_value=30))
        self.image_viewer = ImageViewer()
        self.preset_manager = self.sequencer.presets
        self.vid = self.sequencer.camera

        # 100% view widget
        self.zoom_dockwidget = QtWidgets.QDockWidget(parent=self)
        self.zoom_dockwidget.setObjectName("zoom_dockwidget")
        self.zoom_dockwidget.setWindowTitle('100 %')
        self.zoom_dockwidget.setMinimumSize(300, 300)
        self.zoom_dockwidget.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.zoom_dockwidget.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable)
        self.zoom_image_viewer = MagnifiedImageViewer()
        self.zoom_image_viewer.setMinimumSize(300, 300)
        self.zoom_image_viewer.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.zoom_dockwidget.setWidget(self.zoom_image_viewer)

        # Nest instrument and zoom dockwidgets, zoom at top
        self.splitDockWidget(self.ui.instrument_dockwidget, self.zoom_dockwidget, QtCore.Qt.Vertical)
        self.removeDockWidget(self.ui.instrument_dockwidget)
        self.splitDockWidget(self.zoom_dockwidget, self.ui.instrument_dockwidget, QtCore.Qt.Vertical)
        self.ui.instrument_dockwidget.show()

        # add the viewer to our ui and let resize with image aspect
        aspect_widget = AspectRatioWidget(self.image_viewer)
        self.image_viewer.aspect_changed_signal.connect(aspect_widget.aspect_changed_slot)
        self.ui.main_layout.addWidget(aspect_widget)

        # Threads
        self.screenshooter_thread = QThread()
        self.screenshooter_thread.start()
        self.screen_shooter.moveToThread(self.screenshooter_thread)

        self.sequencer_thread = QThread()
        self.sequencer_thread.start()
        self.sequencer.moveToThread(self.sequencer_thread)
        self.start_sequencer_signal.connect(self.sequencer.initialize_instruments)
        with wait_signal(self.sequencer.done_init_signal, timeout=None):
            self.start_sequencer_signal.emit()  # Need to do it this way for threading

        # connect the outputs to our signals
        self.image_viewer.objectives = self.sequencer.objectives
        self.vid.VideoSignal.connect(self.image_viewer.set_image)
        self.vid.VideoSignal.connect(self.zoom_image_viewer.set_image)
        self.vid.vid_process_signal.connect(self.screen_shooter.screenshot_slot)
        self.ui.record_push_button.clicked.connect(self.screen_shooter.toggle_recording_slot)
        self.ui.imagelabel_lineEdit.textChanged.connect(self.change_image_label)

        self.image_viewer.click_move_signal.connect(self.sequencer.move_rel_frame)

        # Tiling
        self.ui.tile_and_navigate_pushbutton.clicked.connect(self.start_tiling)
        self.start_tiling_signal.connect(self.sequencer.tile)
        self.sequencer.tile_done_signal.connect(self.stop_tiling)

        # Screenshot and comment buttons
        self.ui.misc_screenshot_button.clicked.connect(self.take_image)

        # Filter out key releases in comment box
        self.catchkeys = CatchKeys()
        self.ui.comment_box.installEventFilter(self.catchkeys)
        self.ui.user_comment_button.clicked.connect(self.send_user_comment)

        # Stage movement buttons
        self.stage_fast_moverel_signal.connect(self.sequencer.move_rel_fast)

        # Settings
        self.setting_changed_signal.connect(self.sequencer.presets.change_value)
        self.nvsetting_changed_signal.connect(self.sequencer.settings.change_value)
        self.settings_save_signal.connect(self.sequencer.settings.save_yaml)

        # Preset Manager
        self.ui.save_preset_pushButton.clicked.connect(self.modify_preset)
        self.ui.add_preset_pushButton.clicked.connect(self.add_preset)
        self.add_preset_signal.connect(self.preset_manager.modify_preset)
        self.modify_preset_signal.connect(self.preset_manager.modify_preset)
        self.remove_preset_signal.connect(self.preset_manager.remove_preset)
        self.preset_model = QtGui.QStandardItemModel()
        self.ui.tile_preset_listView.setModel(self.preset_model)
        self.ui.remove_preset_pushButton.clicked.connect(self.remove_preset)

        # Objective calibration
        self.obj_cal_pix_vector = QtCore.QLine()
        self.obj_cal_stage_vector = QtCore.QLine()
        self.ui.objective_calibration_button.clicked.connect(self.objective_calibration_start)
        self.stage_get_pos_signal.connect(self.sequencer.stage.get_position)
        self.objective_calibrating = False

        self.setup_comboboxes()
        self.setup_laser_ui()
        self.setup_af_ui()

        # Restore last window state
        settings = QtCore.QSettings("Wheeler Lab", "LCL Software")
        try:
            self.restoreGeometry(settings.value("MainWindow/geometry"))
            self.restoreState(settings.value("MainWindow/windowState"))
        except TypeError:  # If no previous settings
            logger.info("No saved window state")
            pass

        self.show()

        logger.info('finished gui init')

    def setup_laser_ui(self):
        self.ui.repetition_rate_double_spin_box.valueChanged.connect(
            partial(self.nonpreset_setting_change, "laser_rep"))
        self.ui.burst_count_double_spin_box.valueChanged.connect(
            partial(self.nonpreset_setting_change, "laser_burst"))
        self.laser_arm_signal.connect(self.sequencer.laser_arm)
        self.laser_disarm_signal.connect(self.sequencer.laser_disarm)
        self.laser_fire_signal.connect(self.sequencer.laser_fire)
        self.laser_stop_signal.connect(self.sequencer.laser_stop)

    def setup_af_ui(self):
        self.sequencer.stage.af_status_signal.connect(self.ui.autofocus_status_label.setText)
        self.af_mode_signal.connect(self.sequencer.stage.af_set_state)
        self.ui.af_logcal_button.clicked.connect(partial(self.af_mode_signal.emit, 'log_cal'))
        self.ui.af_idle_button.clicked.connect(partial(self.af_mode_signal.emit, 'idle'))
        self.ui.af_ready_button.clicked.connect(partial(self.af_mode_signal.emit, 'ready'))
        self.ui.af_lock_button.clicked.connect(partial(self.af_mode_signal.emit, 'lock'))
        self.ui.af_gaincal_button.clicked.connect(partial(self.af_mode_signal.emit, 'gain_cal'))
        self.ui.af_dither_button.clicked.connect(partial(self.af_mode_signal.emit, 'dither'))
        self.ui.af_balance_button.clicked.connect(partial(self.af_mode_signal.emit, 'balance'))
        self.ui.af_fcurve_button.clicked.connect(partial(self.af_mode_signal.emit, 'focus_curve'))
        self.ui.af_led_slider.valueChanged.connect(self.sequencer.stage.af_set_led)

    def setup_comboboxes(self):
        self.ui.excitation_lamp_on_combobox.addItems(wl_to_idx.keys())
        self.ui.excitation_lamp_on_combobox.activated.connect(
            partial(self.change_setting, 'excitation'))

        self.ui.cube_position_combobox.addItems(['0', '1', '2', '3'])
        self.ui.cube_position_combobox.setCurrentIndex(
            self.preset_manager.get_values()['cube_position'])
        self.ui.cube_position_combobox.activated.connect(
            partial(self.change_setting, 'cube_position'))

        self.ui.intensity_spin_box.valueChanged.connect(
            partial(self.change_setting, 'intensity'))
        self.ui.emission_spin_box.valueChanged.connect(
            partial(self.change_setting, 'emission'))

        self.ui.magnification_combobox.addItems(
            [f"{n}: {str(i)}" for n, i in self.sequencer.objectives.objectives.items()])
        self.ui.magnification_combobox.setCurrentIndex(self.sequencer.objectives.current_index)
        self.ui.magnification_combobox.currentIndexChanged.connect(
            partial(self.nonpreset_setting_change, 'objective_index'))

        self.ui.preset_comboBox.currentTextChanged.connect(
            partial(self.nonpreset_setting_change, 'preset'))
        self.preset_manager.settings_changed_signal.connect(self.preset_settings_update)
        self.sequencer.settings.settings_changed_signal.connect(self.nonpreset_setting_update)
        self.preset_manager.presets_changed_signal.connect(self.presets_update)

        self.ui.exposure_spin_box.valueChanged.connect(partial(self.change_setting, 'exposure'))
        self.ui.gain_spin_box.valueChanged.connect(partial(self.change_setting, 'gain'))
        self.ui.brightness_spin_box.valueChanged.connect(
            partial(self.change_setting, 'brightness'))

        self.ui.step_size_spin_box.valueChanged.connect(
            partial(self.nonpreset_setting_change, 'stage_step_um'))

        # Fetch initial values
        self.preset_settings_update(self.preset_manager.get_values())
        self.nonpreset_setting_update(self.sequencer.settings.get_values())
        self.presets_update(list(self.preset_manager.presets.keys()))

    def change_setting(self, key: str, value):
        self.setting_changed_signal.emit(key, value)

    def nonpreset_setting_change(self, key: str, value):
        self.nvsetting_changed_signal.emit(key, value)

    def set_ui_enabled(self, activate: bool):
        self.ui.acquisition_dockwidget.setEnabled(activate)
        self.ui.instrument_dockwidget.setEnabled(activate)

    @QtCore.pyqtSlot(dict)
    def preset_settings_update(self, settings: typing.Mapping[str, SettingValue]) -> None:
        self.ui.exposure_spin_box.setValue(settings['exposure'])
        self.ui.brightness_spin_box.setValue(settings['brightness'])
        self.ui.gain_spin_box.setValue(settings['gain'])
        self.ui.cube_position_combobox.setCurrentIndex(settings['cube_position'])
        self.ui.intensity_spin_box.setValue(settings['intensity'])
        self.ui.excitation_lamp_on_combobox.setCurrentIndex(settings['excitation'])
        self.ui.emission_spin_box.setValue(strip_letters(settings['emission']))

    @QtCore.pyqtSlot(dict)
    def nonpreset_setting_update(self, settings: typing.Mapping[str, SettingValue]) -> None:
        self.ui.magnification_combobox.setCurrentIndex(settings['objective_index'])
        self.ui.repetition_rate_double_spin_box.setValue(settings['laser_rep'])
        self.ui.burst_count_double_spin_box.setValue(settings['laser_burst'])
        self.ui.step_size_spin_box.setValue(settings['stage_step_um'])

    @QtCore.pyqtSlot(list)
    def presets_update(self, presets: typing.Sequence):
        # Need to disconnect TextChanged signal to prevent accidentally changing preset
        self.ui.preset_comboBox.currentTextChanged.disconnect()
        self.ui.preset_comboBox.clear()
        self.ui.preset_comboBox.addItems(presets)
        self.ui.preset_comboBox.currentTextChanged.connect(
            partial(self.nonpreset_setting_change, 'preset'))
        self.ui.preset_comboBox.setCurrentText(self.sequencer.presets.preset)
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

    def _get_checked_presets(self) -> typing.Sequence[str]:
        return [self.preset_model.item(i).text()
                for i in range(self.preset_model.rowCount())
                if self.preset_model.item(i).checkState()]

    def _get_text(self, text_prompt):
        text, ok_pressed = QInputDialog.getText(self, 'Experiment Input', text_prompt, QLineEdit.Normal, "")
        if ok_pressed and text is not None:
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
                user_input = self._get_text(var_dict[key])
                val = user_input.lower()
                if any(vowel in val for vowel in checks):
                    logger.info('%s %s', key, user_input)
                    good_entry = True

    @QtCore.pyqtSlot()
    def objective_calibration_start(self):
        self.objective_calibrating = True
        self.ui.statusBar.showMessage("Move an object near one corner of the frame, then click on it. "
                                      "ESC to cancel")
        self.set_ui_enabled(False)
        self.image_viewer.click_move_signal.disconnect()
        self.image_viewer.click_move_pix_signal.connect(self.objective_calibration_p1)

    @QtCore.pyqtSlot(int, int)
    def objective_calibration_p1(self, x: int, y: int):
        self.image_viewer.click_move_pix_signal.disconnect()
        self.obj_cal_pix_vector.setP1(QtCore.QPoint(x, y))
        self.sequencer.stage.position_signal.connect(self.objective_calibration_p1_stage)
        self.stage_get_pos_signal.emit()

    @QtCore.pyqtSlot(tuple)
    def objective_calibration_p1_stage(self, position: typing.Tuple[int, int, int]):
        self.sequencer.stage.position_signal.disconnect()
        stage_x, stage_y, _ = position
        self.obj_cal_stage_vector.setP1(QtCore.QPoint(stage_x, stage_y))
        self.ui.statusBar.showMessage("Move object near opposite corner of the frame, then click on it. "
                                      "ESC to cancel")
        self.image_viewer.click_move_pix_signal.connect(self.objective_calibration_p2)

    @QtCore.pyqtSlot(int, int)
    def objective_calibration_p2(self, x: int, y: int):
        self.set_ui_enabled(True)
        self.image_viewer.click_move_pix_signal.disconnect()
        self.obj_cal_pix_vector.setP2(QtCore.QPoint(x, y))
        self.sequencer.stage.position_signal.connect(self.objective_calibration_p2_stage)
        self.stage_get_pos_signal.emit()

    @QtCore.pyqtSlot(tuple)
    def objective_calibration_p2_stage(self, position: typing.Tuple[int, int, int]):
        self.sequencer.stage.position_signal.disconnect()
        stage_x, stage_y, _ = position
        self.obj_cal_stage_vector.setP2(QtCore.QPoint(stage_x, stage_y))
        angle = self.sequencer.objectives.calibrate_current_objective(
            self.obj_cal_pix_vector, self.obj_cal_stage_vector)
        self.ui.statusBar.showMessage(f"Estimated stage angle: {angle}°", 5000)
        messagebox = QMessageBox(QMessageBox.Question,  # icon
                                 "Set camera angle?",  # title
                                 f"Set camera angle to {angle:.3f}°?",  # text
                                 QMessageBox.Ok | QMessageBox.Cancel,  # buttons
                                 self  # parent
                                 )
        messagebox.setDefaultButton(QMessageBox.Ok)
        messagebox.setModal(True)
        response = messagebox.exec()

        if response == QMessageBox.Ok:
            self.sequencer.settings.change_value('camera_angle', angle)

        self.image_viewer.click_move_signal.connect(self.sequencer.move_rel_frame)

    @QtCore.pyqtSlot()
    def objective_calibration_cancel(self):
        if self.objective_calibrating:
            try:
                self.image_viewer.click_move_pix_signal.disconnect()
            except TypeError:
                pass
            self.image_viewer.click_move_signal.connect(self.sequencer.move_rel_frame)

            self.set_ui_enabled(True)
            self.ui.statusBar.showMessage("Objective calibration cancelled", 1500)
            self.objective_calibrating = False

    @QtCore.pyqtSlot()
    def take_image(self):
        self.screen_shooter.requested_frames.appendleft(self.ui.imagelabel_lineEdit.text())

    @QtCore.pyqtSlot(str)
    def change_image_label(self, label: str):
        self.screen_shooter.image_title = label

    @QtCore.pyqtSlot()
    def start_tiling(self):
        cols = self.ui.tile_cols_spinBox.value()
        rows = self.ui.tile_rows_spinBox.value()
        self.set_ui_enabled(False)
        logger.info("Starting tiling")
        self.start_tiling_signal.emit(self._get_checked_presets(), cols, rows)

    @QtCore.pyqtSlot(list, list)
    def stop_tiling(self, *args):
        logger.info("Finished tiling")
        self.set_ui_enabled(True)

    def send_user_comment(self):
        logger.info('user comment: %s', self.ui.comment_box.toPlainText())
        self.ui.comment_box.clear()

    def laser_arm(self):
        self.ui.laser_groupbox.setTitle('Laser - ARMED')
        self.laser_arm_signal.emit()

    @QtCore.pyqtSlot()
    def laser_fire(self):
        self.laser_fire_signal.emit(self.ui.laser_image_checkbox.isChecked(),
                                    self.ui.laser_video_checkbox.isChecked(),
                                    self.ui.z_offset_spinBox.value())

    def laser_disarm(self):
        self.ui.laser_groupbox.setTitle('Laser')
        self.laser_disarm_signal.emit()

    def _keyboard_move(self, direction: str, mag: int):
        dir_dict = {'left': np.array([-1, 0, 0]),
                    'right': np.array([1, 0, 0]),
                    'up': np.array([0, -1, 0]),
                    'down': np.array([0, 1, 0]),
                    'in': np.array([0, 0, -1]),
                    'out': np.array([0, 0, 1])}
        vector = dir_dict[direction] * mag
        self.stage_fast_moverel_signal.emit(*vector.astype(int))

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            key_control_dict = {
                QtCore.Qt.Key_Minus: partial(self._keyboard_move, 'out', 50),
                QtCore.Qt.Key_Underscore: partial(self._keyboard_move, 'out', 5000),
                QtCore.Qt.Key_Equal: partial(self._keyboard_move, 'in', 50),
                QtCore.Qt.Key_Plus: partial(self._keyboard_move, 'in', 5000),
                QtCore.Qt.Key_A: partial(self._keyboard_move, 'left',
                                         self.ui.step_size_spin_box.value() * 10),
                QtCore.Qt.Key_S: partial(self._keyboard_move, 'down',
                                         self.ui.step_size_spin_box.value() * 10),
                QtCore.Qt.Key_D: partial(self._keyboard_move, 'right',
                                         self.ui.step_size_spin_box.value() * 10),
                QtCore.Qt.Key_W: partial(self._keyboard_move, 'up',
                                         self.ui.step_size_spin_box.value() * 10),
                QtCore.Qt.Key_Control: self.laser_arm,
                QtCore.Qt.Key_F: self.laser_fire,
                QtCore.Qt.Key_Escape: self.objective_calibration_cancel
                # 81: laser.qswitch_auto,
                # 73: stage.start_roll_down,
                # 75:self.autofocuser.roll_backward,
                # 79:self.start_autofocus,
                # 71:self.toggle_dmf_or_lysis,
                # 84: stage.move_left_one_well_slot,
                # 89: stage.move_right_one_well_slot,
                # 96: self.screen_shooter.save_target_image,
            }
            try:
                key_control_dict[event.key()]()
            except KeyError:
                pass

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            # logger.info('key released: %s', event.key())
            key_control_dict = {
                QtCore.Qt.Key_Control: self.laser_disarm,
                QtCore.Qt.Key_F: self.laser_stop_signal.emit
            }
            try:
                key_control_dict[event.key()]()
            except KeyError:
                pass

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        logger.info("Closed MainWindow")
        self.sequencer.settings.save_yaml()
        settings = QtCore.QSettings("Wheeler Lab", "LCL Software")
        settings.setValue("MainWindow/geometry", self.saveGeometry())
        settings.setValue("MainWindow/windowState", self.saveState())
        self.zoom_dockwidget.close()
        self.screen_shooter.set_recording_state(False)
        self.screenshooter_thread.quit()
        self.sequencer_thread.quit()
        super(MainWindow, self).closeEvent(a0)
