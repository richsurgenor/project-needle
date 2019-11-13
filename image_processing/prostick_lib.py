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

from sklearn.cluster import MiniBatchKMeans
import math
from pyclustering.cluster.kmedoids import kmedoids
import numpy as np
import cv2
import scipy as sp
import scipy.ndimage
import image_processing.spooky_lib as grid
from matplotlib import pyplot as plt


def get_centers(image, nclusters, grid, preprocessed=False):
    """
    :param image: image taken by the Raspberry Pi camera
    :param nclusters: number of clusters to run the algorithm with; make sure this is divisible by 2
    :param grid: grid img
    :return: kmean clusters (for plotting purposes)
    """
    mask_grid = grid_mask(grid)
    pic_array_1, pic_array_2 = process_selection_image(image, 0.5, mask_grid, preprocessed)
    centers_first = execute_kmean(pic_array_1, int(nclusters/2))
    centers_second = execute_kmean(pic_array_2, int(nclusters/2))
    centers = np.concatenate((centers_first, centers_second), axis=0)
    return centers


def process_selection_image(img_in, threshold, mask_grid, preprocessed=False):
    """
    :param img_in: image taken by the Raspberry Pi camera
    :param threshold: 0 to 1 analog value, selected threshold for the adaptive thresholding step; this function will be
            used in the grid system, needle check, and main algorithm sections.
    :param mask_grid: defined masking area from the grid images
    :return: the processed image POINTS that will be further analyzed (a 2xN numpy array)

    Algorithm Process is as follows:
    1) Apply the CLAHE
    2) Create the image mask
    3) Apply adaptive mean thresholding
    4) Apply the mask to the image created by (3)
    5) Extract the remaining points and return a 2xN numpy array
    """
    if not preprocessed:
        clahe_img = apply_clahe(img_in, 5.0, (8, 8))
        mask = create_mask(img_in, 100, 255)
        threshold = int(255*threshold)
        adapt_mean_th = adapt_thresh(clahe_img, 255, threshold, 20)
        masked_img = apply_mask(adapt_mean_th, mask)
    else:
        masked_img = img_in
    # for some reason this bit level logic on the images was really hard for me to do...
    masked_img = (np.logical_and(mask_grid, masked_img)) + np.logical_not(mask_grid)
    horizontal_v1 = create_strips(masked_img)
    horizontal_v2 = np.logical_not(horizontal_v1)
    masked_img1 = np.logical_not((np.logical_or(horizontal_v1, masked_img)))
    masked_img2 = np.logical_not((np.logical_or(horizontal_v2, masked_img)))
    pic_array1 = extract_points(masked_img1)
    pic_array2 = extract_points(masked_img2)
    return np.array(pic_array1), np.array(pic_array2)


def final_selection(centers, size, index=False):
    """
    :param centers: kmean dataset
    :param size: size of image array to proportion our box friend correctly
    :return: final [x, y] coordinate set for the injection site

    We want the final selection site to be one that has a neighborhood with low variance in its
    neighbors x coordinates (i.e. resembles a vertical line). We are currently doing this by placing a
    box around each kmean point and analyzing how many points are above and below it as well as their respective
    variances. Also using a function sort_and_compare where we compare the relative y distances from point to point.
    The lower the relative distance from point to point, the better.
    """
    final_selection = None
    hold = [0, 1000, 1000, 1000]
    for i in range(0, len(centers)):
        each = centers[i]
        # original box_friend dimensions were 60x300 for a 3280, 2464 array
        # so the ratio is x/3280 and y/2464
        box_friend = [60*size[0]/3280, 300*size[1]/2464]  # dimensions of box to check with
        [npoints, standev, avgdist, maxdist] = check_box(each, centers, box_friend[0], box_friend[1])
        """
        Ironically, this fucntion works better if we ignore the number of points and instead use the
        standard deviation of the xcoordinates only as the check. I verified this while I was messing
        around with different images. - JPS
        """
        if standev < hold[1] and npoints > 2:
            hold = [npoints, standev, avgdist, maxdist]
            if index:
                final_selection = i
            else:
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


