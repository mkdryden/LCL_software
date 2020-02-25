import os
import datetime
import threading
import typing
import logging
from collections import deque
from contextlib import contextmanager

from PyQt5 import QtCore
from PyQt5.QtWidgets import QBoxLayout, QSpacerItem, QWidget
import cv2
from PIL import Image
import numpy as np
import tensorflow as tf
import ffmpeg
from appdirs import AppDirs

logger = logging.getLogger(__name__)


def now():
    return datetime.datetime.now().strftime('%d_%m_%Y___%H.%M.%S')


def comment(text):
    '''
    prints to screen and logs simultaneously
    '''
    splits = text.split()
    text = ''
    for split in splits:
        text += split + ' '
    now_time = now()
    logging.info('{0}{1}{2}'.format(text,
                                    '.' * (80 - (len(text) + len(now_time))),
                                    now_time))
    print(text, threading.current_thread())


@contextmanager
def wait_signal(signal: QtCore.pyqtSignal = None, timeout=10000):
    """Block loop until signal emitted, or timeout (ms) elapses."""
    loop = QtCore.QEventLoop()
    timer = QtCore.QTimer()
    timer.setSingleShot(True)

    def timed_out():
        logger.warning("Timed out while waiting for %s", signal)
        loop.quit()

    if signal is None and timeout is None:
        logger.error("Cannot call wait_signal with both signal and timeout as None.")
        return

    if signal is not None:
        signal.connect(loop.quit)

    yield

    if timeout is not None:
        timer.timeout.connect(timed_out)
        timer.start(timeout)

    loop.exec_()


