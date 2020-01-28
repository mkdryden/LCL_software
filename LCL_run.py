import os
import sys
import logging
import argparse
import pathlib

from PyQt5.QtWidgets import QApplication

from presets import PresetManager
import utils
from ui.main_window import MainWindow
from hardware.asi_controller import StageController
from hardware.fluorescence_controller import ExcitationController
from hardware.laser_controller import LaserController

# Setup Logging
logger = logging.getLogger(__name__)

logging_choices = {'DEBUG': logging.DEBUG,
                   'INFO': logging.INFO,
                   'WARNING': logging.WARNING,
                   'ERROR': logging.ERROR}


if __name__ == '__main__':
    # TODO refactor so the gui runs on separate process from "stage"
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-run', action='store_true')
    parser.add_argument('--log-level', choices=logging_choices, default="INFO")
    parser.add_argument('--experiment-path', type=str, default=None)
    args = parser.parse_args()

    if args.experiment_path is not None:
        utils.experiment_folder_location = os.path.join(os.path.expanduser(args.experiment_path),
                                                        utils.experiment_name)

    # Make sure paths exist
    pathlib.Path(utils.experiment_folder_location).mkdir(parents=True, exist_ok=True)
    pathlib.Path(utils.appdirs.user_config_dir).mkdir(parents=True, exist_ok=True)

    # Logging
    logfile = os.path.join(utils.experiment_folder_location, '{}.log'.format(utils.experiment_name))
    root_logger = logging.getLogger()
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    log_handlers = [logging.StreamHandler(), logging.FileHandler(logfile)]
    log_formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s: [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    for handler in log_handlers:
        handler.setFormatter(log_formatter)
        root_logger.addHandler(handler)
    root_logger.setLevel(logging_choices[args.log_level])

    app = QApplication(sys.argv)
    asi_controller = StageController()
    asi_controller.init_controller()
    excitation = ExcitationController()
    excitation.init_controller()
    laser = LaserController()
    laser.init_controller()
    preset_manager = PresetManager()
    window = MainWindow(args.test_run, asi_controller=asi_controller, laser_controller=laser,
                        excitation=excitation, preset_manager=preset_manager)
    logger.info('QApplication exit with code: %s', str(app.exec_()))
    sys.exit()
