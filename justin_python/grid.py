"""
    Grid Coordinate Generator
    Justin Sutherland
    11/4/2019

    Script for using the spooky library and testing the xyz coordinate system.

    Eventually will integrate this with kmeans script.
"""

import spooky_lib as grid
import prostick_lib as iv
import cv2
import numpy as np
from matplotlib import pyplot as plt
import time


img_horizontal = cv2.imread('grid6_horizontal.jpg', 0)
img_vertical = cv2.imread('grid6_vertical.jpg', 0)
img_horizontal = grid.process_grid(img_horizontal, 0.6)
img_vertical = grid.process_grid(img_vertical, 0.6)

plt.plot
plt.scatter(img_vertical[:, 0], img_vertical[:, 1], c='blue', s=.1, alpha=0.1)
plt.show()

plt.plot
plt.scatter(img_horizontal[:, 0], img_horizontal[:, 1], c='blue', s=.1, alpha=0.1)
plt.show()