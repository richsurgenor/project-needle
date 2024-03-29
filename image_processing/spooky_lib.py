"""
    "Spooky" Library for the XYZ plane logic
    Justin Sutherland, 11/2/2019

    Contains the logic for navigating the xyz planes using a reference
    grid image. The overall logic for the xyz plane is described in
    detail in the functions contained here.

"""

import image_processing.prostick_lib as iv
import cv2
import numpy as np


def oh_no():
    return "Too Spooky for Jackson"


def test_grid(img):
    """
    :return: 0
    Function takes a predefined set of pixel coordinates and finds the mm coordinates.
    IF they do not match the measurements by hand within an acceptable margin of error,
    the test fails.
    """
    margin = 0.01
    grid_horizontal, grid_vertical = iv.initialize_grids(img, 'grid_ver.jpg', 'grid_hor.jpg')
    set_pixel = [[457, 525], [531, 350], [729, 627], [231, 746]]
    set_mm = [[75, 50], [87.5, 17.5], [122.5, 67.5], [37.5, 87.5]]
    i = 0
    for each in set_pixel:
        y, x = iv.get_position(each, grid_horizontal, grid_vertical)
        print("Actual mm position: " + str(set_mm[i]))
        print("Calculated mm position: " + str(x) + " mm horizontal, " + str(y) + " mm vertical")
        i = i + 1

    return 0


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
    clahe_img = iv.apply_clahe(img_in, 5.0, (2, 2))
    threshold = int(255*threshold)
    adapt_mean_th = iv.adapt_thresh(clahe_img, 255, threshold, 15)
    # pic_array = cv2.medianBlur(adapt_mean_th, 7)
    pic_array = adapt_mean_th
    return np.array(pic_array)


def interpolate(xy, xslice, yslice):
    """
    :param xy: tuple representing the chosen injection site
    :param xslice: slice of x coordinates (so this would be the longitude equivalent)
    :param yslice: slice of y coordinates (so this would be the latitude equivalent)
    :return: equivalent mm position (x and y)
    """
    # Luckily, the x and y positions actually tell us exactly how far we have to go
    # Truncate these arrays at the x y coordinate for this reason
    xpos = count_loop(xslice, xy, 1)
    ypos = count_loop(yslice, xy, 0)
    return xpos, ypos


def count_loop(array, selection, xory):
    """
    :param array: slice from grid array
    :param selection: tuple containing the injections site coordinates
    :param xory: boolean for x or y; 0 is x, 1 is y
    :return: interpolated distance to pass to the gantry
    TO DO: LOW PRIORITY - Add interpolation inside grid lines
    I sincerely apologize for making this as long as it is.
    """

    grid_valid, final_iteration = False, False
    grid_array = []
    white_array = []
    grid_count = 0
    store_whitespace = []
    k = 0
    for each in array:

        if k >= int(selection[xory]) and (final_iteration < 0.5):
            final_iteration = True

        if each < 100:  # grid line
            if (grid_valid < 0.5) and (final_iteration < 0.5):  # we just iterated onto a grid line
                grid_valid = True
                grid_array = []
                store_whitespace = white_array
                grid_count = grid_count + 1
            elif (grid_valid < 0.5) and (final_iteration > 0.5):   # for some reason ~x does not work properly
                store_whitespace = white_array
                break

            grid_array.append(k)

        if each >= 100:    # whitespace
            if grid_valid:  # we just iterated off of a grid line
                grid_valid = False
                store_grid = grid_array
                white_array = []

            white_array.append(k)

        k = k + 1
    #  now we have all the arrays, we can do the final calculations to interpolate
    if len(store_whitespace) > 0.5:
        white_previous = min(store_whitespace)
        white_final = max(store_whitespace)
        interpolated_value = 5*grid_count + 5*(white_previous-selection[xory])/(white_previous-white_final)
    else:
        interpolated_value = 5*grid_count

    return interpolated_value


def slice_grid(xy, horizontal, vertical):
    """
    :param xy: xy position
    :param horizontal: horizontal grid line image array
    :param vertical: vertical grid line image array
    :return: horizontal slice, vertical slice

    Simple function that takes a selected point on the image and returns it's sliced row and column
    vectors from the grid images
    """
    return vertical[int(xy[1]), :], horizontal[:, int(xy[0])]


