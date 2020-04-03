import os.path
import re
import argparse
from typing import Union, Tuple, Dict, Any, List
from collections import namedtuple
from itertools import combinations
import logging
from multiprocessing import Pool

import numpy as np
from nptyping import Array
import pandas as pd
from scipy.optimize import minimize
from skimage import filters, morphology
import skimage.io
from skimage.feature import register_translation
from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)

Coords = namedtuple('Coords', ['x', 'y'])


class NotAdjacentError(Exception):
    """
    Exception raised when a ShiftPair is instantiated with two non-adjacent images.

    Attributes:
        im0 -- Coordinates of first image
        im1 -- Coordinates of second image
        message -- explanation of the error
    """

    def __init__(self, im0: Array[int, 2, 0], im1: Array[int, 2, 0]):
        self.im0 = im0
        self.im1 = im1
        self.message = f"Cannot align non-adjacent images with coordinates {im0} and {im1}"


def im_error(positions: Array[float, ..., 0],
             x_shift: Array[float],
             y_shift: Array[float],
             error: Array[float]) -> float:
    """
    Loss function to optimize image displacements for given pairwise shifts.
    :param positions: 1D array of positions interleaved in x y order
    :param x_shift: 2D images x images array of pairwise x shifts
    :param y_shift: 2D images x images array of pairwise y shifts
    :param error: alignment error
    :return: rms difference weighted by error
    """
    x_positions = positions[::2]
    y_positions = positions[1::2]

    xpos_diff = x_positions[:, np.newaxis] - x_positions
    ypos_diff = y_positions[:, np.newaxis] - y_positions

    mask_count = (error > 0).sum()
    x_err = xpos_diff - x_shift
    y_err = ypos_diff - y_shift

    x_err *= error
    y_err *= error
    x_err **= 2
    y_err **= 2

    x_av = x_err.sum() / mask_count
    y_av = y_err.sum() / mask_count

    return np.sqrt((x_av + y_av) / 2)


class ShiftPair(object):
    def __init__(self, im0: Array[int], im1: Array[int],
                 im0_coords: Array[int, 2, 0], im1_coords: Array[int, 2, 0],
                 overlap: float):
        """
        Create pair of images for shift alignment
        :param im0: first image as numpy array
        :param im1: second image as numpy array
        :param im0_coords: coordinates of first image in tile space (x, y)
        :param im1_coords: coordinates of second image in tile space (x, y)
        :param overlap: fraction of image overlap
        """
        self.im0 = im0
        self.im1 = im1
        self.im0_coords = im0_coords
        self.im1_coords = im1_coords
        self.overlap = overlap

        # Make sure images are adjacent
        self.diff = self.im1_coords - self.im0_coords
        self.diff_x, self.diff_y = self.diff
        if np.linalg.norm(self.diff) != 1:
            raise NotAdjacentError(im0_coords, im1_coords)

        # Calculated
        self.registered = False
        self.shift = np.zeros(2)
        self.error = 0.
        self.phase = 0.

    def register(self, sobel: bool = True, median: int = 3) -> Tuple[Array[float, 2, 0], float, float]:
        """
        Register image pair. Saves results as attributes.
        :param sobel: if True, uses sobel edge detection
        :param median: if > 0, filter image with circular median with given radius
        """
        im0 = self.im0
        im1 = self.im1

        x_overlap = int(im0.shape[1] * self.overlap)
        y_overlap = int(im0.shape[0] * self.overlap)

        im0_x_slice = 0, im0.shape[1]
        im1_x_slice = 0, im1.shape[1]
        im0_y_slice = 0, im0.shape[0]
        im1_y_slice = 0, im1.shape[0]

        if self.diff_x == 1:
            im1_x_slice = 0, x_overlap
            im0_x_slice = im0.shape[1] - x_overlap, im0.shape[1]
        elif self.diff_x == -1:
            im0_x_slice = 0, x_overlap
            im1_x_slice = im0.shape[1] - x_overlap, im0.shape[1]
        if self.diff_y == 1:
            im1_y_slice = 0, y_overlap
            im0_y_slice = im0.shape[0] - y_overlap, im0.shape[0]
        elif self.diff_y == -1:
            im0_y_slice = 0, y_overlap
            im1_y_slice = im0.shape[0] - y_overlap, im0.shape[0]

        im0 = im0[np.s_[im0_y_slice[0]:im0_y_slice[1]],
                  np.s_[im0_x_slice[0]:im0_x_slice[1]]]
        im1 = im1[np.s_[im1_y_slice[0]:im1_y_slice[1]],
                  np.s_[im1_x_slice[0]:im1_x_slice[1]]]

        if median > 0:
            im0 = filters.median(im0, morphology.disk(median))
            im1 = filters.median(im1, morphology.disk(median))

        if sobel:
            im0 = filters.sobel(im0)
            im1 = filters.sobel(im1)

        self.shift, self.error, self.phase = register_translation(im0, im1)

        self.registered = True
        return self.shift, self.error, self.phase

    @property
    def angle(self) -> Union[None, float]:
        if not self.registered:
            logger.warning("Tried to get angle without registering first")
            return None

        if self.diff[0] != 0:  # x angle is inverted in normal order
            return -np.arcsin(self.shift[0] / (self.im0.shape[1] * (1 - self.overlap)))
        elif self.diff[1] != 0:
            return np.arcsin(self.shift[1] / (self.im0.shape[0] * (1 - self.overlap)))


