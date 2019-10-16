"""
This is a simple script that compares the effectiveness of Histogram Equalization
and Contrast Limited Adaptive Histogram Equalization (CLAHE) in enhancing veins
for the ProStick.

This script requires opencv-python, numpy, and matplotlib to run.
"""

import cv2
import numpy as np
from matplotlib import pyplot as plt


# Import the original image
img = cv2.imread('jp1_8.jpg', 0)
img = cv2.medianBlur(img, 5)

# Create the histogram for the original image
hist_orig, bins_orig = np.histogram(img.flatten(), 256, [0, 256])

# Perform histogram equalization on the original image and create the
# histogram for the new image
equ = cv2.equalizeHist(img)
hist_he, bins_he = np.histogram(equ.flatten(), 256, [0, 256])

# Perform CLAHE on the original image and create the histogram for the new image
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
clahe_img = clahe.apply(img)
hist_clahe, bins_clahe = np.histogram(clahe_img.flatten(), 256, [0, 256])

plt.ion()

# Plot each version of the image and its histogram for comparison
fig, axs = plt.subplots(3, 2)
axs[0, 0].imshow(img, 'gray')
axs[0, 0].set_title('Original Image')
axs[0, 1].hist(img.flatten(), 256, [0, 256], color='r')
axs[0, 1].set_title('Original Image Histogram')
axs[1, 0].imshow(equ, 'gray')
axs[1, 0].set_title('Histogram Equalized Image')
axs[1, 1].hist(equ.flatten(), 256, [0, 256], color='r')
axs[1, 1].set_title('Histogram for the Histogram Equalized Image')
axs[2, 0].imshow(clahe_img, 'gray')
axs[2, 0].set_title('CLAHE Image')
axs[2, 1].hist(clahe_img.flatten(), 256, [0, 256], color='r')
axs[2, 1].set_title('Histogram for the CLAHE Image')

plt.show()
plt.clf()
