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


def count_and_interpolate(xy, xslice, yslice):
    """
    :param xy: tuple representing the chosen injection site
    :param xslice: slice of x coordinates (so this would be the longitude equivalent)
    :param yslice: slice of y coordinates (so this would be the latitude equivalent)
    :return: equivalent mm position (x and y)
    """
    # Luckily, the x and y positions actually tell us exactly how far we have to go
    # Truncate these arrays at the x y coordinate for this reason
    xslice = xslice[0:int(xy[0])]
    yslice = yslice[0:int(xy[1])]
    xcount, xpixel = count_loop(xslice, xy, 1)
    ycount, ypixel = count_loop(yslice, xy, 0)
    print(xpixel)
    print(ypixel)
    return 5*xcount, 5*ycount


def count_loop(array, selection, xory):
    '''
    :param array: slice from grid array
    :param selection: tuple containing the injections site coordinates
    :param xory: boolean for x or y; 0 is x, 1 is y
    :return: grid line count and interpolated distance to next grid line in sequence

    This algorithm is actually harder to pull off than I thought it would be. We have
    to set several different flags throughout the loops so we can properly siphon off
    the data we need to interpolate. Key thing to note here that we want to define the grid lines
    at the center of the dark lines (so if we have 000001111X111100000, the 1s are the black grid
    lines and the X will be what we referenced. Stuff like this makes this algorithm a little
    more tedious than I would like, but we need to do it this way (from what I know of now)
    '''
    # slice = array[0:int(selection[xory])]
    slice = array
    grid_valid = False
    count_enable_grid = False
    count_enable_space = False
    pixel_grid = 0
    grid_count = 0
    final_grid_count = 0
    end_flag = False
    final_flag = False
    k = 0
    for each in slice:
        if each < 100 and ~(grid_valid):  # we just set foot on a grid line
            if ~final_flag:
                grid_valid = True
                count_enable_grid, count_enable_space = True, False
                pixel_space = 0
                pixel_grid_array = []
            else:
                break
        if each > 100 and grid_valid:    # we just went off a grid line
            grid_count = grid_count + 1
            grid_valid = False
            count_enable_space, count_enable_grid = True, False
            pixel_grid = 0
            grid_average = np.sum(pixel_grid_array)/len(pixel_grid_array)
        if count_enable_grid:  # fulfilled requirement #1
            pixel_grid = pixel_grid + 1  # we need to do this to figure out the interpolation
            pixel_grid_array.append(k)  # fulfilled requirement #2
        if count_enable_space:
            pixel_space = pixel_space + 1
        if k == int(selection[xory]):
            final_grid_count = grid_count
            gridline_distance = k - grid_average  # we define this as the distance from the last grid line
            # we want to keep going after this so we can find the next grid line so we can interpolate
            final_flag = True

        k = k + 1

    return final_grid_count, pixel_space


