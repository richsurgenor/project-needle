"""
Project Needle
Auburn  University
Senior Design |  Fall 2019

Team Members:
Andrea Walker, Rich Surgenor, Jackson Solley, Jacob Hagewood,
Justin Sutherland, Laura Grace Ayers.
"""

# GUI for Project Needle, mainly allowing the user to view ideal points for needle insertion to veins.

from PyQt5.QtCore import Qt, QCoreApplication, QSize, QThread, QFile, QTextStream, QPoint
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QPainter, QImage, QColor, QKeySequence, QSurfaceFormat, QOpenGLVertexArrayObject
import numpy
import cv2
import sys
import api
import time
import os
import forwarding_server
from common import log_image
from traceback import print_tb
import platform
from OpenGL import GL
from OpenGL.GL import shaders
#from OpenGL.raw.GL.ARB.vertex_array_object import glGenVertexArrays, \
#                                                  glBindVertexArray
#from OpenGL.raw.GL.ARB.vertex_buffer_object import *
from OpenGL.raw.GL.APPLE.vertex_array_object import *
from OpenGL import GLU
from math import pow, sqrt, asin, pi

import common
from objloader import OBJ

if not platform.uname()[0] == 'Windows':
    USING_PI = os.uname()[4][:3] == 'arm'
else:
    USING_PI = False

###############
# Non-Settings:
AUTOMATIC = 0
SEMIAUTOMATIC = 1
MANUAL = 2
###############

# Settings
DEFAULT_MODE = AUTOMATIC
BORDER_SIZE = 10
HALF_BORDER_SIZE = BORDER_SIZE/2
FPS = 10

STILL_IMAGE_CAPTURE = 0 # broken, don't use.

"""
To see how much clipping when CLIP_RAILS_THROUGH_NUMPY see prostick_lib.py

Allows cropping what the selection algo sees without cropping the actual picture.
disadvantage: isn't done before preprocessing..
"""


if USING_PI:
    from pivideostream import PiVideoStream

    LOGGING = 1
    DARK_THEME = 1
    SAVE_RAWIMG = 1                  # Save image after capture

    GANTRY_ON = 1                    # Control Gantry on/off for normal/mock modes
    MOCK_MODE_IMAGE_PROCESSING = 0   # Fake image processing but still run everything else
    MOCK_MODE_GANTRY = 1             # Fake Gantry connection but still run everything else

    CAMERA_RESOLUTION_WIDTH = 1920
    CAMERA_RESOLUTION_HEIGHT = 1080

    CROPPING_ENABLED = 1
    CROPPED_RESOLUTION_WIDTH = 1080
    CROPPED_RESOLUTION_HEIGHT = 1080

    GUI_IMAGE_SIZE_WIDTH = 540  # 640
    GUI_IMAGE_SIZE_HEIGHT = 540  # 368

    CLIP_RAILS_THROUGH_NUMPY = False

else:
    DARK_THEME = 0
    SAVE_RAWIMG = 0
    LOGGING = 0

    GANTRY_ON = 1
    MOCK_MODE_IMAGE_PROCESSING = 0
    MOCK_MODE_GANTRY = 1

    CAMERA_RESOLUTION_WIDTH = 1280
    CAMERA_RESOLUTION_HEIGHT = 720

    CROPPING_ENABLED = 0
    CROPPED_RESOLUTION_WIDTH = 1000
    CROPPED_RESOLUTION_HEIGHT = 720

    GUI_IMAGE_SIZE_WIDTH = 640
    GUI_IMAGE_SIZE_HEIGHT = 360

    CLIP_RAILS_THROUGH_NUMPY = False

def set_forwarding_settings():
    global CAMERA_RESOLUTION_WIDTH,CAMERA_RESOLUTION_HEIGHT, \
    GUI_IMAGE_SIZE_WIDTH,GUI_IMAGE_SIZE_HEIGHT,CROPPING_ENABLED, \
    CROPPED_RESOLUTION_WIDTH,CROPPED_RESOLUTION_HEIGHT,SCALE_FACTOR, \
    LOGGING, SAVE_RAWIMG, GANTRY_ON, MOCK_MODE_GANTRY, MOCK_MODE_IMAGE_PROCESSING, \
    CLIP_RAILS_THROUGH_NUMPY

    LOGGING = 1

    GANTRY_ON = 1
    MOCK_MODE_IMAGE_PROCESSING = 0
    MOCK_MODE_GANTRY = 1

    SAVE_RAWIMG = 1

    """
    Note that on a full size 3280x2464 img that the gantry rails are approx:
    min_x = min_x + 760
    max_x = max_x - 1020
    
    So approx crop would be: 1500x2464
    
    """

    CAMERA_RESOLUTION_WIDTH = 1000 #3280#
    CAMERA_RESOLUTION_HEIGHT = 1000 #2464#
    #GUI_IMAGE_SIZE_WIDTH = CAMERA_RESOLUTION_WIDTH/4
    #GUI_IMAGE_SIZE_HEIGHT = CAMERA_RESOLUTION_HEIGHT/4

    # one problem with cropping height is we only want to crop the max y
    # TODO: make cropping with y only for max_y (so bottom isnt cropped)
    CROPPING_ENABLED = 0
    CROPPED_RESOLUTION_WIDTH = 840 #1500
    CROPPED_RESOLUTION_HEIGHT = 1000 # clip height because uneven distribution of light

    if not CROPPING_ENABLED:
        factor = 4
        GUI_IMAGE_SIZE_WIDTH = CAMERA_RESOLUTION_WIDTH / factor
        GUI_IMAGE_SIZE_HEIGHT = CAMERA_RESOLUTION_HEIGHT / factor
    else:
        factor = 2
        GUI_IMAGE_SIZE_WIDTH = CROPPED_RESOLUTION_WIDTH / factor
        GUI_IMAGE_SIZE_HEIGHT = CROPPED_RESOLUTION_HEIGHT / factor

    CLIP_RAILS_THROUGH_NUMPY = True

FAKE_INPUT_IMG = 1
if FAKE_INPUT_IMG:
    FAKE_INPUT_IMG_NAME = "./test_images/rich.jpg"
    CAMERA_RESOLUTION_WIDTH = 1000#3280
    CAMERA_RESOLUTION_HEIGHT = 1000#2464
    GUI_IMAGE_SIZE_WIDTH = 500 #550  # 640
    GUI_IMAGE_SIZE_HEIGHT = 500  # 368
    CROPPING_ENABLED = 0
    CROPPED_RESOLUTION_WIDTH = 2200
    CROPPED_RESOLUTION_HEIGHT = 2464
    CLIP_RAILS_THROUGH_NUMPY=False

