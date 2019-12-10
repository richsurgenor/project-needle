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

from sklearn.cluster import DBSCAN
from sklearn.cluster import MiniBatchKMeans
import math
from pyclustering.cluster.kmedoids import kmedoids
import numpy as np
import cv2
import scipy as sp
import scipy.ndimage
import image_processing.spooky_lib as grid
from matplotlib import pyplot as plt
from math import tan, atan


def get_centers(image, nclusters, grid_horizontal, preprocessed=False, enable_gantry_rails=True):
    """
    :param image: image taken by the Raspberry Pi camera
    :param nclusters: number of clusters to run the algorithm with; make sure this is divisible by 2
    :param grid_horizontal:
    :return: kmean clusters (for plotting purposes)
    """
    image_size = np.shape(image)
    mask_grid = grid_mask(grid_horizontal, enable_gantry_rails)
    pic_array_1, pic_array_2 = process_selection_image(image, 0.5, mask_grid, preprocessed)
    centers_first = execute_kmean(pic_array_1, int(nclusters/2))
    centers_second = execute_kmean(pic_array_2, int(nclusters/2))
    centers = np.concatenate((centers_first, centers_second), axis=0)
    return centers


def test_db(image, grid_horizontal):
    """
    For testing DB scan
    """
    image_size = np.shape(image)
    mask_grid = grid_mask(grid_horizontal)
    pic_array_1, pic_array_2 = process_selection_image(image, 0.5, mask_grid)
    centers_first = execute_kmean(pic_array_1, int(300/2))
    centers_second = execute_kmean(pic_array_2, int(300/2))
    centers = np.concatenate((pic_array_1, pic_array_2), axis=0)
    X = centers
    db = execute_DBSCAN(X, 10, 10)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels = db.labels_
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise_ = list(labels).count(-1)
    unique_labels = set(labels)
    colors = [plt.cm.Spectral(each)
              for each in np.linspace(0, 1, len(unique_labels))]
    for k, col in zip(unique_labels, colors):
        if k == -1:
            # Black used for noise.
            col = [0, 0, 0, 1]

        class_member_mask = (labels == k)

        xy = X[class_member_mask & core_samples_mask]
        plt.plot(xy[:, 0], -xy[:, 1], 'o', markerfacecolor=tuple(col),
                 markeredgecolor='k', markersize=1)

        xy = X[class_member_mask & ~core_samples_mask]
        plt.plot(xy[:, 0], -xy[:, 1], 'o', markerfacecolor=tuple(col),
                 markeredgecolor='k', markersize=0.1)

    plt.title('Estimated number of clusters: %d' % n_clusters_)
    plt.show()


def process_selection_image(img_in, threshold, mask_grid, preprocessed=False):
    """
    :param img_in: image taken by the Raspberry Pi camera
    :param threshold: 0 to 1 analog value, selected threshold for the adaptive thresholding step; this function will be
            used in the grid system, needle check, and main algorithm sections.
    :param mask_grid: defined masking area from the grid images
    :param preprocessed: bool whether or not the image has already been preprocessed
    :return: the processed image POINTS that will be further analyzed (a 2xN numpy array)

    Algorithm Process is as follows:
    1) Apply the CLAHE
    2) Create the image mask
    3) Apply adaptive mean thresholding
    4) Apply the mask to the image created by (3)
    5) Extract the remaining points and return a 2xN numpy array
    """
    if not preprocessed:
        clahe_img = apply_clahe(img_in, 7.0, (40, 40))
        mask = create_mask(img_in, 100, 255)
        threshold = int(255*threshold)
        low = adapt_thresh(clahe_img, 255, threshold, 10)
        high = adapt_thresh(clahe_img, 255, threshold, 20)  # we are creating a bandpass filter here
        #adapt_mean_th = adapt_thresh(low, 255, threshold, 15)
        masked_low = apply_mask(low, mask)
        masked_high = apply_mask(high, mask)
        masked_img = masked_low - np.logical_and(masked_low, masked_high)
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
    :param index: bool to decide whether final_selection is returned as a point or index
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
        box_friends = [100 * size[0] / 3280, 300 * size[1] / 2464]  # dimensions of box to check with
        box_enemies = [300 * size[0] / 3280,
                       60 * size[1] / 2464]  # don't forget, dividy by 2 so it's larger than appears!
        [npoints, standev, avgdist, maxdist] = check_box(each, centers, box_friends, box_enemies)
        """
        Ironically, this fucntion works better if we ignore the number of points and instead use the
        standard deviation of the xcoordinates only as the check. I verified this while I was messing
        around with different images. - JPS
        """
        if npoints > hold[0]: # and standev < hold[1]
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


