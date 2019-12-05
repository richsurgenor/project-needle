# Interfaces for image processing/gantry

from abc import abstractmethod
import time
import threading
from serial import Serial
import os
import cv2

import image_processing.prostick_lib as iv
from sklearn.cluster import KMeans
import numpy as np
from common import is_numpy_array_avail
import platform

if not platform.uname()[0] == 'Windows':
    USING_WINDOWS = False
    USING_PI = os.uname()[4][:3] == 'arm'
else:
    USING_WINDOWS = True
    USING_PI = False

X_AXIS = 0
Y_AXIS = 1
Z_AXIS = 2
SCREW_LEAD_X = 2
SCREW_LEAD_Y = 8
SCREW_LEAD_Z = 8
STEPS_PER_REVOLUTION = 200

class AbstractProcessor:

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


class Processor(AbstractProcessor):
    """
    Effectively a state tracker for the image-processing. Provides an interface between the GUI and the
    image processing libraries.
    """

    def __init__(self, camera_width, camera_height, clip_rails_numpy=False):
        self.img_in = None
        #horizontal = cv2.imread('assets/coord_static_x_revised.png', 0)
        #vertical = cv2.imread('assets/coord_static_y.png', 0)
        horizontal = cv2.imread('assets/grid_ver_smol_revised.jpg', 0)
        vertical = cv2.imread('assets/grid_hor_smol_revised.jpg', 0)
        self.grid_horizontal, self.grid_vertical = iv.initialize_grids((camera_height, camera_width), horizontal,
                                                                       vertical)
        #self.grid_horizontal = cv2.resize(self.grid_horizontal, (camera_width, camera_height))
        #self.grid_vertical = cv2.resize(self.grid_vertical, (camera_width, camera_height))

        #save grids debug
        #cv2.imwrite('gui-gridhorizontal.jpg', self.grid_horizontal)
        #cv2.imwrite('gui-gridvertical.jpg', self.grid_vertical)

        self.centers = None
        self.selection = None
        self.clip_rails_numpy = clip_rails_numpy

        my_x = self.mm_to_steps(X_AXIS, 21.75)
        my_y = self.mm_to_steps(Y_AXIS, 12)
        my_z = self.mm_to_steps(Z_AXIS, 10)

        print("x: {} y: {} z: {}".format(my_x, my_y, my_z))

    def apply_clahe(self, image):
        self.img_in = image
        return iv.apply_clahe(self.img_in, 7.0, (40, 40))

    def apply_thresholding(self, clahe_img):
        """
        Apply thresholding and CLAHE to the input image
        :param image: input image
        :return: preprocessed image
        """
        mask = iv.create_mask(self.img_in, 100, 255)
        threshold = int(255 * 0.5)
        low = iv.adapt_thresh(clahe_img, 255, threshold, 15)
        high = iv.adapt_thresh(clahe_img, 255, threshold, 20)  # we are creating a bandpass filter here
        masked_low = iv.apply_mask(low, mask)
        masked_high = iv.apply_mask(high, mask)
        masked_img = masked_low - np.logical_and(masked_low, masked_high)
        masked = masked_img.astype(np.uint8)
        return masked

    def get_optimum_points(self, preprocessed_img):
        self.centers = iv.get_centers(preprocessed_img, 40, self.grid_vertical, True, self.clip_rails_numpy)
        return self.centers

    def get_final_selection(self, size, centers):
        self.selection = iv.final_selection(centers, size, True)
        return self.selection

    def get_injection_site_relative_to_point(self, **kwargs):
        #needle_xy_pixel = iv.isolate_needle(self.img_in, self.grid_vertical)
        if 'index' not in kwargs:
            pt = iv.get_position(self.centers[self.selection], self.grid_horizontal, self.grid_vertical)
        else:
            pt = iv.get_position(self.centers[kwargs['index']], self.grid_horizontal, self.grid_vertical)
        mypt = [pt[1], pt[0]]
        return mypt

    def get_correction_relative_to_point(self):
        needle_xy_pixel = iv.isolate_needle(self.img_in, self.grid_vertical)
        pt = iv.compare_points(self.centers[self.selection], needle_xy_pixel, self.grid_horizontal, self.grid_vertical)
        # TODO: why to get this to work we had to flip the axes and offset the x by 10 :)
        realpt = [pt[1]-10, pt[0]]
        return realpt

    def mm_to_steps(self, axis, distance):
        if axis == X_AXIS:
            screw_lead_axis = SCREW_LEAD_X
        elif axis == Y_AXIS:
            screw_lead_axis = SCREW_LEAD_Y
        elif axis == Z_AXIS:
            screw_lead_axis = SCREW_LEAD_Z;

        totalSteps = float(STEPS_PER_REVOLUTION) * (1 / float(screw_lead_axis) * (float(distance)))
        return int(round(totalSteps))

    def get_injection_site_in_steps_relative_to_point(self, injection_site_in_mm):
        x_steps = self.mm_to_steps(X_AXIS, injection_site_in_mm[0]) - 2225 # gantry overextends bc capacitive sensor
        y_steps = self.mm_to_steps(Y_AXIS, injection_site_in_mm[1]) + 237 # marker a little further out
        return [x_steps, y_steps]

