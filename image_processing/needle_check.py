"""
Short script to test the needle verification function
"""
from image_processing.prostick_lib import needle_check


if __name__ == "__main__":
    target_coord = [60, 100]  # sample (x, y) coordinates

    # Calculate and print the differences in the x and y directions
    # The parameters are arbitrarily set and do not necessarily reflect
    # the actual measurements
    diff_x = needle_check(40, 10, target_coord[0], 150)
    diff_y = needle_check(40, 10, target_coord[1], 175)
    print("Adjustment in the x direction: ", diff_x, "mm")
    print("Adjustment in the y direction: ", diff_y, "mm")
