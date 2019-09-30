# Abstract methods for GUI to use

# Things that will go in here:
# og img
# process

from abc import abstractmethod

class AbstractProcessor:

    def __init__(self, camera):
        self.camera = camera

    @abstractmethod
    def process_image(self, image):
        """
        :param image:
        :return: (processed_image, [coords])
        """
        pass


class ProcessorMock(AbstractProcessor):

    def process_image(self, image):
        print("fake image!")
        return image


class Processor(AbstractProcessor):

    def process_image(self, image):
        pass



