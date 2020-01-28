from PyQt5 import QtCore
from PyQt5.QtWidgets import QBoxLayout, QSpacerItem, QWidget
import os
import datetime
import cv2
from contextlib import contextmanager
from PIL import Image
import logging
import numpy as np
import threading
import tensorflow as tf
import matplotlib.pyplot as plt
import ffmpeg

logger = logging.getLogger(__name__)


def now():
    return datetime.datetime.now().strftime('%d_%m_%Y___%H.%M.%S.%f')


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

    if signal and timeout is None:
        logger.error("Cannot call wait_signal with both signal and timeout as None.")
        return

    if signal is not None:
        signal.connect(loop.quit)

    yield

    if timeout is not None:
        QtCore.QTimer.singleShot(timeout, loop.quit)

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


def save_well_imgs(img: np.ndarray, fs_img: np.ndarray, names: list):
    save_loc = os.path.join(experiment_folder_location, '{}___{}'.format('well_image', now()))
    im = Image.fromarray(img)
    im.save(save_loc + "-c.jpg", format='jpeg')

    # Save each channel as a separate file
    for n, name in enumerate(names):
        fs_im = Image.fromarray(np.left_shift(fs_img[..., n], 4))
        fs_im.save(save_loc + "-" + name + ".tif", format='tiff', compression='tiff_lzw')


class ScreenShooter(QtCore.QObject):
    """
    handles the various different types of screenshots
    """

    def __init__(self, parent=None):
        super(ScreenShooter, self).__init__(parent)
        self.requested_frames = 0
        self.image_count = 0
        self.image_title = ''
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
            logger.debug('writing frame %s to disk', self.image_count)
        self.image_count += 1

        # Screenshot
        if self.requested_frames > 0:
            im = Image.fromarray(np.left_shift(self.image, 4))  # Zero pad 12 to 16 bits
            im.save(os.path.join(experiment_folder_location,
                                 '{}___{}.tif'.format(self.image_title, now())),
                    format='tiff', compression='tiff_lzw')

            self.requested_frames -= 1
            logger.debug('writing frame %s to disk', self.image_count)

    @QtCore.pyqtSlot()
    def toggle_recording_slot(self):
        self.recording = not self.recording
        if self.recording:  # Start Recording
            self.ffmpeg = (
                ffmpeg.input('pipe:', format='rawvideo', pix_fmt='gray12le',
                             s='{}x{}'.format(*reversed(self.image.shape)), framerate=20)
                    .output(os.path.join(experiment_folder_location, self.image_title + now() + ".mp4"),
                            crf=21, preset="fast", pix_fmt='yuv420p')
                    .overwrite_output()
                    .run_async(pipe_stdin=True)
            )

        if not self.recording:  # Finish Recording
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait()
            self.ffmpeg = None
            logger.info("Finished saving video %s", self.image_title)

    @QtCore.pyqtSlot()
    def save_target_image(self):
        comment('taking target picture')
        self.image_title = 'target'
        self.requested_frames += 1

    @QtCore.pyqtSlot()
    def save_non_target_image(self):
        comment('taking non-target picture')
        self.image_title = 'non_target'
        self.requested_frames += 1

    @QtCore.pyqtSlot()
    def save_misc_image(self):
        comment('taking miscellaneous picture')
        self.image_title = 'miscellaneous'
        self.requested_frames += 1

    @QtCore.pyqtSlot()
    def save_lysed_screenshot(self):
        comment('taking lysed picture')
        self.image_title = 'lysed'
        self.requested_frames += 1

    @QtCore.pyqtSlot('PyQt_PyObject')
    def save_qswitch_fire_slot(self, num_frames):
        '''
        takes an initial screenshot of the current frame (before firing)
        and then queues up 4 more pictures to be taken during the firing
        '''
        if self.recording:
            return
        im = Image.fromarray(np.left_shift(self.image, 4))
        logger.info('Taking qswitch fire pictures')
        logger.debug('writing frame %s to disk', self.image_count)
        im.save(os.path.join(experiment_folder_location,
                             'before_qswitch___{}.tif'.format(now())), format="tiff", compression="tiff_lzw")
        self.image_title = 'during_qswitch_fire'
        if self.requested_frames >= 30:
            self.requested_frames = 30
        else:
            self.requested_frames += num_frames


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


def display_fluorescence_properly(img: np.ndarray, preset_data):
    img = np.right_shift(img, 4).astype(np.uint8)
    new_shape = img.shape[:-1] + (3,)
    new_img = np.zeros(new_shape).astype(np.uint8)
    for channel_num in range(preset_data.shape[0]):
        # now map the channels to their respective wavelengths
        channel = preset_data.iloc[channel_num]
        print(f'processing {channel}')
        channel_wv = channel['emission']
        if 'nm' in channel_wv:
            channel_wv = channel_wv[:-2]
        if int(channel_wv) == 0:
            # this is a BF channel
            for i in range(3):
                new_img[:, :, i] = img[:, :, channel_num]
        else:
            # now add proper fluorescence on top
            rgb_val = wl_to_rbg(wl)
            new_overlay = np.zeros(new_shape).astype(np.uint8)
            for j in range(3):
                new_overlay[:, :, j] = rgb_val[j] / 255 * img[:, :, channel_num]
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


preset_loc = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets.yaml')
experiment_name = 'experiment_{}'.format(now())
experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Experiments', experiment_name)