def create_strips(image):
    """
    :return: image with horizontal areas removed (so 0's) and the rest 1's

    Idea: if we remove segments of the vein data properly, we can force the kmean to
    be faster because the data will resemble more traditional kmean problems. In essence,
    continuities are bad; discontinuities are good.
    """
    #  determine the image size
    [xsize, ysize] = np.shape(image)
    slice_size = 150
    increment, remainder = ysize//slice_size,  ysize % slice_size
    horizontal = np.ones((xsize, ysize))
    # divide into size 150 segments; may change this as needed
    k = 0
    while k < (increment):
        if k % 2 == 0:
            horizontal[k*100:(k+1)*100, :] = 0
        k = k + 1

    return horizontal


def grid_mask(grid_vertical):
    """
    :return: image with the gantry rails auto removed

    REQUIRES THE GRID "SPOOKY" LIBRARY spooky_lib.py
    We are going to now mask the image based on the farthest left/right and farthest top/bottom
    positions of the grids.
    """
    #  To start, find the points that == 0
    sizey, sizex = np.shape(grid_vertical)
    points = np.where(grid_vertical < 0.5)
    min_y, max_y = min(points[0]), max(points[0])
    min_x, max_x = min(points[1]), max(points[1])
    #  I want to add more clearance here on the xaxis
    #  Also I am adding logic here to ensure that the gantry rails are eliminated. Take
    #  the x size and divide it by 2 and multiply by 0.222 and +/- that on both ends
    #  (Did I forget to mention that these gantry rails are the bane of my existence?
    enable_gantry_rails = True
    if enable_gantry_rails:  # in case Rich comes thru and crops the entire image ( ͡° ͜ʖ ͡°)
        min_x = min_x + 100
        max_x = max_x - 100
    gantry_mask = np.ones((sizey, sizex))
    gantry_mask[:, 0:min_x] = 0
    gantry_mask[:, max_x:sizex] = 0
    gantry_mask[0:min_y, :] = 0
    gantry_mask[max_y:sizey, :] = 0

    return gantry_mask


def execute_kmean(dataset, nclusters):
    """
    :param dataset: valid vein points from image processing
    :param nclusters: number of clusters to generate
    :return: set of n number of cluster centers
    """
    kmeans = MiniBatchKMeans(n_clusters=nclusters, random_state=0).fit(dataset)  # default is Kmeans++ so this function auto does that for us
    return kmeans.cluster_centers_

def initialize_horizontal_grid(file_horizontal):
    """
    :param file_horizontal: address of file containing horizontal grid information
    :return: grid_horizontal array
    """
    grid_horizontal = cv2.imread(file_horizontal, 0)
    grid_horizontal = grid.process_grid(grid_horizontal, 0.6)
    return grid_horizontal

def initialize_vertical_grid(file_vertical):
    """
    :param file_vertical: address of file containing vertical grid information
    :return: grid_vertical array
    """
    grid_vertical = cv2.imread(file_vertical, 0)
    grid_vertical = grid.process_grid(grid_vertical, 0.6)
    return grid_vertical

def initialize_grids(file_horizontal, file_vertical):
    """
    :param file_horizontal: address of file containing horizontal grid information
    :param file_vertical: address of file containing vertical grid information
    :return: two grid arrays, grid_vertical and grid_horizontal
    """
    return initialize_vertical_grid(file_vertical), initialize_horizontal_grid(file_horizontal)


def compare_points(iv_site, needle, grid_horizontal, grid_vertical):
    """
    :param iv_site: injection site
    :param needle: needle position
    :return: xy difference between them to pass to the Arduino (always relative to the injection site)

    This is the function that will be called during error checking to compare the position of
    the needle versus the proposed injection site.
    REQUIRES THE GRID LIBRARY "SPOOKY_LIB"
    """
    # FUN FACT - YOU CANNOT DO THIS IN PIXEL COORDINATES UNDER ANY CONDITIONS! It will not work
    # with the grid logic. You always have to calculate the new heading using mm coordinates!
    iv_mm = get_position(iv_site, grid_horizontal, grid_vertical)
    needle_mm = get_position(needle, grid_horizontal, grid_vertical)
    # Also note that because I suck at keeping track of variables and dimensions, this
    # correction variable has the coordinates purposefully swapped
    correction = [iv_mm[1]-needle_mm[1], iv_mm[0]-needle_mm[0]]
    return correction