def check_box(kpoint, kset, live, kill):
    """
    :param kpoint: reference point (it's critical that this is passed correctly; we want a tuple [x y])
    :param kset: all the kmean points
    :param live: tuple, box width and height for a valid point analysis
    :param kill: tuple, box width and height for a point that needs to be executed by the guillotine
    :return: tuple containing the number of points in the box, and the standard deviation of the x

    The general idea behind this function is that every kmedoid point (or potentially every kmean point)
    can be analyzed simply by throwing a vertical box around it and finding how many points are in the box and
    how varied the x coordinates are (less varied --> more vertically aligned and the better injection site)

    This is significantly simpler than the other method. The most important part that needs to be checked is that
    the kset input is passed correctly and is iterated through correctly. It's a numpy array so that makes it a
    little more difficult to do than a traditional array.
    """
    # start by defining the box. Luckily, we are not bounded by the image so we do not care if it goes off the page.
    xbounds_good = [kpoint[0]-live[0]/2, kpoint[0]+live[0]/2]
    ybounds_good = [kpoint[1]-live[1]/2, kpoint[1]+live[1]/2]
    xbounds_bad = [kpoint[0]-kill[0]/2, kpoint[0]+kill[0]/2]
    ybounds_bad = [kpoint[1]-kill[1]/2, kpoint[1]+kill[1]/2]
    box_bros = []
    box_brosy = []
    xmedian = get_xmedian(kset)
    kill_next_time = False
    xmedian_bounds = [xmedian-500, xmedian+500]
    for each in kset:
        # We need to decide whether to kill this kpoint
        if each[0] == kpoint[0] and each[1] == kpoint[1]:
            # do nothing, since the kill command will cause this poor kpoint to commit suicide if this is not here'
            kill_next_time = True
            'do nothing'
        elif (xbounds_bad[0] < each[0] < xbounds_bad[1]) and (ybounds_bad[0] < each[1] < ybounds_bad[1]) and kill_next_time:
            break
        if (xbounds_good[0] < each[0] < xbounds_good[1]) and (ybounds_good[0] < each[1] < ybounds_good[1]):
            if xmedian_bounds[0] < each[0] < xmedian_bounds[1]:
                box_bros.append(each[0])
                box_brosy.append(each[1])

    if len(box_bros) > 1.5:  # make sure that it is not 1. That will crash the standev calculation.
        standev = calc_standev(box_bros)
        [avgdist, maxdist] = sort_and_compare(box_brosy)
        # nchain = slope_chain(kpoint, kset, 70, )
    else:
        standev = 10000
        avgdist = 10000
        maxdist = 10000

    return len(box_bros), standev, avgdist, maxdist


def slope_chain(kpoint, kset, max_dist, slope, n):
    '''
    :param kpoint:
    :param kset:
    :param max_dist:
    :param slope
    :return: # number of points that fulfill a desired chain of constant slope

    Note: This algorithm is a recursive algorithm and will be executed until the chain
    has reached a point where no points can fulfill the requirements at the end. If a chain
    reaches a certain length, it will be given a priority in the final selection since any
    set of points that meet this chain requirements are representative of a vein and not noise.
    '''
    n_chain = n
    hold_slope = slope
    for each in kset:
        if get_distance(kpoint, each) < max_dist:
            slope = get_slope(kpoint, each)
            if percent_diff(hold_slope, slope) < 0.2:
                n_chain = n_chain + 1
                slope_chain(each, kset, max_dist, slope, n_chain)

    return n_chain


