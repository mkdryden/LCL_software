import time
from utils import comment, now
from keras.models import load_model
import os
from PyQt5 import QtCore
import cv2
import numpy as np
import tensorflow as tf

global graph
from PyQt5.QtWidgets import QApplication
import pickle
from sklearn.preprocessing import StandardScaler
from keras import backend as K

graph = tf.get_default_graph()
import skimage.transform as transform
import scipy.ndimage as nd
import matplotlib.pyplot as plt

# TODO fix this stupid redundant reference!
experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


def mean_iou(y_true, y_pred):
    prec = []
    for t in np.arange(0.5, 1.0, 0.05):
        y_pred_ = tf.to_int32(y_pred > t)
        score, up_opt = tf.metrics.mean_iou(y_true, y_pred_, 2)
        K.get_session().run(tf.local_variables_initializer())
        with tf.control_dependencies([up_opt]):
            score = tf.identity(score)
        prec.append(score)
    return K.mean(K.stack(prec), axis=0)


class WellStitcher():

    def __init__(self, outward_length, img_channels):
        # get our inital coordinates
        self.box_size = int(outward_length * 2 + 1)
        self.center = outward_length
        self.curr_x = self.center
        self.curr_y = self.center
        # initialize the image
        self.img_x, self.img_y = 4096 // 4, 2160 // 4
        self.well_img = np.zeros((self.img_y * self.box_size, self.img_x * self.box_size, img_channels), dtype=np.uint8)
        # self.stitch_img(initial_img)
        self.current_channel = 0

    def stitch_img(self, img):
        img = cv2.resize(img, (self.img_x, self.img_y))
        self.well_img[self.curr_y * self.img_y:(self.curr_y + 1) * self.img_y,
        self.curr_x * self.img_x:(self.curr_x + 1) * self.img_x, self.current_channel] = img
        self.current_channel += 1

    def add_img(self, let, img):
        if let == 'u': self.curr_y -= 1
        if let == 'd': self.curr_y += 1
        if let == 'l': self.curr_x -= 1
        if let == 'r': self.curr_x += 1
        self.stitch_img(img)

    def write_well_img(self):
        experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'well_images')
        save_loc = os.path.join(experiment_folder_location, '{}___{}.tif'.format('well_image', now()))
        plt.imsave(save_loc, self.well_img, cmap='gray')
        # cv2.imshow('Stitch', cv2.resize(self.well_img, (int(1351), int(711)), interpolation=cv2.INTER_AREA))
        # cv2.imshow('Stitch', self.well_img)
        comment('...well image writing completed')