def get_position(site, grid_horizontal, grid_vertical):
    """
    :param site: selected xy position on the image
    :param grid_horizontal: image array of the horizontal grid lines
    :param grid_vertical: image array of the vertical grid lines
    :return: xy position in actual mm length (e.g. 55.2 mm over, 67.1 mm down)
    REQUIRES THE GRID LIBRARY "SPOOKY_LIB"
    """
    xslice, yslice = grid.slice_grid(site, grid_horizontal, grid_vertical)
    [xpos, ypos] = grid.interpolate(site, yslice, xslice)
    return xpos, ypos

"""

Needle Error Checking Logic

Justin Sutherland
11/12/2019

Separating this from the rest of the file for my sake.

"""


def check_needle(updated_image, injection_site):
    """
    :param updated_image: updated image taken by the Raspberry Pi camera after a needle movement operation has
                          been performed
    :param injection_site: chosen injection_site
    :return: valid: 0 if site is not good enough, 1 if site is approved for an injection
    :return: correction: tuple containing a new move command (xy) for the gantry to adjust to the new site
                         (only if "valid" is a 0)
    """


def isolate_needle(updated_image, grid_vertical):
    """
    :param updated_image: image with the needle in view of the camera
    :return: position of the needle tip in pixel coordinates (we want to keep this in pixels because the grid
             library only takes its inputs as pixel coordinates and I really do not want to write a reciprocal
             function for converting mm coordinates to xy pixel locations)

    This function will need an equivalent function "isolate_sharpie" for test purposes at the Senior Design Fair.
    Hopefully that only involves adjusting the threshold of the image processing taking place in this function.
    """

    #  To isolate the needle in the image, let's use the same image processing for the veins but with a higher
    #  threshold value to remove the veins and any noise. If this is done properly (and like it was prototyped in
    #  MATLAB, we should have just a narrow black line remaining.
    mask_grid = grid_mask(grid_vertical)
    image_points = process_needle_image(updated_image, mask_grid)
    #  With the isolated needle, extract the point at the lowest y position (average all the points x and y
    #  positions first just to make sure we are not pulling off noise (there's a high chance of that if we do not
    #  do this check
    idx = find_needle_tip(image_points)
    xarray = image_points[0]
    yarray = image_points[1]
    needle_position = [yarray[idx], xarray[idx]]
    return needle_position


def find_needle_tip(image_points):
    """
    :param image_points: 2xN numpy array containing all potential needle points
    :return: a single xy coordinate representing the tip of the needle

    Luckily, the needle is always oriented vertically so we can always get an accurate guess by just pulling off
    the lowest y position (with the checks described in "isolate_needle"
    """
    minarray = image_points[0]
    idx = np.argmax(minarray)
    return idx


def process_needle_image(img_in, mask_grid):
    """
    :param img_in: image taken by the Raspberry Pi camera
    :return: the processed image POINTS that will be further analyzed (a 2xN numpy array)

    Algorithm Process is as follows:
    1) Apply the CLAHE
    2) Create the image mask
    3) Apply adaptive mean thresholding
    4) Apply the mask to the image created by (3)
    5) Extract the remaining points and return a 2xN numpy array
    """
    clahe_img = apply_clahe(img_in, 5.0, (8, 8))
    threshold = int(0.6*255)
    adapt_mean_th = adapt_thresh(clahe_img, 255, threshold, 97)
    adapt_mean_th = np.logical_or(adapt_mean_th, adapt_mean_th)
    image = (np.logical_and(mask_grid, adapt_mean_th)) + np.logical_not(mask_grid)
    #plt.plot
    #plt.imshow(image)
    #plt.show()
    return np.where(image == 0)


def extract_points(img):
    """
    :param img: numpy array of processed image after thresholding and masking operations
    :return: set of points that represent the veins
    """
    img = np.transpose(img)
    return list(zip(*np.where(img == 1)))


