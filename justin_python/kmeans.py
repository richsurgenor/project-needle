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
from pyclustering.cluster.kmedians import kmedians
from pyclustering.cluster.center_initializer import kmeans_plusplus_initializer
import cv2
import numpy as np
from matplotlib import pyplot as plt
import time
from sklearn.cluster import KMeans
import spooky_lib as grid

if __name__ == "__main__":
    # Read in the image
    grid_horizontal, grid_vertical = iv.initialize_grids('coord_static_x.png', 'coord_static_y.png')
    time_enable = 1
    start = time.time()
    img_in = cv2.imread('justin1.jpg', 0)

    clahe_img = iv.apply_clahe(img_in, 5.0, (8, 8))
    mask = iv.create_mask(img_in, 100, 255)
    threshold = int(255 * 0.5)
    adapt_mean_th = iv.adapt_thresh(clahe_img, 255, threshold, 20)
    preprocessed_img = iv.apply_mask(adapt_mean_th, mask)

    pic_array_1, pic_array_2 = iv.process_image(preprocessed_img, 0.5, time_enable)
    nclusters = 50  # make sure this is always divisible by 2
    centers_first = iv.execute_kmean(pic_array_1, int(nclusters/2))
    centers_second = iv.execute_kmean(pic_array_2, int(nclusters/2))
    centers = np.concatenate((centers_first, centers_second), axis=0)
    final_selection = iv.final_selection(centers)
    end = time.time()
    if time_enable:
        print("Time to make selection: ", (end - start), "s")
    # Plot all steps of the vein enhancement process
    plt.plot
    plt.imshow(img_in, 'gray')
    plt.scatter(centers[:, 0], centers[:, 1], c='blue', s=10, alpha=0.5)
    plt.scatter(final_selection[0], final_selection[1], c='red', s=10, alpha=0.5)
    plt.show()
    plt.clf()

    # Now let's test the grid system and see if we can get a x mm and y mm command!
    # Get the x y slices from the grids
    xslice = grid_vertical[int(final_selection[0]), :]
    yslice = grid_horizontal[:, int(final_selection[1])]
    [xcount, ycount] = grid.count_bumps(final_selection, xslice, yslice)
    print(final_selection)
    print(str(5*xcount) + ' mm horizontal')
    print(str(5*ycount) + ' mm vertical')