def get_distance(kpoint, setpoint):
    '''
    :param kpoint: a point
    :param setpoint: a different point
    :return: absolute distance between the two points
    '''
    return abs(math.sqrt((kpoint[0]**2 - setpoint[0]**2) + (kpoint[1]**2 - setpoint[1]**2)))


def get_slope(kpoint, setpoint):
    '''
    :param kpoints: a point
    :param setpoint: a different point
    :return: slope between the two points (if greater than like 8, just cap it at a high value like 100)
    '''
    slope = (setpoint[1]-kpoint[1])/(setpoint[0] - kpoint[0])
    if slope > 8:
        slope = 100
    if slope < -8:
        slope = -100
    return slope


def percent_diff(value, new):
    # this is self explanatory so I am not going to write out more than I need to...well, I have already written this
    # much about it so why not...NO. I refuse to give in here.
    return (new-value)/(new+value)


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
    slice_size = 100
    increment, remainder = ysize//slice_size,  ysize % slice_size
    horizontal = np.ones((xsize, ysize))
    # divide into size 150 segments; may change this as needed
    k = 0
    while k < (increment):
        if k % 2 == 0:
            horizontal[k*100:(k+1)*100, :] = 0
        k = k + 1

    return horizontal


def grid_mask(grid_vertical, enable_gantry_rails=True):
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
    if enable_gantry_rails:  # in case Rich comes thru and crops the entire image ( ͡° ͜ʖ ͡°)
        min_x = min_x + 133#760#100#
        max_x = max_x - 200#880#100#
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


def execute_DBSCAN(dataset, eps, min_samp):
    """
    :param dataset: points remaining after either the image processing or kmean step (haven't decided which yet)
    :param eps: epsilon value (we'll have to tweak this until it corresponds to veins and rejects shadow groups)
    :param min_samples: not sure what this is yet
    :return: unsure
    """
    db = DBSCAN(eps=eps, min_samples = min_samp).fit(dataset)
    return db

def initialize_grids(image, file_horizontal, file_vertical, unused_arg=False):
    """
    :param image: photo taken by the pi camera
    :param file_horizontal: address of file containing horizontal grid information
    :param file_vertical: address of file containing vertical grid information
    :return: two grid arrays, grid_vertical and grid_horizontal
    """
    horizontal = cv2.imread(file_horizontal, 0)
    vertical = cv2.imread(file_vertical, 0)
    if np.shape(image) != np.shape(horizontal):
        re = np.shape(image)
        horizontal = cv2.resize(horizontal, (re[0], re[1]))
        vertical = cv2.resize(vertical, (re[0], re[1]))
    grid_horizontal = grid.process_grid(horizontal, 0.6)
    grid_vertical = grid.process_grid(vertical, 0.6)
    return grid_vertical, grid_horizontal

def initialize_grids(target_res, np_horizontal, np_vertical):
    """
    :param image: photo taken by the pi camera
    :param file_horizontal: numpy array containing horizontal grid information
    :param file_vertical: numpy array containing vertical grid information
    :return: two grid arrays, grid_vertical and grid_horizontal
    """
    if target_res != np.shape(np_horizontal):
        re = target_res
        np_horizontal = cv2.resize(np_horizontal, (re[1], re[0]))
        np_vertical = cv2.resize(np_vertical, (re[1], re[0]))
    grid_horizontal = grid.process_grid(np_horizontal, 0.6)
    grid_vertical = grid.process_grid(np_vertical, 0.6)
    return grid_vertical, grid_horizontal


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


def isolate_needle(updated_image, grid_vertical, enable_gantry_rails=True):
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
    mask_grid = grid_mask(grid_vertical, enable_gantry_rails)
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
    plt.plot
    plt.imshow(image)
    plt.show()
    return np.where(image == 0)


