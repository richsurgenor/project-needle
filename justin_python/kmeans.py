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
import cv2
import numpy as np
from matplotlib import pyplot as plt
import time
from sklearn.cluster import KMeans

if __name__ == "__main__":
    # Read in the image
    time_enable = 1
    img_in = cv2.imread('grid6.jpg', 0)
    pic_array_np = iv.process_image(img_in, 0.5, time_enable)
    # Run the K-Means algorithm to get 50 centers
    start = time.time()
    kmeans = KMeans(n_clusters=40)
    kmeans.fit(pic_array_np)
    y_kmeans = kmeans.predict(pic_array_np)
    centers = kmeans.cluster_centers_
    end = time.time()
    if time_enable:
        print("Time to create Kmean set: ", (end - start), "s")
    # Now take the array "centers" and do a final selection using that dataset
    start = time.time()
    final_selection = iv.final_selection(centers)
    end = time.time()
    if time_enable:
        print("Time to choose final selection: ", (end - start), "s")
    # Plot all steps of the vein enhancement process
    plt.plot
    plt.imshow(img_in, 'gray')
    plt.scatter(centers[:, 0], centers[:, 1], c='blue', s=10, alpha=0.5)
    plt.scatter(final_selection[0], final_selection[1], c='red', s=10, alpha=0.5)
    plt.show()
    plt.clf()