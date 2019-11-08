from math import tan, atan


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


if __name__ == "__main__":
    target_coord = [60, 100]  # sample (x, y) coordinates

    # Calculate and print the differences in the x and y directions
    # The parameters are arbitrarily set and do not necessarily reflect
    # the actual measurements
    diff_x = needle_check(40, 10, target_coord[0], 150)
    diff_y = needle_check(40, 10, target_coord[1], 175)
    print("Adjustment in the x direction: ", diff_x, "mm")
    print("Adjustment in the y direction: ", diff_y, "mm")
