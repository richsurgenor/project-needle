"""
    ProStick Python Library
    Justin Sutherland
    10/19/2019

    File is structured simply as a large set of functions. This
    is commonly known as a "library". No library card required.
    This library shall be titled prostick_lib.py henceforth.

    Function library that contains all image processing functions
    such as thresholding, kmean, kmedoid, masking, etc. Any future
    functions for the coordinate system logic will reside in a separate
    library titled "spooky"
"""

from sklearn.cluster import KMeans
from sklearn.cluster import MiniBatchKMeans
import math
from pyclustering.cluster.kmedoids import kmedoids
from pyclustering.cluster.elbow import elbow
from pyclustering.cluster.kmeans import kmeans, kmeans_visualizer
from pyclustering.cluster.center_initializer import kmeans_plusplus_initializer
import numpy as np
import cv2
import time
import scipy as sp
import scipy.ndimage
from matplotlib import pyplot as plt
import spooky_lib as grid


def process_image(img_in, threshold, time_enable):
    """
    :param img_in: image taken by the Raspberry Pi camera
    :param threshold: 0 to 1 analog value, selected threshold for the adaptive thresholding step; this function will be
            used in the grid system, needle check, and main algorithm sections.
    :param time_enable: (boolean) enable time checks to find the execution time on the algorithm
    :return: the processed image POINTS that will be further analyzed (a 2xN numpy array)

    Algorithm Process is as follows:
    1) Apply the CLAHE
    2) Create the image mask
    3) Apply adaptive mean thresholding
    4) Apply the mask to the image created by (3)
    5) Extract the remaining points and return a 2xN numpy array
    """
    clahe_img = apply_clahe(img_in, 5.0, (8, 8))
    mask = create_mask(img_in, 100, 255)
    threshold = int(255*threshold)
    adapt_mean_th = adapt_thresh(clahe_img, 255, threshold, 20)
    masked_img = apply_mask(adapt_mean_th, mask)
    mask_rail = rail_mask()
    # for some reason this bit level logic on the images was really hard for me to do...
    masked_img = (np.logical_and(mask_rail, masked_img)) + np.logical_not(mask_rail)
    horizontal_v1 = create_strips()
    horizontal_v2 = np.logical_not(horizontal_v1)
    masked_img1 = np.logical_not((np.logical_or(horizontal_v1, masked_img)))
    masked_img2 = np.logical_not((np.logical_or(horizontal_v2, masked_img)))
    pic_array1 = extract_points(masked_img1)
    pic_array2 = extract_points(masked_img2)
    return np.array(pic_array1), np.array(pic_array2)


def final_selection(centers):
    """
    :param centers: kmean dataset
    :return: final [x, y] coordinate set for the injection site

    We want the final selection site to be one that has a neighborhood with low variance in its
    neighbors x coordinates (i.e. resembles a vertical line). We are currently doing this by placing a
    box around each kmean point and analyzing how many points are above and below it as well as their respective
    variances. Also using a function sort_and_compare where we compare the relative y distances from point to point.
    The lower the relative distance from point to point, the better.
    """
    final_selection = [0, 0]
    hold = [0, 1000, 1000, 1000]
    for each in centers:
        box_friend = [60, 300]  # dimensions of box to check with
        [npoints, standev, avgdist, maxdist] = check_box(each, centers, box_friend[0], box_friend[1])
        """
        Ironically, this fucntion works better if we ignore the number of points and instead use the
        standard deviation of the xcoordinates only as the check. I verified this while I was messing
        around with different images. - JPS
        """
        if standev < hold[1] and npoints > 2:
            hold = [npoints, standev, avgdist, maxdist]
            final_selection = each

    return final_selection