class ShiftMatrix(object):
    """
    Stores a collection of ShiftPair objects and operates on them.
    Gets im_shape and overlap from first image in first object and does not check if the whole list is consistent.
    """

    def __init__(self, columns: int, rows: int, images: skimage.io.ImageCollection,
                 coords: Array[int, ..., 2], overlap: float):
        """
        :param columns: columns in tile
        :param rows: rows in tile
        :param images: ImageCollection, in column order from top-left
        :param coords: List of coordinates of images
        :param overlap: overlap fraction between images
        """
        self.columns = columns
        self.rows = rows
        self.images = images
        self.coords = coords
        self.overlap = overlap
        self.shiftpairs = []

        for i, j in list(combinations(range(len(images)), 2)):
            try:
                self.shiftpairs.append(ShiftPair(images[i], images[j],
                                                 coords[i], coords[j],
                                                 overlap=overlap))
            except NotAdjacentError:
                self.shiftpairs.append(None)

        self.registered = False
        self.angle = 0.
        self.im_shape = images[0].shape

        x_grid = [((x - (columns - 1) / 2.) * (1 - self.overlap)) - .5 for x in range(columns)]
        y_grid = [((y - (rows - 1) / 2.) * (1 - self.overlap)) - .5 for y in range(rows)]

        x_matrix, y_matrix = np.meshgrid(x_grid, y_grid, indexing='ij')

        self.x_pos_pix = (x_matrix * self.im_shape[1]).astype(int).T
        self.y_pos_pix = (y_matrix * self.im_shape[0]).astype(int).T
        self.x_pos_pix_shifted = (x_matrix * self.im_shape[1]).astype(int).T
        self.y_pos_pix_shifted = (y_matrix * self.im_shape[0]).astype(int).T

    def register(self, parallel: bool = True):
        """
        Registers all ShiftPairs
        :param parallel: if True, executes in parallel with multiprocessing.Pool
        """
        shiftpairs = [pair for pair in self.shiftpairs if pair is not None]
        shiftindex = [n for n, pair in enumerate(self.shiftpairs) if pair is not None]
        if parallel:
            with Pool() as p:
                result = p.map(ShiftPair.register, shiftpairs)
            for n, i in enumerate(result):
                pair = self.shiftpairs[shiftindex[n]]
                pair.shift, pair.error, pair.phase = i
                pair.registered = True
        else:
            for shiftpair in self.shiftpairs:
                try:
                    shiftpair.register()
                except AttributeError:
                    pass
        self.registered = True

    def estimate_camera_angle(self):
        """
        Calculates and saves error-weighted average of camera angles as attribute
        """
        if not self.registered:
            logger.error("ShiftPairs not registered")
            return

        df = pd.DataFrame({'theta': [i.angle for i in self.shiftpairs if i is not None],
                           'error': [i.error for i in self.shiftpairs if i is not None]})

        self.angle = (df.theta * ((1 / df.error) / (1 / df.error).sum())).sum()

    def fit_positions(self, max_shift: int = 350):
        """
        Fit image positions to residual shifts after camera angle correction.
        :param max_shift: constraint on max shift in pixels
        """
        if not self.registered:
            logger.error("ShiftPairs not registered")
            return

        # Generate matrices
        pair_matrix_shape = (len(self.images), len(self.images))
        x_shift_pairs = np.zeros(shape=pair_matrix_shape)
        y_shift_pairs = np.zeros(shape=pair_matrix_shape)
        mask_pairs = np.ndarray(shape=pair_matrix_shape, dtype=bool)
        error_shift_matrix = np.zeros(shape=pair_matrix_shape)
        index_combs = list(combinations(range(len(self.images)), 2))

        # Populate matrices
        for n, i in enumerate(self.shiftpairs):
            try:
                x_shift_pairs[index_combs[n]] = i.shift[1] - (
                        np.sin(self.angle) * (self.im_shape[0] * (1 - self.overlap)) * i.diff_y)
                y_shift_pairs[index_combs[n]] = i.shift[0] + (
                        np.sin(self.angle) * (self.im_shape[1] * (1 - self.overlap)) * i.diff_x)
                error_shift_matrix[index_combs[n]] = i.error
                mask_pairs[index_combs[n]] = True
            except (TypeError, AttributeError):
                continue

        results = minimize(im_error,
                           x0=np.zeros(2 * len(self.images)),
                           args=(x_shift_pairs, y_shift_pairs, error_shift_matrix),
                           bounds=[(0, 0)] * 2 +  # Fix one corner to 0, 0
                                  [(-max_shift, max_shift)] * (len(self.images) - 1) * 2)

        positions = np.round(results.x).astype(int)
        self.x_pos_pix_shifted = self.x_pos_pix - positions[::2].reshape((self.columns, self.rows)).T
        self.y_pos_pix_shifted = self.y_pos_pix - positions[1::2].reshape((self.columns, self.rows)).T

    def assemble_angled(self, full_depth: bool = True) -> Array[int]:
        """
        Assemble mosaic of images using fitted shifts.
        :param full_depth: If True, outputs 16-bit image.
        :return: assembled mosaic
        """
        out_s = self.im_shape * np.array(self.x_pos_pix_shifted.shape) / (1 + self.overlap / 2)
        out_s = out_s.astype(int).tolist()

        if full_depth:
            canvas = np.zeros(out_s, dtype=np.uint16)
        else:
            canvas = np.zeros(out_s, dtype=np.uint8)

        x_corners = self.x_pos_pix_shifted.astype(np.float64)
        x_corners += (np.sin(self.angle) * self.y_pos_pix)
        x_corners += out_s[1] / 2
        y_corners = self.y_pos_pix_shifted.astype(np.float64)
        y_corners -= (np.sin(self.angle) * self.x_pos_pix)
        y_corners += out_s[0] / 2

        for n, im in enumerate(self.images):
            x, y = self.coords[n]
            top = int(np.round(y_corners.T.flat[n]))
            left = int(np.round(x_corners.T.flat[n]))

            if full_depth:
                image = im
            else:
                image = np.right_shift(im, 8).astype(np.uint8)
            mask = np.ones(self.im_shape, dtype=float)
            if x > 0:  # left edge
                overlap_width = int(im.shape[1] * self.overlap / 2)
                mask[:, 0:overlap_width] = np.broadcast_to(
                    np.linspace(0., 1., overlap_width), (im.shape[0], overlap_width))

            if y > 0:  # Top edge
                overlap_height = int(im.shape[0] * self.overlap / 2)
                mask[0:overlap_height, :] = np.broadcast_to(
                    np.linspace(0., 1., overlap_height), (im.shape[1], overlap_height)).T

            canvas[top:top + im.shape[0],
            left:left + im.shape[1]] = np.round(image * mask +
                                                canvas[top:top + im.shape[0], left:left + im.shape[1]] *
                                                (1. - mask)).astype(np.uint16)

        return Image.fromarray(canvas)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process individual tile images into a mosiaic.")
    parser.add_argument('path', help='Path to folder containing images (all .tif files will be processed)')
    parser.add_argument('-o', '--output', help='Output path', default='./output')
    parser.add_argument('--overlap', help='fractional overlap between images', default=.25, type=float)
    args = parser.parse_args()

    images = skimage.io.ImageCollection(os.path.join(os.path.realpath(args.path), "*.tif"))
    xy_regex = re.compile(r"(?P<prefix>.*_[\d]{2}_[\d]{2}_[\d]{4}___[\d]{2}\.[\d]{2}\.[\d]{2})-"
                          r"(?P<x>[\d]+)_(?P<y>[\d]+)-.*\.tif")

    matches = [re.match(xy_regex, i) for i in images.files]
    image_coords = np.array([(int(match.group('x')), int(match.group('y'))) for match in matches])
    y_max, x_max = np.sort(image_coords)[-1]

    matrix = ShiftMatrix(columns=x_max + 1, rows=y_max + 1,
                         images=images,
                         coords=image_coords,
                         overlap=args.overlap)

    matrix.register()
    matrix.estimate_camera_angle()
    matrix.fit_positions()
    tiled = matrix.assemble_angled()

    os.makedirs(os.path.realpath(args.output), exist_ok=True)
    Image.fromarray(tiled).save(os.path.join(os.path.realpath(args.output),
                                             os.path.split(f"{matches[0].group('prefix')}-stitched.tif")[-1]))