def get_direction(current, target):
    if current - target < 0:
        return 1
    else:
        return -1

STEPS_TO_Y_HOME = 3875 # 155mm
NEEDLE_X_PROJ_STEPS = 2175
NEEDLE_Y_PROJ_STEPS = 300
NEEDLE_Z_PROJ_STEPS = 250
NEEDLE_Z_INSERTION_DEPTH = 250
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
            elif req == REQ_GO_TO_WORK:
                #self.y_go_to_home()
                #time.sleep(2)
                self.move_cap_to_il()
                time.sleep(5)
                self.position_needle()
                time.sleep(3)
                self.inject_needle()
                time.sleep(5)
                self.pull_needle()
                time.sleep(3)
                self.move_back_from_il()
                self.send_cmd(CMD_STATUS_MSG, "Sequence complete!")
                #self.send_cmd(CMD_POSITION_UPDATE, "00")
            elif req == REQ_WAIT_COORDINATE:
                self.des_point['x'] = int(line[1:5].decode())
                self.des_point['y'] = int(line[5:9].decode())
                print("Coordinate received by GantryMock!")
                print(line)
            else:
                print("Unknown command passed to mock gantry interface..")

    def y_go_to_home(self):
        self.send_cmd(CMD_STATUS_MSG, "Moving to home position...")
        for i in range(0, STEPS_TO_Y_HOME):
            self.send_cmd(CMD_POSITION_UPDATE, "10")
            time.sleep(0.001)

    def move_cap_to_il(self):
        #self.send_cmd(CMD_STATUS_MSG, "Moving to insertion location...")
        for i in range(0, self.des_point['x']):
            self.send_cmd(CMD_POSITION_UPDATE, "00")
            time.sleep(0.001)
        self.send_cmd(CMD_STATUS_MSG, "Moving Y to IL...")
        for i in range(0, self.des_point['y']):
            self.send_cmd(CMD_POSITION_UPDATE, "10")
            time.sleep(0.001)
        self.send_cmd(CMD_STATUS_MSG, "Moving Z to IL...")
        # lets say 1500 steps
        for i in range(0, 1500):
            self.send_cmd(CMD_POSITION_UPDATE, "20")
            time.sleep(0.001)

    def move_back_from_il(self):
        self.send_cmd(CMD_STATUS_MSG, "Moving Z back from IL...")
        # lets say 1500 steps
        for i in range(0, 1500-NEEDLE_Z_PROJ_STEPS+NEEDLE_Z_INSERTION_DEPTH):
            self.send_cmd(CMD_POSITION_UPDATE, "21")
            time.sleep(0.001)
        self.send_cmd(CMD_STATUS_MSG, "Moving X back from IL...")
        for i in range(0, self.des_point['x'] + NEEDLE_X_PROJ_STEPS):
            self.send_cmd(CMD_POSITION_UPDATE, "01")
            time.sleep(0.001)
        self.send_cmd(CMD_STATUS_MSG, "Moving Y back from IL...")
        for i in range(0, self.des_point['y'] + STEPS_TO_Y_HOME - NEEDLE_Y_PROJ_STEPS):
            self.send_cmd(CMD_POSITION_UPDATE, "11")
            time.sleep(0.001)

    def position_needle(self):
        self.send_cmd(CMD_STATUS_MSG, "Positioning needle...")
        for i in range(0, NEEDLE_Z_PROJ_STEPS):
            self.send_cmd(CMD_POSITION_UPDATE, "21")
            time.sleep(0.001)
        for i in range(0, NEEDLE_Y_PROJ_STEPS):
            self.send_cmd(CMD_POSITION_UPDATE, "11")
            time.sleep(0.001)
        for i in range(0, NEEDLE_X_PROJ_STEPS):
            self.send_cmd(CMD_POSITION_UPDATE, "00")
            time.sleep(0.001)

    def inject_needle(self):
        #todo: move only needle tip instead of entire model
        self.send_cmd(CMD_STATUS_MSG, "Injecting needle...")
        for i in range(0, NEEDLE_Z_INSERTION_DEPTH):
            self.send_cmd(CMD_POSITION_UPDATE, "20")
            time.sleep(0.001)

    def pull_needle(self):
        #todo: move only needle tip instead of entire model
        self.send_cmd(CMD_STATUS_MSG, "Pulling needle...")
        for i in range(0, NEEDLE_Z_INSERTION_DEPTH):
            self.send_cmd(CMD_POSITION_UPDATE, "21")
            time.sleep(0.001)

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

    def close(self):
        print("Closing GantryMock!!")

