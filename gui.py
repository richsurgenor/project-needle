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
from PyQt5.QtGui import QPixmap, QPainter, QImage, QColor, QStandardItemModel
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

import common

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
    SCALE_FACTOR = 2  # TODO: scale factor could be auto-calced..

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
    SCALE_FACTOR = 2  # TODO: scale factor could be auto-calced..

def set_forwarding_settings():
    global CAMERA_RESOLUTION_WIDTH,CAMERA_RESOLUTION_HEIGHT, \
    GUI_IMAGE_SIZE_WIDTH,GUI_IMAGE_SIZE_HEIGHT,CROPPING_ENABLED, \
    CROPPED_RESOLUTION_WIDTH,CROPPED_RESOLUTION_HEIGHT,SCALE_FACTOR, \
    LOGGING, SAVE_RAWIMG, GANTRY_ON, MOCK_MODE_GANTRY, MOCK_MODE_IMAGE_PROCESSING

    LOGGING = 1

    GANTRY_ON = 1
    MOCK_MODE_IMAGE_PROCESSING = 0
    MOCK_MODE_GANTRY = 0

    SAVE_RAWIMG = 1
    CAMERA_RESOLUTION_WIDTH = 1000
    CAMERA_RESOLUTION_HEIGHT = 1000
    GUI_IMAGE_SIZE_WIDTH = CAMERA_RESOLUTION_WIDTH/2
    GUI_IMAGE_SIZE_HEIGHT = CAMERA_RESOLUTION_HEIGHT/2
    CROPPING_ENABLED = 0
    CROPPED_RESOLUTION_WIDTH = 1000
    CROPPED_RESOLUTION_HEIGHT = 1000
    SCALE_FACTOR = 2

FAKE_INPUT_IMG = 0
if FAKE_INPUT_IMG:
    FAKE_INPUT_IMG_NAME = "./justin_python/justin4.jpg"
    CAMERA_RESOLUTION_WIDTH = 3280
    CAMERA_RESOLUTION_HEIGHT = 2464
    GUI_IMAGE_SIZE_WIDTH = 820 #550  # 640
    GUI_IMAGE_SIZE_HEIGHT = 616  # 368
    CROPPING_ENABLED = 0
    CROPPED_RESOLUTION_WIDTH = 2200
    CROPPED_RESOLUTION_HEIGHT = 2464
    SCALE_FACTOR = 4

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
            return api.Processor(CROPPED_RESOLUTION_WIDTH, CROPPED_RESOLUTION_HEIGHT)
        else:
            return api.Processor(CAMERA_RESOLUTION_WIDTH, CAMERA_RESOLUTION_HEIGHT)

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
        self.fakepic = cv2.cvtColor(self.rawframe, cv2.COLOR_RGB2BGR)

    def get_frame(self):
        return self.fakepic

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

    def get_frame(self, rbg2rgb=True):
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
        img = QImage(numpy.asarray(self.rawframe, order='C'), self.rawframe.shape[1], self.rawframe.shape[0], QImage.Format_RGB888)

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

        self.show()

    def get_active_mode(self):
        return self.checkbox_widget.group.checkedId() # will correspond to modes

    def display_coordinates(self, x, y):
        self.output_box.display_coords.setText("Coordinates(pixels): x: " + str(x) + " y: " + str(y))
        self.output_box.display_coords.repaint()

    def display_injection_site(self, x, y, x_steps, y_steps):
        self.output_box.display_injection_site_label.setText("Injection Site(mm): x: " + str(x) + " away. y: " + str(y) + " down." \
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

        raw = self.feed.rawframe
        raw = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
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
        #if CROPPING_ENABLED:
        #    raw = common.cropND(raw, (CROPPED_RESOLUTION_HEIGHT, CROPPED_RESOLUTION_WIDTH))
        #grayimg = cv2.imread("justin_python/justin4.jpg", 0)
        grayimg = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY) # TODO: may need to be different per camera
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
        #QThread.msleep(1000)
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
        self.gc.send_coordinate(self.gc.coordinate[0], self.gc.coordinate[1])

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
        pass
