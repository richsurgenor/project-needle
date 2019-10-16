""" ProStick Vein Enhancement Script

This script enhances the veins on a person's arm that has been illuminated
with near-infrared light using Contrast Limited Adaptive Histogram
Equalization (CLAHE), global thresholding, and adaptive thresholding.

This script requires that opencv-python, numpy, maplotlib, time and argparse
be installed within the Python environment this script is run in.
"""

import argparse
import cv2
import numpy as np
from matplotlib import pyplot as plt
import time


def apply_clahe(img, clip_lim, grid_size):
    """
    Apply Contrast Limiting Adaptive Histogram Equalization to an image.
    :param img: An image represented by a NumPy array
    :param clip_lim: The value at which the histogram is clipped
    :param grid_size: The area of pixels to examine as a tuple (X, Y)
    :return: The image with CLAHE applied
    """
    img = cv2.medianBlur(img, 5)
    clahe = cv2.createCLAHE(clipLimit=clip_lim, tileGridSize=grid_size)
    result_img = clahe.apply(img)
    return result_img


def create_mask(img, thresh, max_val):
    """
    Create a binary mask for an image using global thresholding.
    :param img: An image represented by a NumPy array
    :param thresh: The threshold value to use on the image
    :param max_val: The maximum pixel value
    :return: The binary mask represented by a NumPy array
    """
    _, mask_ret = cv2.threshold(img, thresh, max_val, cv2.THRESH_BINARY)
    return mask_ret


# Apply adaptive thresholding to the image
def adapt_thresh(img, max_val, block_sz, c):
    """
    Apply Adaptive Mean Thresholding to an image.
    :param img: An image represented by a NumPy array
    :param max_val: The maximum pixel value
    :param block_sz: The area of pixels to calculate each threshold for
    :param c: Constant that is subtracted from the mean of the block size
    :return: The image with Adaptive Mean Thresholding applied
    """
    result_img = cv2.adaptiveThreshold(img, max_val, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, block_sz, c)
    return result_img


def apply_mask(img, mask_in):
    """
    Apply a binary mask to an image
    :param img: An image represented by a NumPy array
    :param mask_in: A binary mask represented by a NumPy array
    :return: The masked image
    """
    # Replace all black pixels in the image with a value that is neither black nor white
    temp = np.where(img < 1, 127, 0)
    # And the image with the mask.  The background of the image is completely black except
    # where the veins are
    temp_mask = cv2.bitwise_and(temp, temp, mask=mask_in)
    # Replace all black pixels with white pixels, and all other pixels with black pixels
    masked = np.where(temp_mask < 1, 255, 0)
    return masked


def apply_mask_brute_force(img, mask_in):
    """
    Apply a binary mask to an image using brute force.
    :param img: An image represented by a NumPy array
    :param mask_in: A binary mask represented by a NumPy array
    :return: The masked image
    """
    temp_img = img
    for y in range(0, mask_in.shape[0] - 1):
        for x in range(0, mask_in.shape[1] - 1):
            if mask_in[y][x] == 0:
                temp_img[y][x] = 255
    return temp_img


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', action='store', dest='fname', help='Image filename')
    parser.add_argument('-t', action='store_true', default=False, dest='test_array',
                        help='Test the timing of threshold operations')
    results = parser.parse_args()
    total_time = 0

    # Read in the image
    img_in = cv2.imread(results.fname, 0)

    # Apply CLAHE to the image
    start = time.time()
    clahe_img = apply_clahe(img_in, 5.0, (8, 8))
    end = time.time()
    total_time += (end - start)
    print("Time to apply CLAHE: ", (end - start), "s")

    # Create the image mask using global thresholding
    start = time.time()
    mask = create_mask(img_in, 100, 255)
    end = time.time()
    total_time += (end - start)
    print("Time to create mask: ", (end - start), "s")

    # Apply Adaptive Mean Thresholding to the image
    start = time.time()
    adapt_mean_th = adapt_thresh(clahe_img, 255, 105, 20)
    end = time.time()
    total_time += (end - start)
    print("Time to apply Adaptive Mean Thresholding: ", (end - start), "s")

    # Apply the mask using array operations (comparing each pixel of the mask with
    # each pixel of the image
    if results.test_array:
        start = time.time()
        tmp = np.copy(adapt_mean_th)  # Prevents adapt_mean_thresh from being overwritten
        masked_img = apply_mask_brute_force(tmp, mask)
        end = time.time()
        total_time += (end - start)
        print("Time to apply mask using array operations: ", (end - start), "s")

    # Apply the mask using the Numpy where function
    else:
        start = time.time()
        masked_img = apply_mask(adapt_mean_th, mask)
        end = time.time()
        total_time += (end - start)
        print("Time to apply mask using Numpy where: ", (end - start), "s")

    print("Total time elapsed", total_time, "s")

    # Plot all steps of the vein enhancement process
    images = [img_in, clahe_img, mask, adapt_mean_th, masked_img]
    titles = ["Original Image", "CLAHE", "Image Mask", "Adaptive Mean Thresholding", "Masked Image"]
    for i in range(1, 6):
        plt.subplot(5, 1, i)
        plt.imshow(images[i - 1], 'gray')
        plt.title(titles[i - 1])
    plt.show()
    plt.clf()


