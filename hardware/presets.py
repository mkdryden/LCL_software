import logging
import typing
import time

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QWidget, QMessageBox, QInputDialog, QLineEdit
import yaml

from utils import preset_loc, wait_signal

logger = logging.getLogger(__name__)


class SettingValue(object):
    def __init__(self, name, default_value=None, changed_call: typing.Callable = None,
                 change_done_signal: QtCore.pyqtSignal = None, delay_ms: int = None):
        """

        :param name: Name stored in parameters dict
        :param default_value: Default parameter value
        :param changed_call: Function/method to be called when value is changed
        :param change_done_signal: Signal emitted by controller when change is complete
                                   (Cannot be emitted directly by changed_call!)
        :param delay_ms:
        """
        super(SettingValue, self).__init__()
        self.name = name
        self.changed = changed_call
        self.default_value = default_value
        self._value = default_value
        self.signal = change_done_signal
        self.delay_ms = delay_ms

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (self.changed is not None) and (self._value != value):
            if self.signal is not None:
                with wait_signal(self.signal, timeout=3000):
                    logger.info("Setting %s to %s", self.name, value)
                    self.changed(value)
            elif self.delay_ms is not None:
                self.changed(value)
                with wait_signal(timeout=self.delay_ms):
                    pass
            else:
                self.changed(value)
        self._value = value

    def set_default(self):
        self.value = self.default_value


class PresetManager(QtCore.QObject):
    number_of_checked_presets_signal = QtCore.pyqtSignal('PyQt_PyObject')
    preset_loaded_signal = QtCore.pyqtSignal(dict)
    presets_changed_signal = QtCore.pyqtSignal(list)

    def __init__(self, parent=None, window=None):
        super(PresetManager, self).__init__(parent)
        self.presets = {}
        self.preset = None

        self._settings = {}
        self.saving = False
        self.model = None
        self.checked_names = []
        self.current_channel = 0
        self.number_of_channels = 0
        self.window = window

    def add_setting(self, setting: SettingValue):
        self._settings[setting.name] = setting
        setting.set_default()

    @QtCore.pyqtSlot(str)
    def set_preset(self, preset: str):
        if preset != self.preset:
            try:
                self.change_values(self.presets[preset])
            except KeyError:
                logger.error("Preset not found: %s", preset)
                return
            self.preset = preset
            self.preset_loaded_signal.emit(self.get_values())

    @QtCore.pyqtSlot(dict)
    def change_values(self, values: typing.Mapping):
        for key, value in values.items():
            self.change_value(key, value)

    def change_value(self, key: str, value):
        # try:
            self._settings[key].value = value
        # except KeyError:
        #     logger.warning("Invalid setting key: %s", key)

    def get_values(self):
        return {setting.name: setting.value for setting in self._settings.values()}

    def load_presets(self, preset_file=None):
        try:
            if preset_file is None:
                preset_file = preset_loc
            with open(preset_file) as f:
                self.presets = yaml.load(f, Loader=yaml.SafeLoader)
        except FileNotFoundError:
            logger.warning("Presets file not found, populating with default.")
            self.presets = {'Default': {name: setting.value
                                        for name, setting in self._settings.items()}}

        if 'Default' in self.presets.keys():
            self.set_preset('Default')
        else:
            self.set_preset(next(iter(self.presets)))
        self.presets_changed_signal.emit(list(self.presets.keys()))

    def save_presets(self, preset_file=None):
        if preset_file is None:
            preset_file = preset_loc
        with open(preset_file, 'w') as f:
            yaml.dump(self.presets, f)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def modify_preset(self, name: str = None) -> None:
        """
        Save current settings into current preset.
        :param name: Name of new preset. (If None, use current)
        """
        if name is not None:
            self.preset = name
        self.presets[self.preset] = self.get_values()
        logger.info("Preset %s saved", self.preset)
        self.save_presets()

        if name is not None:
            self.set_preset(name)
            self.presets_changed_signal.emit(list(self.presets.keys()))

    @QtCore.pyqtSlot(str)
    def remove_preset(self, name: str) -> None:
        """
        Delete preset by name. Will fail if trying to delete current preset.
        :param name: preset to delete
        """
        if name == self.preset:
            logger.error("Cannot delete current preset.")
            return
        try:
            del(self.presets[name])
        except KeyError:
            logger.error("Tried to delete non-existent preset %s", name)
            return
        self.save_presets()
