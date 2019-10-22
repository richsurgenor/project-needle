# Abstract interface for GUI to use

from abc import abstractmethod
from image_processing.thresholding import process_image_get_mask

class AbstractProcessor:

    def __init__(self, camera):
        self.camera = camera

    @abstractmethod
    def process_image(self, image):
        """
        :param image:
        :return: (processed_image, [points])
        """
        pass

class AbstractGantryController:

    def __init__(self, camera):
        # State of axes in millimeters
        self.x = None
        self.y = None
        self.z = None

    @abstractmethod
    def get_current_axes_distance_from_home(self):
        """
        :return: (x, y, z)
        """
        pass

    @abstractmethod
    def send_gantry_absolute_pos(self, x, y, z):
        """
        Move Gantry to absolute position.
        :param x: x pos
        :param y: y pos
        :param z: z pos
        :return: success
        """
        pass

    @abstractmethod
    def send_gantry_distance(self, x, y, z):
        """
        Move Gantry relative to current position.
        :param x: x pos
        :param y: y pos
        :param z: z pos
        :return: success
        """
        pass

    def send_gantry_home(self):
        """
        Send Gantry Home
        :return: success
        """
        self.send_gantry_absolute_pos(0, 0, 0)

class ProcessorMock(AbstractProcessor):

    def process_image(self, image):
        print("fake image!")
        return image, [(320*3,120*3), (481*3, 233*3), (179*3, 211*3)]#[(100,100), (100, 200), (200, 250)]

    """
    TODO: Provide some exceptions for the image processor to raise for situations like:
    1. not finding any ideal points
    2. low quality image detected
    """


class Processor(AbstractProcessor):

    def process_image(self, image):
        process_image_get_mask(image, True)
        return image, [(320 * 3, 120 * 3), (481 * 3, 233 * 3), (179 * 3, 211 * 3)]