class AspectRatioWidget(QWidget):
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self.setLayout(QBoxLayout(QBoxLayout.LeftToRight, self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.widget = widget
        self.aspect = 1
        #  add spacer, then widget, then spacer
        self.layout().addItem(QSpacerItem(0, 0))
        self.layout().addWidget(self.widget)
        self.layout().addItem(QSpacerItem(0, 0))

    @QtCore.pyqtSlot(float)
    def aspect_changed_slot(self, aspect: float):
        self.aspect = aspect
        w = self.width()
        h = self.height()

        if w / h > self.aspect:  # too wide
            self.layout().setDirection(QBoxLayout.LeftToRight)
            widget_stretch = h * self.aspect
            outer_stretch = (w - widget_stretch) / 2 + 0.5
        else:  # too tall
            self.layout().setDirection(QBoxLayout.TopToBottom)
            widget_stretch = w / self.aspect
            outer_stretch = (h - widget_stretch) / 2 + 0.5

        self.layout().setStretch(0, outer_stretch)
        self.layout().setStretch(1, widget_stretch)
        self.layout().setStretch(2, outer_stretch)

    def resizeEvent(self, e):
        w = e.size().width()
        h = e.size().height()
        self.aspect

        if w / h > self.aspect:  # too wide
            self.layout().setDirection(QBoxLayout.LeftToRight)
            widget_stretch = h * self.aspect
            outer_stretch = (w - widget_stretch) / 2 + 0.5
        else:  # too tall
            self.layout().setDirection(QBoxLayout.TopToBottom)
            widget_stretch = w / self.aspect
            outer_stretch = (h - widget_stretch) / 2 + 0.5

        self.layout().setStretch(0, outer_stretch)
        self.layout().setStretch(1, widget_stretch)
        self.layout().setStretch(2, outer_stretch)


class ScreenShooter(QtCore.QObject):
    """
    handles the various different types of screenshots
    """
    screenshot_done_signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(ScreenShooter, self).__init__(parent)
        self.requested_frames = deque()
        self.image_title = ""
        self.recording = False
        self.movie_file = None
        self.image = None
        self.ffmpeg = None

    @QtCore.pyqtSlot(np.ndarray)
    def screenshot_slot(self, image):
        self.image = image

        # Video
        if self.recording:
            self.ffmpeg.stdin.write(self.image.tobytes())

        # Screenshot
        try:
            name = self.requested_frames.pop()
        except IndexError:
            return
        im = Image.fromarray(np.left_shift(self.image, 4))  # Zero pad 12 to 16 bits
        im.save(os.path.join(experiment_folder_location,
                             '{}_{}.tif'.format(name, now())),
                format='tiff', compression='tiff_lzw')

    @QtCore.pyqtSlot(np.ndarray, str)
    def save_named_image(self, image: np.ndarray, name: str):
        self.image = image
        im = Image.fromarray(np.left_shift(self.image, 4))  # Zero pad 12 to 16 bits
        im.save(os.path.join(experiment_folder_location, '{}_{}.tif'.format(name, now())),
                format='tiff', compression='tiff_lzw')

    @QtCore.pyqtSlot(bool)
    def set_recording_state(self, state: bool):
        """
        Set recording on or off.
        :param state: If true, starts recording (if not already), otherwise stops.
        """
        if state and not self.recording:
            self.ffmpeg = (
                ffmpeg.input('pipe:', format='rawvideo', pix_fmt='gray12le',
                             s='{}x{}'.format(*reversed(self.image.shape)), framerate=20)
                      .output(os.path.join(experiment_folder_location,
                                           self.image_title + "-" + now() + ".mp4"),
                              crf=21, preset="fast", pix_fmt='yuv420p')
                      .overwrite_output()
                      .run_async(pipe_stdin=True)
            )
            self.recording = True
            return
        if not state and self.recording:  # Finish Recording
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait()
            self.ffmpeg = None
            logger.info("Finished saving video %s", self.image_title)
            self.recording = False

    @QtCore.pyqtSlot()
    def toggle_recording_slot(self):
        self.set_recording_state(not self.recording)

    @QtCore.pyqtSlot(list, list)
    def save_well_imgs(self, imgs: typing.List[typing.List[np.ndarray]],
                       presets: typing.Sequence[typing.Tuple[str, int]]):
        """

        :param imgs: Nested list of 3D ndarrays of images.
        :param presets: List of name, wavelength tuples with same length as 3rd dimension of imgs.
        :return:
        """
        save_loc = os.path.join(experiment_folder_location, f'{self.image_title}_{now()}')
        im_list = []

        for x, i in enumerate(imgs):
            im_list.append([])
            for y, img in enumerate(i):
                # noinspection PyTypeChecker
                im = Image.fromarray(channels_to_rgb_img(img, [preset[1] for preset in presets]))
                im_list[x].append(im)

                for n, preset in enumerate(presets):
                    fs_im = Image.fromarray(np.left_shift(img[..., n], 4))
                    fs_im.save(save_loc + f"-{x}_{y}-" + preset[0] + ".tif",
                               format='tiff', compression='tiff_lzw')

        im_width, im_height = im_list[0][0].size
        stitched_im = Image.new('RGB', (im_width * len(im_list), im_height * len(im_list[0])))

        for x, i in enumerate(im_list):
            for y, img in enumerate(i):
                stitched_im.paste(img, box=(x * im_width, y * im_height))

        stitched_im.save(save_loc + "-stitched-c.jpg", format='jpeg')


class MeanIoU(object):
    # taken from http://www.davidtvs.com/keras-custom-metrics/
    def __init__(self, num_classes):
        super().__init__()
        self.num_classes = num_classes

    def mean_iou(self, y_true, y_pred):
        # Wraps np_mean_iou method and uses it as a TensorFlow op.
        # Takes numpy arrays as its arguments and returns numpy arrays as
        # its outputs.
        return tf.py_func(self.np_mean_iou, [y_true, y_pred], tf.float32)

    def np_mean_iou(self, y_true, y_pred):
        # Compute the confusion matrix to get the number of true positives,
        # false positives, and false negatives
        # Convert predictions and target from categorical to integer format
        target = np.argmax(y_true, axis=-1).ravel()
        predicted = np.argmax(y_pred, axis=-1).ravel()

        # Trick from torchnet for bincounting 2 arrays together
        # https://github.com/pytorch/tnt/blob/master/torchnet/meter/confusionmeter.py
        x = predicted + self.num_classes * target
        bincount_2d = np.bincount(x.astype(np.int32), minlength=self.num_classes ** 2)
        assert bincount_2d.size == self.num_classes ** 2
        conf = bincount_2d.reshape((self.num_classes, self.num_classes))

        # Compute the IoU and mean IoU from the confusion matrix
        true_positive = np.diag(conf)
        false_positive = np.sum(conf, 0) - true_positive
        false_negative = np.sum(conf, 1) - true_positive

        # Just in case we get a division by 0, ignore/hide the error and set the value to 0
        with np.errstate(divide='ignore', invalid='ignore'):
            iou = true_positive / (true_positive + false_positive + false_negative)
        iou[np.isnan(iou)] = 0

        return np.mean(iou).astype(np.float32)


def channels_to_rgb_img(img: np.ndarray, wavelengths: typing.Sequence[int]):
    img = np.right_shift(img, 4).astype(np.uint8)  # Convert to 8-bit
    new_shape = img.shape[:-1] + (3,)
    new_img = np.zeros(new_shape).astype(np.uint8)

    channels = {wl: n for n, wl in enumerate(wavelengths)}

    for wl in sorted(wavelengths):  # Sort so that BF channel goes first
        if int(wl) == 0:
            # this is a BF channel
            for i in range(3):
                new_img[:, :, i] = img[:, :, channels[wl]]
        else:
            # now add proper fluorescence on top
            rgb_val = wl_to_rbg(wl)
            new_overlay = np.zeros(new_shape).astype(np.uint8)
            for j in range(3):
                new_overlay[:, :, j] = rgb_val[j] / 255 * img[:, :, channels[wl]]
            new_img = cv2.addWeighted(new_img, .5, new_overlay, 1, .6)
    return new_img


# stolen from: http://codingmess.blogspot.com/2009/05/conversion-of-wavelength-in-nanometers.html
def wl_to_rbg(wavelength: typing.SupportsInt) -> typing.Tuple[int, int, int]:
    w = int(wavelength)

    # colour
    if 380 <= w < 440:
        R = -(w - 440.) / (440. - 350.)
        G = 0.0
        B = 1.0
    elif 440 <= w < 490:
        R = 0.0
        G = (w - 440.) / (490. - 440.)
        B = 1.0
    elif 490 <= w < 510:
        R = 0.0
        G = 1.0
        B = -(w - 510.) / (510. - 490.)
    elif 510 <= w < 580:
        R = (w - 510.) / (580. - 510.)
        G = 1.0
        B = 0.0
    elif 580 <= w < 645:
        R = 1.0
        G = -(w - 645.) / (645. - 580.)
        B = 0.0
    elif 645 <= w <= 780:
        R = 1.0
        G = 0.0
        B = 0.0
    else:
        R = 0.0
        G = 0.0
        B = 0.0

    # intensity correction
    if 380 <= w < 420:
        SSS = 0.3 + 0.7 * (w - 350) / (420 - 350)
    elif 420 <= w <= 700:
        SSS = 1.0
    elif 700 < w <= 780:
        SSS = 0.3 + 0.7 * (780 - w) / (780 - 700)
    else:
        SSS = 0.0
    SSS *= 255

    return int(SSS * R), int(SSS * G), int(SSS * B)


appdirs = AppDirs("LCL-interface", "Wheeler Lab")
experiment_name = 'experiment_{}'.format(now())
experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Experiments', experiment_name)