def create_kmedoids(kmean_set, n):
    """
    :param centers: set of kmean points
    :param n: number of kmedoids we want
    :return: a set of kmedoid points to be used to get the final selection point
    """
    # Run the K-Medoids algorithm on the 50 centers returned by K-Means
    # Set random initial medoids.  Also determines how many medoids will be found
    initial_medoids = [25, 25, 25, 25, 25]
    # Create instance of k-medoids algorithm
    kmedoids_instance = kmedoids(kmean_set, initial_medoids)
    # Run cluster analysis and obtain the medoids
    kmedoids_instance.process()
    clusters = kmedoids_instance.get_clusters()
    medoids = kmedoids_instance.get_medoids()
    # Extract the medoids in their own list
    clust_x = []
    clust_y = []
    for i in range(0, len(medoids)):
        clust_x.append(kmean_set[medoids[i]][0])
        clust_y.append(kmean_set[medoids[i]][1])

    return [clust_x, clust_y]


def check_box(kpoint, kset, width, height):
    """
    :param kpoint: reference point (it's critical that this is passed correctly; we want a tuple [x y])
    :param kset: all the kmean points
    :param width: box width
    :param height: box height
    :return: tuple containing the number of points in the box, and the standard deviation of the x

    The general idea behind this function is that every kmedoid point (or potentially every kmean point)
    can be analyzed simply by throwing a vertical box around it and finding how many points are in the box and
    how varied the x coordinates are (less varied --> more vertically aligned and the better injection site)

    This is significantly simpler than the other method. The most important part that needs to be checked is that
    the kset input is passed correctly and is iterated through correctly. It's a numpy array so that makes it a
    little more difficult to do than a traditional array.
    """
    # start by defining the box. Luckily, we are not bounded by the image so we do not care if it goes off the page.
    xbounds = [kpoint[0]-width/2, kpoint[0]+width/2]
    ybounds = [kpoint[1]-height/2, kpoint[1]+height/2]
    box_bros = []
    box_brosy = []
    xmedian = get_xmedian(kset)
    xmedian_bounds = [xmedian-500, xmedian+500]
    for each in kset:
        if (xbounds[0] < each[0] < xbounds[1]) and (ybounds[0] < each[1] < ybounds[1]):
            if xmedian_bounds[0] < each[0] < xmedian_bounds[1]:
                box_bros.append(each[0])
                box_brosy.append(each[1])

    if len(box_bros) > 1.5:  # make sure that it is not 1. That will crash the standev calculation.
        standev = calc_standev(box_bros)
        [avgdist, maxdist] = sort_and_compare(box_brosy)
    else:
        standev = 10000
        avgdist = 10000
        maxdist = 10000

    return len(box_bros), standev, avgdist, maxdist


def calc_standev(x_set):
    """
    :param x_set:  array containing y values of all points selected
    :return: standev: standard deviation of the y coordinates.
    """
    total = 0
    mean_x = sum(x_set)/len(x_set)
    for each in x_set:
        total += (each - mean_x)**2

    return math.sqrt(total/(len(x_set)-1))


def sort_and_compare(pset):
    """
    :param pset: set of points that passed the box check algorithm
    :return: a tuple containing the average y distance and the max y distance
    """
    sortedy = sorted(pset)
    i = 0
    holddist = 0
    avgd = 0
    maxdist = 0
    while i < (len(sortedy)-1):
        dist = abs(sortedy[i + 1] - sortedy[i])
        avgd = avgd + dist
        if dist > holddist:
            maxdist = dist
        i = i + 1

    avgd = avgd / i
    return [avgd, maxdist]


def check_injection(needle_image, iv_site):
    """
    :param needle_image: image with the needle overlayed; want to make sure it is in the right spot
    :param iv_site: original injection site chosen by the algorithm
    :return: a boolean value (0 for good, 1 for bad) and a tuple containing a boolean value and an adjustment heading
    """
    clahe_img = apply_clahe(needle_image, 5.0, (8, 8))
    mask = create_mask(needle_image, 100, 255)
    adapt_mean_th = adapt_thresh(clahe_img, 255, 135, 20)
    masked_img = apply_mask(adapt_mean_th, mask)
    pic_array = extract_points(masked_img)
    pic_array_np = np.array(pic_array)


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