if USING_PI:
    SERIAL_INTERFACE = '/dev/ttyACM0'
elif USING_WINDOWS:
    SERIAL_INTERFACE = 'COM3'
else: #using mac?
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
REQ_WAIT_COORDINATE = '5'
REQ_RESET = '9'

# Commands to Pi
CMD_STATUS_MSG = b'0'
CMD_GANTRY_INITIALIZED = b'1'
CMD_POSITION_UPDATE = b'2'
CMD_COORDINATE_RECEIVED = b'7'
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
        self.coordinate = None
        self.gfx_widget = None

    def run(self):
        print("started gantry controller thread...")
        while not self.stopped:
            line = self.gantry.readline()
            line = line.rstrip()
            if len(line) > 0: # for some reason a newline character is by itself after readline
                cmd = line[0:1]

                if cmd == CMD_GANTRY_INITIALIZED:
                    #self.msg = 'Moving Y Home...'
                    # self.send_msg(REQ_MOVE_Y_HOME)'
                    print("Arduino told gantry controller (gui) that it is initialized...")
                elif cmd == CMD_STATUS_MSG:
                    msg = line[1:].decode('ascii')
                    print("Gantry: " + msg)
                    self.msg = msg
                elif cmd == CMD_WAIT_COORDINATE:
                    """
                    print("Received request for coordinate...");
                    self.coordinate_request = True
                    if self.coordinate:
                        self.send_coordinate(self.coordinate[0], self.coordinate[1])
                        print("Send coordinate to gantry. x: {} y: {}".format(self.coordinate[0], self.coordinate[1]))
                    else:
                        print("Coordinate was requested but we had no coordinate ready...")
                    """
                    pass
                elif cmd == CMD_POSITION_UPDATE:
                    #print("Received position update!")
                    axis = int(chr(line[1]))
                    dir = int(chr(line[2]))
                    self.gfx_widget.move_needle(axis, dir)
                    pass
                    #print("Received position update...")
                elif cmd == CMD_COORDINATE_RECEIVED:
                    print("Arduino received coordinates sent.")
                    print("Pending gantry start...")

        print("gantry thread ended...")

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
        x_str = str(int(round(x))).rjust(4, '0')
        y_str = str(int(round(y))).rjust(4, '0')
        self.send_msg(REQ_WAIT_COORDINATE, x_str + y_str)
        pass

    """
    def send_msg(self, cmd, msg="", encode=True):
        msg = cmd + msg
        if encode:
            msg = msg.encode('ascii')
        else:
            # only encode command
            cmd_enc = cmd.encode('ascii')
            msg = cmd_enc + msg + "\n"
        self.gantry.write(msg)
        """

    def send_msg(self, req, msg='', encode=True):
        #TODO: add cond encode
        if len(msg) > 0:
            mymsg = str(req) + msg + '\n'
            mymsg = mymsg.encode('ascii')
            #mymsg = req + mymsg
        else:
            myreq = req + '\n'
            mymsg = str(myreq).encode('ascii')

        self.gantry.write(mymsg)





