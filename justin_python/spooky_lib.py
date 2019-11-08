"""
    "Spooky" Library for the XYZ plane logic
    Justin Sutherland, 11/2/2019

    Contains the logic for navigating the xyz planes using a reference
    grid image. The overall logic for the xyz plane is described in
    detail in the functions contained here.

"""

import prostick_lib as iv
import cv2
import numpy as np


def oh_no():
    return "Spooky"


def process_grid(img_in, threshold):
    """
    :param img_in: image taken by the Raspberry Pi camera
    :param threshold: 0 to 1 analog value, selected threshold for the adaptive thresholding step; this function will be
            used in the grid system, needle check, and main algorithm sections.
    :return: the processed image

    This is an altered version of the main image processsing algorithm adapted for use with
    the grid image. Algorithm Process is as follows:
    1) Apply the CLAHE
    3) Apply adaptive mean thresholding
    4) Apply a median blurring operation to remove noise. Tried several methods, and this worked the best.
        NOTE: Leave the Bilateral Filter option commented out just in case that is needed at some point
    5) Return as an image array. We want to get column vectors and row vectors from it so we need to keep it in
        that format.
    """
    clahe_img = iv.apply_clahe(img_in, 5.0, (8, 8))
    threshold = int(255*threshold)
    adapt_mean_th = iv.adapt_thresh(clahe_img, 255, threshold, 20)
    pic_array = cv2.medianBlur(adapt_mean_th, 7)
    return np.array(pic_array)


def white_out_grid(pic_array):
    """
    :param grid_points: processed image
    :return: grid_points with extreme outliers removed (the rails on the gantry specifically)

    This algorithm does not have to be fast because we can just run it when we start up the GUI. Therefore, I am just
    going to iterate point by point.
    """
    new = []
    for each in pic_array:
        if 150 < each[0] < 2800 and 400 < each[1] < 2500:
            new.append(each)

    return new


def count_bumps(xy, xslice, yslice):
    """
    :param xy: tuple representing the chosen injection site
    :param xslice: slice of x coordinates (so this would be the longitude equivalent)
    :param yslice: slice of y coordinates (so this would be the latitude equivalent)
    :return: tuple containing the number of "bumps" (grid lines) passed for each direction
    """
    xcount = 0
    ycount = 0
    # Luckily, the x and y positions actually tell us exactly how far we have to go
    # Truncate these arrays at the x y coordinate for this reason
    grid_valid = 0
    xslice = xslice[0:int(xy[0])]
    yslice = yslice[0:int(xy[1])]
    for each in xslice:
        if each < 100 and ~(grid_valid):
            grid_valid = 1
        if each > 100 and grid_valid:
            xcount = xcount + 1
            grid_valid = 0
    grid_valid = 0
    for each in yslice:
        if each < 100 and ~(grid_valid):
            grid_valid = 1
        if each > 100 and grid_valid:
            ycount = ycount + 1
            grid_valid = 0

    return xcount, ycount


def grid_interpolation(selection, vertical, horizontal):
    """
    :param selection: selection site
    :param vertical:
    :param horizontal:
    :return:
    """





