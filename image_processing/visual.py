"""
    "Visual" Library
    Justin Sutherland
    11/11/2019

    The Visualization Library is simply a set of functions for displaying common plots
    and images.

    I am doing this because these commands just irritate me for some reason and I want them
    put away in this file where I do not have to look at their annoying presence.
"""

from matplotlib import pyplot as plt


def plot_clusters(image, centers, selection):
    """
    :param image: image taken by the camera
    :param centers: kmean clusters
    :return: plot of the kmean clusters vs the image
    """
    plt.imshow(image, 'gray')
    plt.scatter(centers[:, 0], centers[:, 1], c='blue', s=10, alpha=0.5)
    plt.scatter(selection[0], selection[1], c='red', s=10, alpha=0.5)
    plt.show()
    plt.clf()


def show_grids(grid_horizontal, grid_vertical):
    'do nothing'


def plot_needle(needle_image, needle_pos):
    """
    :param needle_image:
    :param needle_pos:
    :return:
    """
    plt.imshow(needle_image, 'gray')
    plt.scatter(needle_pos[0], needle_pos[1], c='red', s=10, alpha=0.5)
    plt.show()
    plt.clf()