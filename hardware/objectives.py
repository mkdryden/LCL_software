import logging
import typing
import os

import yaml
from PyQt5 import QtCore

from utils import appdirs, wait_signal
from hardware.asi_controller import StageController

logger = logging.getLogger(__name__)
default_file = os.path.join(appdirs.user_config_dir, 'objectives.yaml')


class Objective(yaml.YAMLObject):
    yaml_tag = "!Objective"

    def __init__(self, name: str, mag: int, z_offset: int = 0,
                 field_dimx: int = 6411, field_dimy: int = 3397):
        self.name = name
        self.mag = mag
        self.z_offset = z_offset
        self.field_dimx = field_dimx
        self.field_dimy = field_dimy

    def __repr__(self):
        return f"{type(self).__name__}({self.name}, mag={self.mag}, z_offset={self.z_offset}, "\
               f"field_dimx={self.field_dimx}, field_dimy={self.field_dimy})"

    def __str__(self):
        return f"{self.name} Objective"


class Objectives(QtCore.QObject):
    objectives_changed = QtCore.pyqtSignal(list)
    objective_changed = QtCore.pyqtSignal(str)

    def __init__(self, controller: StageController = None):
        super(Objectives, self).__init__()
        self.controller = controller
        self.objectives = {n: Objective("Empty", 1) for n in range(1, 7)}
        if self.controller is not None:
            if self.controller.connected:
                self.current_index = self.controller.get_objective_position()
                logger.info("Current objective position: %s", self.current_index)
            else:
                self.current_index = None
                logger.error("Can't fetch current objective; controller not connected")

    @property
    def current_objective(self) -> Objective:
        return self.objectives[self.current_index]

    def load_yaml(self, path=None):
        try:
            if path is None:
                path = default_file
            with open(path) as f:
                loaded = yaml.load(f, Loader=yaml.FullLoader)
                self.objectives.update(loaded)
        except FileNotFoundError as e:
            logger.warning("Objective file not found")
            raise e

        self.objectives_changed.emit([obj.name for obj in self.objectives.values()])

    def save_yaml(self, path: str = None):
        if path is None:
            path = default_file
        with open(path, 'w') as f:
            yaml.dump(self.objectives, f)

    def set_objective(self, obj: Objective, position: int):
        if position in self.objectives:
            self.objectives[position] = obj
        else:
            logger.error("Invalid objective position: %s", position)

    def change_objective(self, position: int):
        if position not in self.objectives:
            logger.error("Invalid objective position: %s", position)
            return
        with wait_signal(self.controller.done_moving_signal, timeout=15000):
            self.controller.move(z=0)
        with wait_signal(self.controller.done_moving_signal, timeout=15000):
            self.controller.set_objective_position(position)
        self.current_index = position


if __name__ == "__main__":
    objectives = Objectives()
    try:
        objectives.load_yaml()
    except FileNotFoundError:
        objective = Objective("Oly 20x", mag=20)
        objectives.set_objective(objective, 1)
        objectives.save_yaml()

    print("\n".join((str(i) for i in objectives.objectives.values())))
