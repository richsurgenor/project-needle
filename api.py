# Interfaces for image processing/gantry

from abc import abstractmethod
import time
import threading

from serial import Serial
import os

USING_PI = os.uname()[4][:3] == 'arm'

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
        pass


def get_direction(current, target):
    if current - target < 0:
        return 1
    else:
        return -1

class GantryMock(threading.Thread):
    """
    simulate gantry
    """


    def __init__(self):
        threading.Thread.__init__(self)

        self.point = { "x": 40, "y": 40, "z": 40}

        self.des_point = { "x": 0, "y": 0, "z": 0}

    def run(self):
        print("Gantry thread initialized..")
        while True:
            pass

    def is_home(self):
        return self.point['x'] == 0 and self.point['y'] == 0 and self.point['z'] == 0

    def set_gantry_absolute_pos(self, in_point):
        for axis in self.des_point:
            self.des_point[axis] = in_point[axis]

        while self.point['x'] != self.des_point['x'] and self.point['y'] != self.des_point['y'] and self.point['z'] != self.des_point['z']:
            time.sleep(0.1) # do work
            for axis in self.des_point:
                cur = self.point[axis]
                tar = self.des_point[axis]
                self.point[axis] = cur + get_direction(cur, tar)

            print("x: " + str(self.point['x']) + " y + " + str(self.point['y']) + " z " + str(self.point['z']))

    def get_gantry_pos(self):
        time.sleep(0.5)
        return self.point

if USING_PI:
    SERIAL_INTERFACE = '/dev/ttyACM0'
else:
    SERIAL_INTERFACE = '/dev/cu.usbmodem1421'
BAUD_RATE = 115200

class AbstractGantryController(threading.Thread):
    """
    Will interface with arduino to move/check status of gantry.
    """

    @abstractmethod
    def __init__(self, camera):
        pass

    @abstractmethod
    def get_current_gantry_pos(self):
        """
        Request current pos from arduino.
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
        self.send_gantry_absolute_pos({"x": 0, "y": 0, "z": 0})

    @abstractmethod
    def send_coordinate(self, x, y):
        """
        :param x: x in mm
        :param y: y in mm
        :return:
        """
        pass

POSITION_UPDATE = b'1'
SEND_COORDINATE = '8'
END_MESSAGE = '9'

class GantryController(AbstractGantryController):

    def __init__(self):
        threading.Thread.__init__(self) # TODO: add thread events..
        # State of axes in millimeters
        self.x = 0
        self.y = 0
        self.z = 0

        print("initializing serial interface..")
        self.arduino = Serial(SERIAL_INTERFACE, BAUD_RATE)
        print("connected to serial interface..")

    def run(self):
        print("started gantry controller thread...")
        while True:
            if self.arduino.inWaiting() > 0:
                line = self.arduino.readline()
                line = line.rstrip()
                if len(line) > 0: # for some reason a newline character is by itself after readline
                    cmd = line[0:1]

                    if cmd == POSITION_UPDATE:
                        print("Received position update.")

                    print(line)

    def get_current_gantry_pos(self):
        pass

    def send_gantry_absolute_pos(self, x, y, z):
        pass

    def send_gantry_distance(self, x, y, z):
        pass

    def send_coordinate(self, x, y):
        print("sending coordinate...")
        self.arduino.write("hi".encode('ascii'))
        pass

    def send_msg(self, msg):
        self.arduino.write(msg.encode('ascii'))


class GantryControllerMock(AbstractGantryController):

    def __init__(self):

        threading.Thread.__init__(self)
        # State of axes in millimeters
        self.point = {"x": 0, "y": 0, "z": 0}

        self.des_point = {"x": 0, "y": 0, "z": 0}

        self.gantry = GantryMock()

        self.mode = 0
        self.mutex = threading.Lock()

    def run(self):
        print("GantryController thread initialized..")
        while True:
            self.mutex.acquire()
            if self.mode == 1: # set pos
                self.gantry.set_gantry_absolute_pos(self.des_point)
                self.mode = 0
            self.mutex.release()


    def get_current_gantry_pos(self):
        self.gantry.get_gantry_pos()

    def send_gantry_absolute_pos(self, in_point):
        for axis in self.des_point:
            self.des_point[axis] = in_point[axis]

        self.gantry.set_gantry_absolute_pos(in_point)

    def send_gantry_distance(self, x, y, z):
        pass

    def send_coordinate(self, x, y):
        pass