def extract_points(img):
    """
    :param img: numpy array of processed image after thresholding and masking operations
    :return: set of points that represent the veins
    """
    img = np.transpose(img)
    return list(zip(*np.where(img == 1)))


def get_xmedian(points):
    """
    :param points: final kmean set
    :return: new_points: median of the x coordinates
    
    I am having an issue where some points are making it through the process image algorithm and are
    on the gantry rails and not from the arm. These points are also perfectly verticle so they are causing serious
    problems in the final selection algorithm.
    
    We will call this function in final selection. Iterating through the entire dataset would take too long.
    """
    xpoints = []
    for each in points:
        xpoints.append(each[0])  # pull the x coordinate out into xpoints
    # sort the array
    sortedx = sorted(xpoints)
    middle = int(len(sortedx)/2)  # I do not care if this is not the exact median
    return sortedx[middle]


def reduce_data(image, sigma_x, sigma_y):
    """
    :param image: processed image from image processing functions
    :param sigma_x: unsure what this does; default this to 2
    :param sigma_y: unsure what this does; default this to 3
    :return: image with reduced points (e.g. I want to get 7000 pts from 70,000 pts)
    """
    sigma = [sigma_y, sigma_x]
    y = sp.ndimage.filters.gaussian_filter(image, sigma, mode='constant')
    return y


def create_strips():
    """
    :return: image with horizontal areas removed (so 0's) and the rest 1's

    Idea: if we remove segments of the vein data properly, we can force the kmean to
    be faster because the data will resemble more traditional kmean problems. In essence,
    continuities are bad; discontinuities are good.
    """
    horizontal = np.ones((2464, 3280))
    # divide into size 154 segments
    horizontal[0:154, :] = 0
    horizontal[154*2:154*3, :] = 0
    horizontal[154*4:154*5, :] = 0
    horizontal[154*6:154*7, :] = 0
    horizontal[154*8:154*9, :] = 0
    horizontal[154*10:154*11, :] = 0
    horizontal[154*12:154*13, :] = 0
    horizontal[154*14:154*15, :] = 0
    #horizontal[154*16:154*17, :] = 0
    return horizontal


def rail_mask():
    """
    :return: image with the gantry rails auto removed

    I am having an issue with the gantry rails appearing in the image so I am going to perform a logical
    operation on the numpy array to remove them.

    The dimensions of the image are always the same and the gantry rails do not move so I will make the
    values for this mask constant. No need to derive an algorithm for extracting them from the image.
    """

    # From observing the image, the gangtry rails reside from x = [0 800] and x = [2400 3280]
    gantry_mask = np.ones((2464, 3280))
    gantry_mask[:, 0:800] = 0
    gantry_mask[:, 2400:3280] = 0
    gantry_mask[0:200, :] = 0
    gantry_mask[2300:2464, :] = 0
    return gantry_mask


def execute_kmean(dataset, nclusters):
    """
    :param dataset: valid vein points from image processing
    :param nclusters: number of clusters to generate
    :return: set of n number of cluster centers
    """
    kmeans = MiniBatchKMeans(n_clusters=nclusters, random_state=0).fit(dataset)  # default is Kmeans++ so this function auto does that for us
    return kmeans.cluster_centers_


def initialize_grids(file_horizontal, file_vertical):
    """
    :param file_horizontal: address of file containing horizontal grid information
    :param file_vertical: address of file containing vertical grid information
    :return: two grid arrays, grid_vertical and grid_horizontal
    """
    grid_horizontal = cv2.imread(file_horizontal, 0)
    grid_vertical = cv2.imread(file_vertical, 0)
    grid_horizontal = grid.process_grid(grid_horizontal, 0.6)
    grid_vertical = grid.process_grid(grid_vertical, 0.6)
    return grid_vertical, grid_horizontal