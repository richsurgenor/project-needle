""" ProStick Vein Enhancement Script
​
This script enhances the veins on a person's arm that has been illuminated
with near-infrared light using Contrast Limited Adaptive Histogram
Equalization (CLAHE), global thresholding, andd adaptive thresholding.
​
This script requires that opencv-python, numpy, maplotlib, time and argparse
be installed within the Python environment this script is run in.
"""

import prostick_lib as iv
import cv2
import numpy as np
import time
import visual
from matplotlib import pyplot as plt


if __name__ == "__main__":
    # Read in the image
    grid_horizontal, grid_vertical = iv.initialize_grids('coord_static_x_revised.png', 'coord_static_y.png')
    img_in = cv2.imread('justin4.jpg', 0)
    start = time.time()
    selection, clusters = iv.selection(img_in, 40, grid_vertical)
    # Plot all steps of the vein enhancement process
    end = time.time()
    print(end-start)
    visual.plot_clusters(img_in, clusters, selection)
    # Now let's test the grid system and see if we can get a x mm and y mm command!
    # Get the x y slices from the grids
    inject_x, inject_y = iv.get_position(selection, grid_horizontal, grid_vertical)
    needle_xy_pixel = iv.isolate_needle(img_in, grid_vertical)
    visual.plot_needle(img_in, needle_xy_pixel)
    # Now let's test the comparison tool using the grid functionality
    correction = iv.compare_points(selection, needle_xy_pixel, grid_horizontal, grid_vertical)
    print("Go " + str(correction[0]) + " mm away from the current needle horizontal location.")
    print("Go " + str(correction[1]) + " mm down from the current needle vertical location.")