class Localizer(QtCore.QObject):
    localizer_move_signal = QtCore.pyqtSignal('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
    get_position_signal = QtCore.pyqtSignal()
    fire_qswitch_signal = QtCore.pyqtSignal()
    stop_laser_flash_signal = QtCore.pyqtSignal()
    ai_fire_qswitch_signal = QtCore.pyqtSignal('PyQt_PyObject')
    start_laser_flash_signal = QtCore.pyqtSignal()
    qswitch_screenshot_signal = QtCore.pyqtSignal('PyQt_PyObject')
    localizer_stage_command_signal = QtCore.pyqtSignal('PyQt_PyObject')
    get_number_of_presets_signal = QtCore.pyqtSignal()
    cycle_image_channel_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Localizer, self).__init__(parent)
        self.localizer_model = load_model(os.path.join(experiment_folder_location, 'model2018-12-06_09_18'),
                                          custom_objects={'mean_iou': mean_iou})
        self.norm = StandardScaler()
        self.localizer_model._make_predict_function()
        self.position = np.zeros((1, 2))
        self.well_center = np.zeros((1, 2))
        self.lysed_cell_count = 0
        self.delay_time = .1
        self.cells_to_lyse = 1
        self.cell_type_to_lyse = 'red'
        self.lysis_mode = 'direct'
        self.auto_mode = False
        self.image = None
        self.prev_image = None
        self.frame_count = 0
        self.number_of_presets = None

    # Lines for testing network output
    # im_loc = os.path.join(experiment_folder_location,'test_img.jpeg')
    # self.hallucination_img = cv2.imread(im_loc)
    # img = self.get_network_output(self.hallucination_img)
    # plt.imshow(img)
    # plt.show()

    @QtCore.pyqtSlot('PyQt_PyObject')
    def vid_process_slot(self, image):
        self.image = image
        self.frame_count += 1

    @QtCore.pyqtSlot('PyQt_PyObject')
    def position_return_slot(self, position):
        # we need to get the position from the stage and store it
        self.position = position.copy()
        self.wait_for_position = False

    def stop_auto_mode(self):
        self.auto_mode = False

    def get_stage_position(self):
        self.wait_for_position = True
        self.get_position_signal.emit()
        while self.wait_for_position is True:
            QApplication.processEvents()
            time.sleep(.3)
        return self.position

    def move_frame(self, direction, relative=True):
        y_distance = 340 * 10
        x_distance = 128 * 5 * 10
        frame_dir_dict = {
            'u': np.array([0, -y_distance]),
            'd': np.array([0, y_distance]),
            'l': np.array([-x_distance, 0]),
            'r': np.array([x_distance, 0])
        }
        self.localizer_move_signal.emit(frame_dir_dict[direction], False, True, False)

    def return_to_original_position(self, position):
        self.localizer_move_signal.emit(position, False, False, False)

    def get_spiral_directions(self, outward_length):
        letters = ['u', 'l', 'd', 'r']
        nums = []
        lets = []
        for i in range(1, outward_length * 2, 2):
            num_line = [i] * 2 + [i + 1] * 2
            let_line = letters
            nums += num_line
            lets += let_line
        nums += [nums[-1]]
        lets += lets[-4]
        directions = zip(nums, lets)
        return directions

    def wait_for_new_image(self, initial_frame_number):
        while self.frame_count - initial_frame_number < 15:
            self.delay()
            QApplication.processEvents()
        return

    @QtCore.pyqtSlot('PyQt_PyObject')
    def number_of_presets_slot(self, number):
        self.number_of_presets = number

    def get_image_channels(self):
        # gets the number of checked preset boxes from the gui
        self.get_number_of_presets_signal.emit()
        self.delay()
        return self.number_of_presets

    def cycle_image_channel(self):
        self.cycle_image_channel_signal.emit()

    def gather_all_channel_images(self, stitcher, img_channels):
        for _ in range(img_channels):
            self.wait_for_new_image(self.frame_count)
            stitcher.stitch_img(self.image)
            self.cycle_image_channel()

    @QtCore.pyqtSlot()
    def tile_slot(self):
        # first get our well center position
        self.well_center = self.get_stage_position()
        outward_length = 1
        self.auto_mode = True
        img_channels = self.get_image_channels()
        if img_channels == 0: return
        # acquire our initial images:
        stitcher = WellStitcher(outward_length, img_channels)
        self.gather_all_channel_images(stitcher, img_channels)
        # now start moving a frame at a time and adding them
        directions = self.get_spiral_directions(outward_length)
        self.localizer_stage_command_signal.emit('B X=0.04 Y=0.04')
        for num, let in directions:
            for i in range(num):
                if self.auto_mode is False:
                    return
                self.move_frame(let)
                self.gather_all_channel_images(stitcher, img_channels)
        comment('Tiling completed!')
        stitcher.write_well_img()
        self.return_to_original_position(self.well_center)
        self.localizer_stage_command_signal.emit('B X=0 Y=0')

    def change_type_to_lyse(self, index):
        map_dict = {
            0: ('red', 'model2018-11-27_15_17'),
            1: ('green', 'model2018-11-27_15_17')
        }
        self.cell_type_to_lyse = map_dict[index][0]
        comment('changed cell type to:' + str(self.cell_type_to_lyse))

    def change_lysis_mode(self, index):
        map_dict = {
            0: 'direct',
            1: 'excision'
        }
        self.lysis_mode = map_dict[index]
        comment('changed cell lysis type to:' + str(self.lysis_mode))

    def set_cells_to_lyse(self, number_of_cells):
        self.cells_to_lyse = number_of_cells
        comment('set the number of cells to lyse to:' + str(number_of_cells))

    def delay(self):
        time.sleep(self.delay_time)
        QApplication.processEvents()

    def get_network_output(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = transform.resize(img, (128, 128), anti_aliasing=False)
        img = self.norm.fit_transform(img)
        model_input = np.expand_dims(img, axis=4)
        model_input = np.expand_dims(model_input, axis=0)
        with graph.as_default():
            model_output = self.localizer_model.predict(model_input, batch_size=1)
            model_img = np.squeeze(model_output)
            segmented_image = self.get_voted_output(model_img)
        return_img = np.zeros((128, 128, 3))
        # red cell
        return_img[:, :, 0] = segmented_image[:, :, 0]
        # green cell
        return_img[:, :, 1] = segmented_image[:, :, 1]
        # TODO: fix the resizing issue
        # return_img = transform.resize(return_img, (128, 128, 3), anti_aliasing=False)
        return return_img

    def get_voted_output(self, model_img):
        threshold = 0.2
        mask = model_img[:, :, 0] + model_img[:, :, 1]
        mask = np.where(mask > threshold, np.ones(mask.shape), np.zeros(mask.shape))
        labeled_array, num_features = nd.label(mask)
        fixed_mask = np.zeros(model_img.shape)
        for label_num in range(1, num_features):
            # we want to sum up where the mask overlays items in a single label
            first_label = np.where(labeled_array == label_num, np.ones(labeled_array.shape),
                                   np.zeros(labeled_array.shape))
            red = np.sum(np.where(first_label, model_img[:, :, 0], np.zeros(first_label.shape)))
            green = np.sum(np.where(first_label, model_img[:, :, 1], np.zeros(first_label.shape)))
            # now we know that what the votes are for each object. we need to turn them that color completely
            if green > red:
                fixed_mask[:, :, 1] += np.where(labeled_array == label_num, np.ones(first_label.shape),
                                                np.zeros(first_label.shape))
            elif red > green:
                fixed_mask[:, :, 0] += np.where(labeled_array == label_num, np.ones(first_label.shape),
                                                np.zeros(first_label.shape))
        return fixed_mask

    def check_if_done(self):
        done = False
        if self.auto_mode == False:
            self.stop_laser_flash_signal.emit()
            done = True
        if self.lysed_cell_count >= self.cells_to_lyse:
            self.delay()
            self.return_to_original_position(self.well_center)
            self.stop_laser_flash_signal.emit()
            done = True
        return done

    @QtCore.pyqtSlot()
    def localize(self):
        '''
        function to scan an entire well, and lyse the number of cells desired by the user,
        using the method of lysis that the user selects, then returns to the original
        position (the center of the well)
        '''
        # first get our well center position
        self.lysed_cell_count = 0
        self.auto_mode = True
        self.well_center = self.get_stage_position()
        # now start moving and lysing all in view
        self.lyse_all_in_view()
        box_size = 6
        directions = self.get_spiral_directions(box_size)
        for num, let in directions:
            for i in range(num):
                if self.check_if_done(): return
                self.delay()
                self.move_frame(let)
                self.lyse_all_in_view()
        self.return_to_original_position(self.well_center)
        comment('lysis completed!')

    def lyse_all_in_view(self):
        '''
        gets initial position lyses all cells in view, and then
        returns to initial position
        '''
        self.start_laser_flash_signal.emit()
        view_center = self.get_stage_position()
        print('lysing all in view...')
        self.delay()
        segmented_image = self.get_network_output(self.image)
        # segmented_image = self.get_network_output(self.hallucination_img)
        cv2.imshow('Cell Outlines and Centers', segmented_image)
        # lyse all cells in view
        self.lyse_cells(segmented_image, self.cell_type_to_lyse, self.lysis_mode)
        if self.check_if_done(): return
        # now return to our original position
        self.delay()
        self.return_to_original_position(view_center)
        self.stop_laser_flash_signal.emit()

    def lyse_cells(self, segmented_image, cell_type, lyse_type):
        '''
        takes the image from the net, and determines what targets to lyse
        based upon the input parameters. also lyses in different ways based
        upon the input parameters
        '''
        type_image = self.select_type(segmented_image, cell_type)
        cell_contours, cell_centers = self.get_contours_and_centers(type_image)
        if len(cell_centers) == 0:
            print('NO CELLS FOUND')
            return
        if lyse_type == 'direct':
            self.direct_lysis(cell_centers)
        elif lyse_type == 'excision':
            self.excision_lysis(cell_contours)

    def select_type(self, segmented_image, cell_type):
        if cell_type == 'green':
            return segmented_image[:, :, 1]
        elif cell_type == 'red':
            return segmented_image[:, :, 0]

    def get_contours_and_centers(self, confidence_image):
        _, contours, _ = cv2.findContours(np.uint8(confidence_image), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cell_image = np.zeros((128, 128))
        cell_contours = []
        cell_centers = []
        for contour in contours:
            # print(cv2.contourArea(contour))
            if cv2.contourArea(contour) > 40:
                cell_contours.append(contour)
                center = self.get_contour_center(contour)
                cell_centers.append(center)
        cv2.drawContours(cell_image, contours, -1, (255, 255, 255), 1)
        for center in cell_centers:
            cv2.circle(cell_image, center, 2, 255, thickness=-1)
        cv2.imshow('Cell Outlines and Centers', cell_image)
        return cell_contours, cell_centers

    def get_contour_center(self, contour):
        M = cv2.moments(contour)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        return (int(cX), int(cY))

    def direct_lysis(self, cell_centers):
        if len(cell_centers) == 0: return
        window_center = np.array([128. / 2, 128. / 2])
        # print('centers:',cell_centers)
        old_center = cell_centers[0]
        self.qswitch_screenshot_signal.emit(10)
        self.move_to_target(old_center - window_center, True)
        self.delay()
        for i in range(3):
            self.ai_fire_qswitch_signal.emit(False)
            time.sleep(.15)
        self.lysed_cell_count += 1
        if self.check_if_done(): return
        if len(cell_centers) < 2: return
        for i in range(1, len(cell_centers)):
            self.qswitch_screenshot_signal.emit(15)
            self.move_to_target(-np.array(old_center) + cell_centers[i], False)
            old_center = cell_centers[i]
            self.delay()
            for i in range(3):
                self.ai_fire_qswitch_signal.emit(False)
                self.delay()
            self.delay()
            self.lysed_cell_count += 1
            if self.check_if_done(): return

    def excision_lysis(self, cell_contours):
        if len(cell_contours) == 0: return
        # for each contour we want to trace it
        window_center = np.array([128. / 2, 128. / 2])
        for i in range(len(cell_contours)):
            contour = cell_contours[i]
            num_contour_points = contour.shape[0]
            # this block is responsible for vectoring from one contour start to another
            if i == 0:
                # need to move to the reticle on the first cell only
                contour_start = contour[0].reshape(2)
                self.move_to_target(contour_start - window_center, True)
                old_center = np.copy(contour_start)
            else:
                # return_vec =  np.sum((cell_contours[i-1].reshape(-1,2)),axis = 1)
                new_center = contour[0].reshape(2)
                self.move_to_target(-return_vec.reshape(2) - contour_start + new_center, False)
                old_center = new_center
                contour_start = np.copy(new_center)
            # now turn on the autofire
            time.sleep(.05)
            self.qswitch_screenshot_signal.emit(2)
            self.ai_fire_qswitch_signal.emit(True)
            time.sleep(.05)
            # this block is responsible for vectoring around the contour
            return_vec = np.zeros((2))
            for j in range(1, num_contour_points, 5):
                new_center = contour[j].reshape(2)
                move_vec = -old_center + new_center
                scaled_move_vec = move_vec * 2
                return_vec = np.add(return_vec, scaled_move_vec)
                # print(return_vec,return_vec.shape, scaled_move_vec.shape)
                self.qswitch_screenshot_signal.emit(1)
                self.move_to_target(scaled_move_vec, False)
                old_center = new_center
                time.sleep(.05)
            self.lysed_cell_count += 1
            self.qswitch_screenshot_signal.emit(5)
            self.ai_fire_qswitch_signal.emit(False)
            self.delay()
            if self.check_if_done(): return

    def move_to_target(self, center, goto_reticle=False):
        # we need to scale our centers up to the proper resolution and then
        # send it to the stage
        x = center[0] * 851 / 128
        y = center[1] * 681 / 128
        self.localizer_move_signal.emit(np.array([x, y]), goto_reticle, True, True)