def ui_main(fwd=False):
    """
    Initialize main UI
    :return: None
    """
    global FORWARDING
    FORWARDING = fwd
    if fwd:
        set_forwarding_settings()
    app = QApplication(sys.argv)
    if DARK_THEME:
        file = QFile("./assets/dark.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())
    ui = MainWindow()
    sys.exit(app.exec_())

def _createCntrBtn(*args):
    l = QHBoxLayout()
    for arg in args:
        l.setSpacing(30)
        l.setAlignment(arg, Qt.AlignCenter)
        #l.addStretch()
        l.addWidget(arg)
    #l.addStretch()
    return l

def get_effective_image_height():
    if CROPPING_ENABLED:
        return CROPPED_RESOLUTION_HEIGHT
    else:
        return CAMERA_RESOLUTION_HEIGHT

def get_effective_image_width():
    if CROPPING_ENABLED:
        return CROPPED_RESOLUTION_WIDTH
    else:
        return CAMERA_RESOLUTION_WIDTH

def get_processor():
    if MOCK_MODE_IMAGE_PROCESSING:
        return api.ProcessorMock()
    else:
        if CROPPING_ENABLED:
            return api.Processor(CROPPED_RESOLUTION_WIDTH, CROPPED_RESOLUTION_HEIGHT, clip_rails_numpy=CLIP_RAILS_THROUGH_NUMPY)
        else:
            return api.Processor(CAMERA_RESOLUTION_WIDTH, CAMERA_RESOLUTION_HEIGHT, clip_rails_numpy=CLIP_RAILS_THROUGH_NUMPY)

def get_controller():
    if MOCK_MODE_GANTRY:
        return api.GantryControllerMock()
    else:
        return api.GantryController()

class FakeCamera:
    def __init__(self):
        self.rawframe = cv2.imread(FAKE_INPUT_IMG_NAME, 1)
        # self.rawframe = cv2.resize(self.rawframe, dsize=(GUI_IMAGE_SIZE_WIDTH, GUI_IMAGE_SIZE_HEIGHT), interpolation=cv2.INTER_CUBIC)
        # cv2.imwrite('testproc.jpg', self.rawframe)
        self.opened = False
        #self.fakepic = cv2.cvtColor(self.rawframe, cv2.COLOR_RGB2BGR)

    def get_frame(self):
        return self.rawframe

    def start(self):
        self.opened = True

    def stop(self):
        pass

class Camera:
    def __init__(self, camera_num):
        self.cap = None
        self.camera_num = camera_num
        self.opened = False

    def start(self):
        self.cap = cv2.VideoCapture(self.camera_num)
        self.set_resolution(CAMERA_RESOLUTION_WIDTH, CAMERA_RESOLUTION_HEIGHT)
        self.opened = True

    def is_open(self):
        return self.opened

    def set_brightness(self, value):
        pass

    def set_resolution(self, width, height):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def get_frame(self, rbg2rgb=False):
        ret, frame = self.cap.read()
        if rbg2rgb:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    def stop(self):
        self.cap.release()

    def __str__(self):
        return 'OpenCV Camera {}'.format(self.camera_num)


class StatusThread(QThread):
    """
    Thread maintaining status assets, because if main thread is halted qt will be nonoperational.
    """

    def __init__(self, gantry_status, processing_status):
        super().__init__()
        self.gantry_status = gantry_status
        self.processing_status = processing_status
        if GANTRY_ON:
            self.gc = api.GantryController(MOCK_MODE_GANTRY)
            self.gc.start()
        self.msleep(100)
        #self.gc.send_msg(api.REQ_ECHO_MSG, "Connected to Arduino!")

    def run(self):
        while True:
            if self.gc:
                self.gantry_status.showMessage("Gantry:   " + self.gc.msg)
                self.msleep(1000)

        """
        self.status.showMessage("STATUS: Connecting to Gantry..")

        self.status.showMessage("STATUS: Gantry going home..")
        self.gc.mutex.acquire()
        self.gc.mode = 1
        self.gc.mutex.release()

        while not self.gc.gantry.is_home():
            pass

        self.status.showMessage("STATUS: Gantry is Home..")
        self.msleep(1000)
        self.status.showMessage("STATUS: Waiting for user input..")
        # self.gc.send_gantry_home()
        """



class PreviewThread(QThread):
    """
    Thread for the input image.
    """
    def __init__(self, camera, video_frame):
        super().__init__()
        self.camera = camera
        self.video_frame = video_frame
        self.rawframe = None
        self.inputbox = video_frame

    def next_frame_slot(self):
        self.rawframe = self.camera.get_frame()

        # Sometimes the first few frame are null, so we will ignore them.
        if self.rawframe is None:
            return

        if CROPPING_ENABLED:
            self.rawframe = common.cropND(self.rawframe, (CROPPED_RESOLUTION_HEIGHT, CROPPED_RESOLUTION_WIDTH))

        #savemat('data.mat', {'frame': frame, 'framee': framee})
        #img = cv2.resize(self.rawframe, (GUI_IMAGE_SIZE_WIDTH, GUI_IMAGE_SIZE_HEIGHT))
        rawframe_conv = cv2.cvtColor(self.rawframe, cv2.COLOR_BGR2RGB)
        img = QImage(numpy.asarray(rawframe_conv, order='C'), rawframe_conv.shape[1], rawframe_conv.shape[0], QImage.Format_RGB888)

        pix = QPixmap.fromImage(img)

        pix = pix.scaled(GUI_IMAGE_SIZE_WIDTH,GUI_IMAGE_SIZE_HEIGHT, Qt.IgnoreAspectRatio)
        #self.video_frame.setPixmap(pix)

        self.video_frame.img = pix
        self.video_frame.start()
        self.video_frame.update() # rather than repaint bc flicker

    def run(self):
        while True:
            self.next_frame_slot()
            time_slept = int((float(1)/FPS) * 1000)
            self.msleep(time_slept) # TODO: make this settable
            qApp.processEvents()


class QImageBox(QGroupBox):

    def __init__(self, text):
        super(QGroupBox, self).__init__(text)
        #self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

class QProcessedImageGroupBox(QGroupBox):
    def __init__(self, parent, text, img):
        super(QGroupBox, self).__init__(text)
        self.parent = parent
        self._layout = QVBoxLayout()
        self._layout.setSpacing(0)
        self.setLayout(self._layout)
        self.img = img

        self.image_label = QImageLabel("", img)
        self.display_coords = QLabel("Coordinates(pixels): ")
        self.display_injection_site_label = QLabel("Injection Site(mm): \nInjection Site(steps): ")
        self.display_coords.setStyleSheet("font-weight: bold; color: red");
        self.display_injection_site_label.setStyleSheet("font-weight: bold; color: red");

        self._layout.addWidget(self.image_label)
        self._layout.addWidget(self.display_coords)
        self._layout.addWidget(self.display_injection_site_label)

        self.points = None

        # Configure mouse press on processed image widget
        self.image_label.mousePressEvent = self.get_pos
        #self.image_label.connect(self, pyqtSignal("clicked()"), self.getPos)

    def get_layout(self):
        return self._layout

    def update_image(self, img):
        self.image_label.img = img

    def reset(self):
        self.image_label.set_status(False)
        self.image_label.img = None

    def get_pos(self, event):
        # TODO: Reverse scaling to get closet coordinates...

        if not self.image_label.img:
            print('User tried to click point before any existed.')
            return

        selected_x = event.pos().x() - HALF_BORDER_SIZE - 5
        selected_y = event.pos().y() - HALF_BORDER_SIZE - 5
        mode = self.parent.get_active_mode()
        if mode == MANUAL:
            # because the top-left corner of the blue reticle is where it actually starts painting,
            # and we want our point that will be converted to mm to be as accurate as possible..
            actual_selected_x = selected_x + 5
            actual_selected_y = selected_y + 5
            # now we scale points up instead... :) at a loss of accuracy :(
            factor_x = float(CAMERA_RESOLUTION_WIDTH) / GUI_IMAGE_SIZE_WIDTH
            factor_y = float(CAMERA_RESOLUTION_HEIGHT) / GUI_IMAGE_SIZE_HEIGHT

            scaled_x = int(round(factor_x * actual_selected_x))
            scaled_y = int(round(factor_y * actual_selected_y))

            self.points = [(int(selected_x), int(selected_y))]
            self.parent.processor.centers = [(scaled_x, scaled_y)]
            chosen = 0 # only one point...
            self.parent.draw_processed_img_with_pts(self.parent.masked_img, self.points, chosen)
            self.image_label.repaint()
            self.parent.display_coordinates(self.parent.output_box.points[chosen][0],
                                            self.parent.output_box.points[chosen][1])
            self.parent.process_point(index=chosen)
        else:

            best_x = 10000
            best_y = 10000
            chosen = -1
            # check closest point

            for i in range(0, len(self.points)):
                point = self.points[i]
                x,y = point

                diff_x = abs(selected_x - x)
                diff_y = abs(selected_y - y)
                diff_sum = diff_x + diff_y
                if diff_sum < best_x+best_y:
                    best_x = diff_x
                    best_y = diff_y
                    #print("diff_x: " + str(selected_x - x) + " diff_y: " + str(selected_y - y))
                    chosen = i
            #print("best_x: " + str(best_x) + " best_y: " + str(best_y))
            self.parent.draw_processed_img_with_pts(self.image_label.img, self.points, chosen)
            self.parent.display_coordinates(self.parent.output_box.points[chosen][0],
                                            self.parent.output_box.points[chosen][1])
            self.parent.process_point(index=chosen)


class QImageLabel(QLabel):
    def __init__(self, _, img):
        super(QLabel, self).__init__(_)
        self.setFrameShape(QFrame.Panel)
        #self.setFrameStyle("background-color: rgb(255, 255, 255")
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(3)
        self.setMidLineWidth(3)
        #self.mousePressEvent = self.getPos
        self.img = img
        self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.done = False

    def set_status(self, status):
        self.done = status
        self.repaint()

    def paintEvent(self, e):
        QLabel.paintEvent(self, e)
        p = QPainter(self)

        if self.done:
            p.drawPixmap(QPoint(HALF_BORDER_SIZE, HALF_BORDER_SIZE), self.img)
        #print(self.img.size())

    def sizeHint(self):
        return QSize(GUI_IMAGE_SIZE_WIDTH + BORDER_SIZE, GUI_IMAGE_SIZE_HEIGHT + BORDER_SIZE)


class QInputBox(QLabel):
    def __init__(self, _, img):
        super(QLabel, self).__init__(_)
        self.setFrameShape(QFrame.Panel)
        #self.setFrameStyle("background-color: rgb(255, 255, 255")
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(3)
        self.setMidLineWidth(3)
        #self.mousePressEvent = self.getPos
        self.img = img
        self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.started = False

    def set_status(self, status):
        pass

    def paintEvent(self, e):
        QLabel.paintEvent(self, e)
        p = QPainter(self)

        if self.started:
            p.drawPixmap(QPoint(HALF_BORDER_SIZE, HALF_BORDER_SIZE), self.img)
        #print(self.img.size())

    def start(self):
        self.started = True

    def sizeHint(self):
        return QSize(GUI_IMAGE_SIZE_WIDTH + BORDER_SIZE, GUI_IMAGE_SIZE_HEIGHT + BORDER_SIZE)

class QModeMenuWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__()
        self.titles = ["Automatic Mode", "Semiautomatic Mode", "Manual Mode"]
        self.checkboxes = []
        self.checkboxes_layout = QHBoxLayout()
        self.group = QButtonGroup()
        self.parent = parent

        self.current = 0

        for i in range(0, len(self.titles)):
            title = self.titles[i]
            checkbox = QCheckBox(title)
            checkbox.setCheckState(Qt.Unchecked)
            self.checkboxes.append(checkbox)
            self.group.addButton(checkbox, i)
            self.checkboxes_layout.addWidget(self.checkboxes[i])

        self.checkboxes[DEFAULT_MODE].setCheckState(Qt.Checked)
        self.group.buttonClicked.connect(self.mode_change_event)

        self.checkboxes_layout.setAlignment(Qt.AlignLeft)
        self.checkboxes_layout.setSpacing(30)
        self.setLayout(self.checkboxes_layout)

    def mode_change_event(self, button):
        self.parent.output_box.reset()
        self.parent.gantry_status.showMessage("Gantry:   ")
        self.parent.processing_status.showMessage("Processing:   ")
        pass


class MainWindow(QMainWindow):
    """
    Main window for application.
    """

    def __init__(self):
        super(QMainWindow, self).__init__()
        #self.resize(1200, 800)

        self.camera = None

        if FAKE_INPUT_IMG:
            self.camera = FakeCamera()
        else:
            if USING_PI:
                self.camera = PiVideoStream(resolution=(CAMERA_RESOLUTION_WIDTH, CAMERA_RESOLUTION_HEIGHT))
            else:
                if FORWARDING:
                    self.camera = forwarding_server.ForwardingCamera()
                else:
                    self.camera = Camera(0)

            self.camera.start()


        self.processor = get_processor()
        self.wid = QWidget(self)
        self.setCentralWidget(self.wid)
        self.setWindowTitle('Project Needle')
        self._layout = QBoxLayout(QBoxLayout.TopToBottom, self.wid)
        self._layout.setSpacing(0)
        self.wid.setLayout(self._layout)

        self.gantry_status = QStatusBar()
        self._layout.addWidget(self.gantry_status)
        self.processing_status = QStatusBar()
        self._layout.addWidget(self.processing_status)

        self.checkbox_widget = QModeMenuWidget(self)
        self._layout.addWidget(self.checkbox_widget)

        #self._layout.addWidget(self.centralWidget)
        self.pic_widget = QImageBox("Image View")
        self.pics_hbox = QHBoxLayout(self.pic_widget)
        self.pics_hbox.setAlignment(Qt.AlignHCenter)
        self.pics_hbox.setSpacing(10)
        self.pic_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.video_frame = QInputBox("", None)
        self.input_box = QGroupBox("Input Image") #QImageGroupBox("Input Image", self.video_frame)
        self.input_box_status = QLabel("Change Camera: ")

        input_box_layout = QVBoxLayout()
        self.input_box.setLayout(input_box_layout)

        input_box_layout.addWidget(self.video_frame)
        input_box_layout.addWidget(self.input_box_status)
        self.pics_hbox.addWidget(self.input_box) #(self.lb)
        self.feed = PreviewThread(self.camera, self.video_frame)
        self.feed.start()

        # Init thread that manages Gantry...
        self.status_thread = StatusThread(self.gantry_status, self.processing_status)
        self.status_thread.start()
        self.gc = self.status_thread.gc

        self.output_box = QProcessedImageGroupBox(self, "Processed Image", None)
        self.pics_hbox.addWidget(self.output_box)
        self._layout.addWidget(self.pic_widget)

        # buttons
        btn_process_img = QPushButton("Capture Image")
        btn_process_img.clicked.connect(self.process_image_event)
        btn_gantry_start = QPushButton("Start Gantry")
        btn_gantry_start.clicked.connect(self.gantry_start_event)
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset_event)
        btn_calibrate = QPushButton("Calibrate")
        btn_calibrate.clicked.connect(self.calibrate_event)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close_event)
        btn_settings = QPushButton("Settings")
        btn_settings.clicked.connect(self.settings_event)
        btn_debug_cmds = QPushButton("Debug Cmds")
        btn_debug_cmds.clicked.connect(self.debug_cmds_event)


        self.btn_widget = QWidget()
        btn_panel = _createCntrBtn(btn_debug_cmds, btn_settings, btn_reset, btn_calibrate, btn_close)
        self.btn_widget.setLayout(btn_panel)
        self._layout.addWidget(self.btn_widget)

        self.btn_widget2 = QWidget()
        btn_panel2 = _createCntrBtn(btn_process_img, btn_gantry_start)
        self.btn_widget2.setLayout(btn_panel2)
        self._layout.addWidget(self.btn_widget2)

        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.show()

        self.gfx_thread = GraphicsThread(self)
        self.gfx_thread.start()
        self.gc.gfx_thread = self.gfx_thread


    def get_active_mode(self):
        return self.checkbox_widget.group.checkedId() # will correspond to modes

    def display_coordinates(self, x, y):
        self.output_box.display_coords.setText("Coordinates(pixels): x: " + str(x) + " y: " + str(y))
        self.output_box.display_coords.repaint()

    def display_injection_site(self, x, y, x_steps, y_steps):
        self.output_box.display_injection_site_label.setText("Injection Site(mm): x: {0:.2f} away. y: {0:.2f} down.".format(x, y) \
                + "\nInjection Site(steps): x: " + str(x_steps) + " away. y: " + str(y_steps) + " down.")
        self.output_box.display_injection_site_label.repaint()

    def clear_coordinates(self):
        self.output_box.display_coords.setText("Coordinates(pixels): ")
        self.output_box.display_coords.repaint()

    def clear_injection_site(self):
        self.output_box.display_injection_site_label.setText("Injection Site(mm): \nInjection Site(steps): ")
        self.output_box.display_injection_site_label.repaint()

    #class ProcessingThread(QThread): TODO: do we need this?

    def draw_output_img(self, img):
        result = QPixmap(img.width(), img.height())
        painter = QPainter(result)
        # Paint final images on result
        painter.drawPixmap(0, 0, img)
        painter.end()
        self.output_box.update_image(result)
        self.output_box.image_label.set_status(True)

    def draw_processed_img_with_pts(self, processed_img_scaled, scaled_points, chosen):
        """
        :param processed_img_scaled: scaled version of image
        :param scaled_points: scaled points
        :param chosen: index of point chosen from list of scaled_points
        :return: currently None
        """
        # Create Overlay Img with Transparency
        overlay_img = QPixmap("assets/transp_bluedot.png") # transparent_reticle.png")
        overlay_alpha = QPixmap(overlay_img.size())
        overlay_alpha.fill(Qt.transparent)  # force alpha channel
        # Paint overlay_img onto overlay_alpha
        overlay_alpha_cpy = overlay_alpha.copy()
        painter = QPainter(overlay_alpha)
        painter.drawPixmap(0, 0, overlay_img)
        painter.end()

        painter = QPainter(overlay_alpha_cpy)
        mask = overlay_img.createMaskFromColor(Qt.transparent, Qt.MaskInColor)
        painter.setPen(QColor(0, 255, 0))
        painter.drawPixmap(overlay_alpha.rect(), mask, mask.rect())
        painter.end()

        # processed_img = QPixmap("image3_results_n1.jpg")
        overlay_scaled = overlay_alpha.scaled(10, 10, Qt.KeepAspectRatio)
        overlay_scaled_green = overlay_alpha_cpy.scaled(10, 10, Qt.KeepAspectRatio)
        result = QPixmap(processed_img_scaled.width(), processed_img_scaled.height())
        result.fill(Qt.transparent)  # force alpha channel
        painter = QPainter(result)
        # Paint final images on result
        painter.drawPixmap(0, 0, processed_img_scaled)
        for i in range(0, len(scaled_points)):
            point = scaled_points[i]
            if i == chosen:
                #x += 31
                #y += 35
                painter.drawPixmap(point[0], point[1], overlay_scaled_green)
            else:
                painter.drawPixmap(point[0], point[1], overlay_scaled)
        painter.end()
        self.output_box.points = scaled_points
        self.output_box.update_image(result)
        self.output_box.image_label.set_status(True)

    def process_point(self, **kwargs):
        success = 0
        try:
            if 'index' in kwargs:
                injection_site_in_mm = self.processor.get_injection_site_relative_to_point(index=kwargs['index'])
            else:
                injection_site_in_mm = self.processor.get_injection_site_relative_to_point()
            success = 1
        except IndexError as e:
            # This occurs sometimes.. usually during slice_grid from spookylib...
            print("{} : {}".format(type(e), e))
            print_tb(e.__traceback__)
            QMessageBox.information(None, 'Error 1', 'Getting injection site in mm failed.', QMessageBox.Ok)
            if LOGGING and 'index' not in kwargs: # only log if in automatic mode...
                log_image(self.processor.img_in, "error_1_num")
        except Exception as e:
            print("=====Unknown Error getting injection site...=====")
            print("{} : {}".format(type(e), e))
            print_tb(e.__traceback__)
            if LOGGING and 'index' not in kwargs:
                log_image(self.processor.img_in, "error_site_unk_num")

        if success:
            print("Coordinate in mm: x: {} y: {}".format(injection_site_in_mm[0], injection_site_in_mm[1]))
            self.gc.coordinate = self.processor.get_injection_site_in_steps_relative_to_point(injection_site_in_mm)
            # send coordinate
            self.gc.send_coordinate(self.gc.coordinate[0], self.gc.coordinate[1])
            self.display_injection_site(injection_site_in_mm[0], injection_site_in_mm[1], self.gc.coordinate[0],
                                        self.gc.coordinate[1])
            QCoreApplication.processEvents()

    """
    Events
    """

    def process_image_event(self):
        """
        Receive processed image and use the received points to display a final image.
        :return: None
        """

        #TODO: redo this whole function
        print("Processing...")
        # clear old
        self.clear_coordinates()
        self.clear_injection_site()
        self.output_box.points = None
        self.processor.centers = None
        self.processor.selection = None

        if STILL_IMAGE_CAPTURE: # should only be on if picamera
            raw = self.camera.capture_still_image()
        else:
            raw = self.feed.rawframe
        # curious enough cvting to correct colors seems to throw off pts
        #if not USING_PI and not FORWARDING:
        #raw = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
        #if SAVE_RAWIMG:
        cv2.imwrite('gui-rawimg.jpg', raw)
        height, width, channels = raw.shape
        bytes_per_line = width * 3
        q_img = QImage(raw.copy().data, width, height, bytes_per_line, QImage.Format_RGB888)
        processed_img = QPixmap.fromImage(q_img)
        processed_img_scaled = processed_img.scaled(GUI_IMAGE_SIZE_WIDTH, GUI_IMAGE_SIZE_HEIGHT, Qt.IgnoreAspectRatio)
        self.draw_output_img(processed_img_scaled)
        QCoreApplication.processEvents()
        self.processing_status.showMessage("Processing:   Applying thresholding...")
        #grayimg = cv2.imread("justin_python/justin4.jpg", 0)
        grayimg = cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY) # TODO: may need to be different per camera
        clahe_img = self.processor.apply_clahe(grayimg)
        # we gray now...
        height, width = clahe_img.shape
        bytes_per_line = width
        q_img = QImage(clahe_img.copy().data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        processed_img = QPixmap.fromImage(q_img)

        processed_img_scaled = processed_img.scaled(GUI_IMAGE_SIZE_WIDTH, GUI_IMAGE_SIZE_HEIGHT, Qt.IgnoreAspectRatio)
        #scaled_points = [(x / SCALE_FACTOR, y / SCALE_FACTOR) for x, y in points]
        self.draw_output_img(processed_img_scaled)

        self.output_box.repaint()
        QCoreApplication.processEvents()
        self.processing_status.showMessage("Processing:   Applying mask...")
        QThread.msleep(1000)
        thresholding_img = self.processor.apply_thresholding(clahe_img)
        height, width = thresholding_img.shape
        bytes_per_line = width
        q_img = QImage(thresholding_img.copy().data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        processed_img = QPixmap.fromImage(q_img)
        processed_img_scaled = processed_img.scaled(GUI_IMAGE_SIZE_WIDTH, GUI_IMAGE_SIZE_HEIGHT, Qt.IgnoreAspectRatio)
        self.masked_img = processed_img_scaled.copy()
        self.draw_output_img(processed_img_scaled)
        if self.get_active_mode() == MANUAL:
            self.processing_status.showMessage("Processing:   Mask complete! You can now manually select a point...")
            return
        self.processing_status.showMessage("Processing:   Calculating optimal points...")
        QCoreApplication.processEvents()
        #QThread.msleep(1000)
        try:
            centers = self.processor.get_optimum_points(thresholding_img)
        except Exception as e:
            print("=====Unknown Error getting centers..=====")
            print("{} : {}".format(type(e), e))
            print_tb(e.__traceback__)
            if LOGGING:
                log_image(self.processor.img_in, "error_3_centers_num")
            return # we failed...

        #numpy.savetxt('test2.txt', centers, fmt='%d')
        points = numpy.copy(centers)

        scalex = float(get_effective_image_width()) / GUI_IMAGE_SIZE_WIDTH
        scaley = float(get_effective_image_height()) / GUI_IMAGE_SIZE_HEIGHT
        #scalex = int(scalex)
        #scaley = int(scaley)

        for point in points:
            point[0] = round(point[0] / scalex)
            point[1] = round(point[1] / scaley)
            point[0] = point[0] + HALF_BORDER_SIZE - 5
            point[1] = point[1] + HALF_BORDER_SIZE - 5

        self.output_box.points = points
        self.draw_processed_img_with_pts(processed_img_scaled, points, -1)
        if self.get_active_mode() == AUTOMATIC:
            self.processing_status.showMessage("Processing:   Searching for final selection...")
            QCoreApplication.processEvents()
            #QThread.msleep(2000)
            final_selection = self.processor.get_final_selection(numpy.shape(raw), centers)
            if final_selection:
                self.display_coordinates(self.output_box.points[final_selection][0],self.output_box.points[final_selection][1]) # TODO what if no coordinate...
                self.draw_processed_img_with_pts(processed_img_scaled, points, final_selection)
                self.processing_status.showMessage("Processing:   Final selection complete...")
                self.process_point()
            else:
                QMessageBox.information(None, 'Error 2', 'No final selection was returned.', QMessageBox.Ok)
                if LOGGING:
                    log_image(self.processor.img_in, "error_2_num")
        else:
            self.processing_status.showMessage("Processing:   Optimal points found!")

    def gantry_start_event(self):
        self.gantry_status.showMessage("Starting Gantry...")
        self.gc.send_msg(api.REQ_GO_TO_WORK)

    def reset_event(self):
        self.gc.send_msg(api.REQ_RESET)
        self.status_thread.gc.stop()
        del self.status_thread.gc
        self.status_thread.gc = None
        time.sleep(1) # not okay probably
        self.status_thread.gc = api.GantryController(MOCK_MODE_GANTRY)
        self.status_thread.gc.start()
        #self.output_box.image_label.set_status(False)
        # TODO: actually make this reset the entire state of the GUI

    def calibrate_event(self):
        QMessageBox.information(None, 'Calibration', 'pretty sure this is a meme now.', QMessageBox.Ok)
        # TODO: deem if this is a necessary functionality or if we will keep it in arduino code

    def close_event(self):
        self.camera.stop()
        #if self.
        gc = self.status_thread.gc
        if gc.gantry:
            if gc.gantry.is_open:
                self.status_thread.gc.gantry.close()
                print("closed serial interface..")
        time.sleep(1)
        qApp.exit()

    def settings_event(self):
        pass

    def debug_cmds_event(self):
        for i in range(0, 8000):
            self.gfx_thread.move_needle(2, 0)
        pass

    # verticies = (
    #     (4, -8, -12),
    #     (4, 8, -12),
    #     (-4, 8, -12),
    #     (-4, -8, -12),
    #     (4, -8, 12),
    #     (4, 8, 12),
    #     (-4, -8, 12),
    #     (-4, 8, 12)
    # )

# in mm
STARTING_CAMERA_HEIGHT=100
STARTING_CAMERA_DISTANCE=400 #900
GANTRY_WIDTH = 108.0 #152.0

BOX_HEIGHT = 140.0
GANTRY_HEIGHT = 60.0

GANTRY_DEPTH = 265 #673.0

# Make each unit 1mm
# Guessing gantry "box" is around 1ft x 2ft x 3ft ~ 1ft=300mm
verticies = (
    (GANTRY_WIDTH, -(BOX_HEIGHT+GANTRY_HEIGHT), -GANTRY_DEPTH),
    (GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), -GANTRY_DEPTH),
    (-GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), -GANTRY_DEPTH),
    (-GANTRY_WIDTH, -(BOX_HEIGHT+GANTRY_HEIGHT), -GANTRY_DEPTH),
    (GANTRY_WIDTH, -(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH),
    (GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH),
    (-GANTRY_WIDTH, -(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH),
    (-GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH)
)

verticies = numpy.hstack(verticies).reshape(-1,3).astype(numpy.float32)

# def define_color_buffer_data(width, height, depth):
#     vertices = [] # every 3 points is 1 vertex
#     for i in range(0, 12): # 12 triangles
#         vertices.append()
#         pass
#     pass


vertex_buffer_data = [
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH, # red face
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,

    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH, # green face
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,

    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH, # blue face
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,

    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH, # yellow face
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    
    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH, # light blue face
    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT),-GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,

    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH, # pink face
    -GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    -GANTRY_WIDTH, (BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH,
    GANTRY_WIDTH,-(BOX_HEIGHT+GANTRY_HEIGHT), GANTRY_DEPTH]

vertex_buffer_data = numpy.array(vertex_buffer_data, dtype=numpy.float32)

def define_color_buffer_data(colors):
    vertices = [] # every 3 points is 1 vertex
    for i in range(0, 12): # 12 triangles
        vertices.append()
        pass
    pass

color_buffer_data = [
    1.0, 0, 0,
    1.0, 0, 0,
    1.0, 0, 0,
    1.0, 0, 0,
    1.0, 0, 0,
    1.0, 0, 0,

    0, 1.0, 0,
    0, 1.0, 0,
    0, 1.0, 0,
    0, 1.0, 0,
    0, 1.0, 0,
    0, 1.0, 0,

    0, 0, 1.0,
    0, 0, 1.0,
    0, 0, 1.0,
    0, 0, 1.0,
    0, 0, 1.0,
    0, 0, 1.0,

    1.0, 1.0, 0,
    1.0, 1.0, 0,
    1.0, 1.0, 0,
    1.0, 1.0, 0,
    1.0, 1.0, 0,
    1.0, 1.0, 0,
    
    0, 0.7, 1.0,
    0, 0.7, 1.0,
    0, 0.7, 1.0,
    0, 0.7, 1.0,
    0, 0.7, 1.0,
    0, 0.7, 1.0,
    
    1.0, 0, 1.0,
    1.0, 0, 1.0,
    1.0, 0, 1.0,
    1.0, 0, 1.0,
    1.0, 0, 1.0,
    1.0, 0, 1.0]

# color_buffer_data = [
#     0.583,  0.771,  0.014,
#     0.609,  0.115,  0.436,
#     0.327,  0.483,  0.844,
#     0.822,  0.569,  0.201,
#     0.435,  0.602,  0.223,
#     0.310,  0.747,  0.185,
#     0.597,  0.770,  0.761,
#     0.559,  0.436,  0.730,
#     0.359,  0.583,  0.152,
#     0.483,  0.596,  0.789,
#     0.559,  0.861,  0.639,
#     0.195,  0.548,  0.859,
#     0.014,  0.184,  0.576,
#     0.771,  0.328,  0.970,
#     0.406,  0.615,  0.116,
#     0.676,  0.977,  0.133,
#     0.971,  0.572,  0.833,
#     0.140,  0.616,  0.489,
#     0.997,  0.513,  0.064,
#     0.945,  0.719,  0.592,
#     0.543,  0.021,  0.978,
#     0.279,  0.317,  0.505,
#     0.167,  0.620,  0.077,
#     0.347,  0.857,  0.137,
#     0.055,  0.953,  0.042,
#     0.714,  0.505,  0.345,
#     0.783,  0.290,  0.734,
#     0.722,  0.645,  0.174,
#     0.302,  0.455,  0.848,
#     0.225,  0.587,  0.040,
#     0.517,  0.713,  0.338,
#     0.053,  0.959,  0.120,
#     0.393,  0.621,  0.362,
#     0.673,  0.211,  0.457,
#     0.820,  0.883,  0.371,
#     0.982,  0.099,  0.879]

color_buffer_data = numpy.array(color_buffer_data, dtype=numpy.float32)

small_verticies = (
    (1, -1, -1),
    (1, 1, -1),
    (-1, 1, -1),
    (-1, -1, -1),
    (1, -1, 1),
    (1, 1, 1),
    (-1, -1, 1),
    (-1, 1, 1)
)

edges = (
    (0, 1),
    (0, 3),
    (0, 4),
    (2, 1),
    (2, 3),
    (2, 7),
    (6, 3),
    (6, 4),
    (6, 7),
    (5, 1),
    (5, 4),
    (5, 7)
)

# void main() {
#     gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
# }
VERTEX_SHADER = '''
#version 120

attribute vec3 a_position;
attribute vec3 a_color;

varying vec3 in_color;

void main() {
  gl_Position = gl_ModelViewProjectionMatrix * vec4(a_position.xyz, 1);
  in_color = a_color;
}
'''

# void main()
# {
#   gl_FragColor = vec4(1.0, 1.0, 0.0, 1.0);
# }
FRAGMENT_SHADER = '''
#version 120

varying vec3 in_color;

void main() {
  gl_FragColor = vec4(in_color, 0.4);
}
'''

def Cube():
    GL.glBegin(GL.GL_LINES)
    for edge in edges:
        for vertex in edge:
            GL.glVertex3fv(verticies[vertex])
    GL.glEnd()


def SmallCube():
    GL.glBegin(GL.GL_LINES)
    for edge in edges:
        for vertex in edge:
            GL.glVertex3fv(small_verticies[vertex])
    GL.glEnd()

X_MM_PER_STEP = 0.01
Y_MM_PER_STEP = 0.04
Z_MM_PER_STEP = 0.04
FORWARD = 0
BACKWARD = 1

class GraphicsThread(QThread):
    """
    Thread for graphics rendering.
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.window = GfxWindow(self, self.parent)

        self.needle_counter = 0

        # QLayout
        print("window opened....")

        #for i in range(0, 3875):
        #    self.move_needle(1, 0)
            #self.msleep(1)

    #X_AXIS = 0
    #Y_AXIS = 1
    #Z_AXIS = 2
    # define FORWARD 0
    # define BACKWARD 1

    def move_needle(self, axis, dir):
        if axis == 0: # x axis
            gfx_axis = 0
            amt = X_MM_PER_STEP
            if dir == BACKWARD:
                amt = -1 * amt
        elif axis == 1:
            gfx_axis = 2
            amt = Y_MM_PER_STEP
            if dir == BACKWARD: # fwd for z axis is actually going down on gantry
                amt = -1 * amt
        elif axis == 2:
            gfx_axis = 1
            amt = Z_MM_PER_STEP
            if dir == FORWARD:
                amt = -1 * amt

        self.window.gfx_widget.needle_position[gfx_axis] = self.window.gfx_widget.needle_position[gfx_axis] + amt
        self.needle_counter = self.needle_counter + 1
        if self.needle_counter == 100:
            self.window.gfx_widget.update()
            qApp.processEvents()
            self.needle_counter = 0


class GfxWindow(QDialog):

    def __init__(self, parent, main):
        super().__init__()

        self.parent = parent
        self.main = main
        self.resize(600, 600)

        self.gfx_widget = OpenGLWidget(self, self.parent)

        format = QSurfaceFormat()
        format.setDepthBufferSize(24);
        format.setStencilBufferSize(8);
        format.setVersion(2, 1);
        #format.setProfile(QSurfaceFormat.CoreProfile);
        #self.gfx_widget.setFormat(format)

        down = QShortcut(Qt.Key_Down, self, self.gfx_widget.changePerspective)
        up = QShortcut(Qt.Key_Up, self, self.gfx_widget.changePerspective2)
        right = QShortcut(Qt.Key_Right, self, self.gfx_widget.changePerspective3)
        left = QShortcut(Qt.Key_Left, self, self.gfx_widget.changePerspective4)

        self.move(self.main.window().x() - 600, self.main.window().y() + 400)
        self.setWindowTitle("GFX View")

        self.show()
        QCoreApplication.processEvents()

        self.i = 1

        #self.gfx_widget.moveCube()

    #def keyPressEvent(self, eventQKeyEvent):
    #    eventQKeyEvent.
    #    print("hi")

    def mousePressEvent(self, event):
        pos = event.pos()
        #print("pressed. coords: {}".format(pos))
        self.setMouseTracking(True)

        # Convert window coordinates to cartesian
        self.old_x = float(event.pos().x() - GFX_WINDOW_WIDTH/2)
        self.old_y = float(GFX_WINDOW_HEIGHT/2 - event.pos().y())

        val = float((GFX_WINDOW_WIDTH/2)*(GFX_WINDOW_HEIGHT/2)-pow(self.old_x, 2)-pow(self.old_y, 2))
        try:
            self.old_z = sqrt(val)
        except:
            self.setMouseTracking(False)
            pass
        #print("complete..")

    def mouseReleaseEvent(self, event):
        pos = event.pos()
        #print("released. coords: {}".format(pos))
        self.setMouseTracking(False)

    def mouseMoveEvent(self, event):
        #print("coords: {}".format(event.pos()))
        pos = event.pos()
        self.new_x = float(pos.x() - GFX_WINDOW_WIDTH / 2)
        self.new_y = float(GFX_WINDOW_HEIGHT / 2 - pos.y())
        try:
            self.new_z = float(
                sqrt(( (GFX_WINDOW_WIDTH / 2) * (GFX_WINDOW_HEIGHT / 2) ) - pow(self.new_x, 2) - pow(self.new_y, 2)))
        except:
            return
        # cross products of 2 vectors
        ux = self.new_y * self.old_z - self.new_z * self.old_y
        uy = self.new_z * self.old_x - self.new_x * self.old_z
        uz = self.new_x * self.old_y - self.new_y * self.old_x

        # new (cross) old = |new||old|sin(angle)
        self.gfx_widget.angle = asin(
            sqrt(pow(ux, 2) + pow(uy, 2) + pow(uz, 2)) / ( (GFX_WINDOW_WIDTH/2) * (GFX_WINDOW_HEIGHT/2) )) * (180 / pi)

        #print("this is angle: {}".format(self.gfx_widget.angle))
        self.gfx_widget.ux = ux
        self.gfx_widget.uy = uy
        self.gfx_widget.uz = uz

        # set rotation to trigger
        self.gfx_widget.rotation = True
        self.gfx_widget.update()

        # update old for next rotation... otherwise we will be using the original old pos over and over
        self.old_x = self.new_x
        self.old_y = self.new_y
        self.old_z = self.new_z

GFX_WINDOW_WIDTH=600
GFX_WINDOW_HEIGHT=600

class OpenGLWidget(QOpenGLWidget):

    def __init__(self, window, parent):
        super(QOpenGLWidget, self).__init__(window)
        self.window = window
        self.parent = parent
        self.i = 0
        self.z = 800.0
        self.zoom = 120
        self.change = False
        self.rotation = False
        self.CT = None
        self.needle_position = [-GANTRY_WIDTH, GANTRY_HEIGHT, -GANTRY_DEPTH+40]

    def initializeGL(self):

        # not valid in 2.x core profile...
        #self.vao = glGenVertexArrays(1)
        #GL.glBindVertexArray(self.vao)


        """
        self.vao = QOpenGLVertexArrayObject()
        if not self.vao.create():
            print("error creating")
            return

        self.vao.bind()
        """

        # works for apple ;) todo: learn more about VAOs
        #vao = GL.GLuint()
        #glGenVertexArraysAPPLE(1, vao)
        #glBindVertexArrayAPPLE(vao)

        #self.vs = shaders.compileShader(VERTEX_SHADER, GL.GL_VERTEX_SHADER)

        #self.fs = shaders.compileShader(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)
        #self.shader = shaders.compileProgram(self.vs, self.fs)

        self.program = GL.glCreateProgram()
        vertex = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        fragment = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)

        # Set shaders source
        GL.glShaderSource(vertex, VERTEX_SHADER)
        GL.glShaderSource(fragment, FRAGMENT_SHADER)

        # Compile shaders
        GL.glCompileShader(vertex)
        if not GL.glGetShaderiv(vertex, GL.GL_COMPILE_STATUS):
            error = GL.glGetShaderInfoLog(vertex).decode()
            print("Vertex shader compilation error: {}".format(error))

        GL.glCompileShader(fragment)
        if not GL.glGetShaderiv(fragment, GL.GL_COMPILE_STATUS):
            error = GL.glGetShaderInfoLog(fragment).decode()
            print(error)
            raise RuntimeError("Fragment shader compilation error")

        GL.glAttachShader(self.program, vertex)
        GL.glAttachShader(self.program, fragment)
        GL.glLinkProgram(self.program)

        if not GL.glGetProgramiv(self.program, GL.GL_LINK_STATUS):
            print(GL.glGetProgramInfoLog(self.program))
            raise RuntimeError('Linking error')

        GL.glDetachShader(self.program, vertex)
        GL.glDetachShader(self.program, fragment)

        self.vertexBuffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertexBuffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertex_buffer_data.nbytes, vertex_buffer_data, GL.GL_STATIC_DRAW)

        self.colorBuffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.colorBuffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, color_buffer_data.nbytes, color_buffer_data, GL.GL_STATIC_DRAW)

        # vs = shaders.compileShader(VERTEX_SHADER, GL.GL_VERTEX_SHADER)
        # fs = shaders.compileShader(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

        #GL.glViewport(0, 0, GFX_WINDOW_WIDTH, GFX_WINDOW_HEIGHT)

        #GL.glMatrixMode(GL.GL_MODELVIEW)
        #GL.glLoadIdentity()
        GL.glClearColor(0.0, 1.0, 1.0, 0.0)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(120, (GFX_WINDOW_WIDTH / GFX_WINDOW_HEIGHT), 1, 4000.0)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GLU.gluLookAt(0, STARTING_CAMERA_HEIGHT, STARTING_CAMERA_DISTANCE, 0, 0, 0, 0, 1, 0)
        #GL.glTranslatef(0.0, 0.0, -20)

        #GL.glRotatef(20, 3, 1, 1)

        # need glortho?
        GL.glMatrixMode(GL.GL_MODELVIEW)
        #GL.glLoadIdentity()

        self.ux = None
        self.uy = None
        self.uz = None
        self.angle = None
        self.CT = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
        self.obj = OBJ("assets/syringe.obj", swapyz=True)

        #GL.glEnable(GL.GL_DEPTH_TEST);
        #GL.glDepthFunc(GL.GL_LESS);

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA);

        pass

    def moveCube(self):
        for x in range(0, 300):
            self.i = self.i - 1
            self.update()
            self.parent.msleep(10)
            qApp.processEvents()

    def paintGL(self):
            # glRotatef(1, 3, 1, 1)
            #GLU.gluPerspective(90, (800 / 600), 0.1, 50.0)

            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()

            GLU.gluPerspective(self.zoom, (GFX_WINDOW_WIDTH / GFX_WINDOW_HEIGHT), 1, 4000.0)
            GL.glMatrixMode(GL.GL_MODELVIEW)

            if self.rotation:
                #GL.glMatrixMode(GL.GL_MODEL_VIEW)
                GL.glLoadMatrixf(self.CT)
                GL.glRotatef(self.angle, self.ux, self.uy, 0)
                self.CT = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
                self.rotation=False
                pass

            #if self.change:
            GL.glLoadMatrixf(self.CT)
            #GLU.gluLookAt(0, 0, self.z, 0, 0, 0, 0, 1, 0)
            self.change = False
            #GL.glMatrixMode(GL.GL_PROJECTION)
            #GL.glTranslatef(0.0, 0.0, -20)
            #GL.glRotatef(20, 3, 1, 1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            GL.glColor3d(0, 0, 0)

            GL.glPushMatrix()
            GL.glTranslatef(self.needle_position[0], self.needle_position[1], self.needle_position[2])
            GL.glScalef(20, 20, 20)
            GL.glRotatef(180, 0, 0, 0)
            GL.glCallList(self.obj.gl_list)
            GL.glPopMatrix()

            GL.glUseProgram(self.program)

            GL.glEnableVertexAttribArray(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.colorBuffer)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

            GL.glEnableVertexAttribArray(0)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertexBuffer)
            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 36)
            GL.glDisableVertexAttribArray(0)
            GL.glDisableVertexAttribArray(1)

            GL.glUseProgram(0)

            Cube()

            # GL.glPushMatrix()
            # GL.glTranslatef(self.i * 0.01, self.i * 0.01, 0)
            # SmallCube()
            # GL.glPopMatrix()

        #GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)

    def changePerspective(self):
        self.z = self.z - 1.5
        self.change = True
        self.update()

    def changePerspective2(self):
        self.z = self.z + 1.5
        self.change = True
        self.update()

    def changePerspective3(self):
        self.zoom = self.zoom + 1
        self.update()

    def changePerspective4(self):
        self.zoom = self.zoom - 1
        self.update()

    def sizeHint(self):
        return QSize(GFX_WINDOW_WIDTH, GFX_WINDOW_HEIGHT)