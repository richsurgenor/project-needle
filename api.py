# Interfaces for image processing/gantry

from abc import abstractmethod
import time
import threading
from serial import Serial
import os

import justin_python.prostick_lib as iv
from sklearn.cluster import KMeans
import numpy as np

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

    def apply_clahe(self, image):
        return iv.apply_clahe(image, 5.0, (8, 8))

    def apply_thresholding(self, clahe_img):
        """
        Apply thresholding and CLAHE to the input image
        :param image: input image
        :return: preprocessed image
        """
        mask = iv.create_mask(clahe_img, 100, 255)
        threshold = int(255 * 0.5)
        adapt_mean_th = iv.adapt_thresh(clahe_img, 255, threshold, 20)
        masked = iv.apply_mask(adapt_mean_th, mask)
        masked = masked.astype(np.uint8) # ??? numpy.where changes the dtype..
        return masked

    def get_optimum_points(self, image):
        pic_array_1, pic_array_2 = iv.process_image(image, 0.5, True)
        # Run the K-Means algorithm to get 50 centers
        kmeans = KMeans(n_clusters=25)
        kmeans.fit(pic_array_1)
        centers = kmeans.cluster_centers_
        kmeans2 = KMeans(n_clusters=25)
        kmeans2.fit(pic_array_2)
        centers2 = kmeans2.cluster_centers_
        centers = np.concatenate((centers, centers2), axis=0)
        return centers

    def get_final_selection(self, centers):
        return iv.final_selection(centers)


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

        import queue
        self.gantry_buffer = queue.SimpleQueue() # msgs to gantry
        self.pi_buffer = queue.SimpleQueue() # msgs to pi

    def run(self):
        print("GantryMock thread initialized..")
        self.initialize_gantry()

        while True:
            # blocks.. allows us to use a normal thread instead of Event
            line = self.gantry_buffer.get()
            req = chr(line[0])
            if req == REQ_ECHO_MSG:
                self.send_cmd(CMD_STATUS_MSG, line[1:].decode())
            elif req == REQ_MOVE_STEPPER:
                pass
            elif req == REQ_MOVE_Y_HOME:
                pass
            else:
                print("Unknown command passed to mock gantry interface..")

    def initialize_gantry(self):
        time.sleep(1)
        self.send_cmd(CMD_STATUS_MSG, "Gantry is initialized...")
        time.sleep(1)
        self.send_cmd(CMD_GANTRY_INITIALIZED)

    def send_cmd(self, cmd, msg=''):
        if len(msg) > 0:
            mymsg = bytearray(msg, 'ascii')
            mymsg = cmd + mymsg
        else:
            mymsg = cmd
        self.write_pi(mymsg)

    def is_open(self):
        return True

    #def simulate(self):
    #
    #    pass

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

    """
    For now just combine the serial interface and the gantry for mock..
    """
    def readline(self):
        return self.pi_buffer.get()

    def write(self, msg):
        self.gantry_buffer.put(msg)

    def write_pi(self, msg):
        self.pi_buffer.put(msg)

    def inWaiting(self):
        return self.pi_buffer.qsize()

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

    @abstractmethod
    def send_msg(self, cmd, msg=""):
        """
        :param cmd: cmd as python string
        :param msg: msg to be echoed back from arduino
        :return:
        """
        msg = cmd + msg
        self.gantry.write(msg.encode('ascii'))

# Requests from Pi
REQ_ECHO_MSG = '0'
REQ_POSITION_UPDATE = '1'
REQ_MOVE_Y_HOME = '2'
REQ_MOVE_STEPPER = '3'
REQ_GO_TO_WORK = '4'
REQ_RESET = '9'

# Commands to Pi
CMD_STATUS_MSG = b'0'
CMD_GANTRY_INITIALIZED = b'1'
CMD_POSITION_UPDATE = b'2'
CMD_WAIT_COORDINATE = b'8'
CMD_FINISH = b'9'

class GantryController(AbstractGantryController):

    def __init__(self, mocked=0):
        threading.Thread.__init__(self) # TODO: add thread events..
        # State of axes in millimeters
        self.point = {"x": 0, "y": 0, "z": 0}
        self.des_point = {"x": 0, "y": 0, "z": 0}

        self.coordinate_request = False
        self.msg = 'No status available.'

        print("initializing serial interface..")

        if mocked:
            self.gantry = GantryMock()
            self.gantry.start()
        else:
            self.gantry = Serial(SERIAL_INTERFACE, BAUD_RATE)
        print("connected to serial interface..")

        self.stopped = False

    def run(self):
        print("started gantry controller thread...")
        while not self.stopped:
            line = self.gantry.readline()
            line = line.rstrip()
            if len(line) > 0: # for some reason a newline character is by itself after readline
                cmd = line[0:1]

                if cmd == CMD_GANTRY_INITIALIZED:
                    self.msg = 'Moving Y Home...'
                    self.send_msg(REQ_MOVE_Y_HOME)
                elif cmd == CMD_STATUS_MSG:
                    msg = line[1:].decode('ascii')
                    print(msg)
                    self.msg = msg
                elif cmd == CMD_WAIT_COORDINATE:
                    print("Received request for coordinate...");
                    self.coordinate_request = True
                elif cmd == CMD_POSITION_UPDATE:
                    print("Received position update...")

        print("gantry thread ended...")

                    #print(line)

    def get_current_gantry_pos(self):
        pass

    def send_gantry_absolute_pos(self, x, y, z):
        pass

    def send_gantry_distance(self, x, y, z):
        pass

    def stop(self):
        self.stopped = True

    def send_coordinate(self, x, y):
        print("sending coordinate...")
        self.gantry.write("hi".encode('ascii'))
        pass

    def send_msg(self, cmd, msg="", encode=True):
        msg = cmd + msg
        if encode:
            msg = msg.encode('ascii')
        else:
            # only encode command
            cmd_enc = cmd.encode('ascii')
            msg = cmd_enc + msg
        self.gantry.write(msg)