def extract_points(img):
    """
    :param img: numpy array of processed image after thresholding and masking operations
    :return: set of points that represent the veins
    """
    img = np.transpose(img)
    return list(zip(*np.where(img == 1)))


def isolate_sharpie(img, mask_img, mask_t, adapt_t, c, grid_vertical, enable_gantry_rails):
    """

    :param img: An image with the sharpie in the fram
    :param mask_img: The original image used to create the mask
    :param mask_t: The threshold value used for the mask (0 to 255)
    :param adapt_t: The threshold value for adaptive thresholding to find the sharpie
    :param c: Constant for adaptive thresholding
    :param grid_vertical: The grid with veritcal lines (I think)
    :param enable_gantry_rails: To remove the gantry rails
    :return: The sharpie tip coordinate in pixels
    """
    #  Process the image
    clahe_img = apply_clahe(img, 5.0, (8, 8))
    mask = create_mask(mask_img, mask_t, 255)
    plt.imshow(mask, 'gray')
    threshold = int(adapt_t*255)
    if threshold % 2 == 0:
        threshold = threshold + 1
    adapt_mean_th = adapt_thresh(clahe_img, 255, threshold, c)
    # plt.imshow(adapt_mean_th, 'gray')

    #  Apply the mask
    mask_grid = grid_mask(grid_vertical, enable_gantry_rails)
    masked_img = apply_mask(adapt_mean_th, mask)
    masked_img = (np.logical_and(mask_grid, masked_img)) + np.logical_not(mask_grid)
    plt.imshow(masked_img, 'gray')

    #  Extract the remaining points and remove any associated with the gantry rails
    sharpie_pts = np.where(masked_img == 0)
    temp_x = sharpie_pts[0][sharpie_pts[1] < 2400]
    temp_y = sharpie_pts[1][sharpie_pts[1] < 2400]
    temp_x = temp_x[temp_y > 700]
    temp_y = temp_y[temp_y > 700]
    combined = np.vstack((temp_x, temp_y))
    minarray = combined[0]
    idx = np.argmax(minarray)
    xarray = combined[1]
    yarray = combined[0]
    sharpie_pos = [yarray[idx], xarray[idx]]
    return sharpie_pos, mask, masked_img


def calc_diff(needle_height, dist_to_skin, dist_to_target):
    """
    Calculates the difference between the location of the needle tip and the location
    of the target in the x or y direction.  All parameters should be given in millimeters.
    :param needle_height: from the top of the needle to the tip (in mm)
    :param dist_to_skin: the distance from the tip of the needle to the arm (in mm)
    :param dist_to_target: location (in mm) of the opposite home point
    :return: the difference between the needle tip and target
    """
    total_height = needle_height + dist_to_skin
    dist_to_needle = needle_height * tan(atan(dist_to_target / total_height))
    return dist_to_target - dist_to_needle


def needle_check(needle_height, dist_to_skin, dist_to_target, right_home_pt):
    """
    Calculates the distance of the needle tip away from the target in the x or y
    direction.  The left home point (origin of the needle) is assumed to be at (0, 0).
    If the target is past the midway point, then the diffference is negative, indicating
    that the needle needs to move back towards the origin in the -x or -y direction.
    :param needle_height: from the top of the needle to the tip (in mm)
    :param dist_to_skin: the distance from the tip of the needle to the arm (in mm)
    :param dist_to_target: the x or y coordinate of the target (in mm)
    :param right_home_pt: location (in mm) of the opposite home point
    :return: the difference between the needle tip and target
    """
    mid = right_home_pt / 2  # the midway point on the grid

    if dist_to_target < mid:
        diff = calc_diff(needle_height, dist_to_skin, dist_to_target)
    else:
        diff = - calc_diff(needle_height, dist_to_skin, (right_home_pt - dist_to_target))
    return diff