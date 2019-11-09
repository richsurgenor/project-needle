"""
Project Needle
Auburn  University
Senior Design |  Fall 2019

Team Members:
Andrea Walker, Rich Surgenor, Jackson Solley, Jacob Hagewood,
Justin Sutherland, Laura Grace Ayers.
"""

# GUI for Project Needle, mainly allowing the user to view ideal points for needle insertion to veins.

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QThread, QFile, QTextStream, QPoint
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QPainter, QImage, QColor
import numpy
import cv2
import sys
import api
import time
import os
import forwarding_server
from scipy.io import savemat

import common

USING_PI = os.uname()[4][:3] == 'arm'
FORWARDING = False

if USING_PI:
    from pivideostream import PiVideoStream

    DARK_THEME = 1
    SAVE_RAWIMG = 0

    MOCK_MODE_IMAGE_PROCESSING = 1
    MOCK_MODE_GANTRY = 0

    CAMERA_RESOLUTION_WIDTH = 1920
    CAMERA_RESOLUTION_HEIGHT = 1080

    CROPPING_ENABLED = 1
    CROPPED_RESOLUTION_WIDTH = 1080
    CROPPED_RESOLUTION_HEIGHT = 1080

    IMAGE_SIZE_WIDTH = 540  # 640
    IMAGE_SIZE_HEIGHT = 540  # 368
    SCALE_FACTOR = 2  # TODO: scale factor could be auto-calced..
    BORDER_SIZE = 10

else:

    DARK_THEME = 0
    SAVE_RAWIMG = 0
    FAKE_INPUT_IMG = 1
    FAKE_INPUT_IMG_NAME = "./fake_images/fake1.jpg"

    MOCK_MODE_IMAGE_PROCESSING = 1
    MOCK_MODE_GANTRY = 1

    CAMERA_RESOLUTION_WIDTH = 1280
    CAMERA_RESOLUTION_HEIGHT = 720

    CROPPING_ENABLED = 1
    CROPPED_RESOLUTION_WIDTH = 1000
    CROPPED_RESOLUTION_HEIGHT = 720

    IMAGE_SIZE_WIDTH = 500  # 640
    IMAGE_SIZE_HEIGHT = 368  # 368
    SCALE_FACTOR = 2  # TODO: scale factor could be auto-calced..
    BORDER_SIZE = 10

FAKE_INPUT_IMG = 1
if FAKE_INPUT_IMG:
    FAKE_INPUT_IMG_NAME = "./fake_images/fake1.jpg"
    CAMERA_RESOLUTION_WIDTH = 3280
    CAMERA_RESOLUTION_HEIGHT = 2464
    IMAGE_SIZE_WIDTH = 820  # 640
    IMAGE_SIZE_HEIGHT = 616  # 368
    CROPPING_ENABLED = 0
    CROPPED_RESOLUTION_WIDTH = 1000
    CROPPED_RESOLUTION_HEIGHT = 720
    SCALE_FACTOR = 3


def ui_main(fwd=False):
    """
    Initialize main UI
    :return: None
    """
    app = QApplication(sys.argv)
    if DARK_THEME:
        file = QFile("./assets/dark.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())
    ui = MainWindow()
    sys.exit(app.exec_())

    global FORWARDING
    FORWARDING = fwd

def _createCntrBtn(*args):
    l = QHBoxLayout()
    for arg in args:
        l.addStretch()
        l.addWidget(arg)
    l.addStretch()
    return l

def get_processor(camera):
    if MOCK_MODE_IMAGE_PROCESSING:
        return api.ProcessorMock(camera)
    else:
        return api.Processor(camera)

def get_controller():
    if MOCK_MODE_GANTRY:
        return api.GantryControllerMock()
    else:
        return api.GantryController()

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

    def __init__(self, status):
        super().__init__()
        self.status = status
        self.gc = api.GantryController(MOCK_MODE_GANTRY)
        self.gc.start()
        self.msleep(100)
        #self.gc.send_msg(api.REQ_ECHO_MSG, "Connected to Arduino!")

    def run(self):
        while True:
            if self.gc:
                self.status.showMessage(self.gc.msg)
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

    def next_frame_slot(self):
        if FAKE_INPUT_IMG:
            frame = cv2.imread(FAKE_INPUT_IMG_NAME, 1)
            frame = cv2.resize(frame, dsize=(IMAGE_SIZE_WIDTH, IMAGE_SIZE_HEIGHT), interpolation=cv2.INTER_CUBIC)
            cv2.imwrite('testproc.jpg', frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame = self.camera.get_frame()

        # Sometimes the first few frame are null, so we will ignore them.
        if frame is None:
            return

        if CROPPING_ENABLED:
            frame = common.cropND(frame, (CROPPED_RESOLUTION_HEIGHT, CROPPED_RESOLUTION_WIDTH))
        #savemat('data.mat', {'frame': frame, 'framee': framee})
        img = QImage(numpy.asarray(frame, order='C'), frame.shape[1], frame.shape[0], QImage.Format_RGB888)
        pix = QPixmap.fromImage(img)
        #if not USING_PI:
        pix = pix.scaled(IMAGE_SIZE_WIDTH,IMAGE_SIZE_HEIGHT, Qt.IgnoreAspectRatio)
        self.video_frame.setPixmap(pix)

    def run(self):
        while True:
            self.next_frame_slot()
            self.msleep(200) # TODO: make this settable
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
        self.setLayout(self._layout)
        self.img = img

        self.image_label = QImageLabel("", img)
        self.display_coords = QLabel("Coordinates")
        self.display_coords.setStyleSheet("font-weight: bold; color: red");

        self._layout.addWidget(self.image_label)
        self._layout.addWidget(self.display_coords)

        self.points = None

        # Configure mouse press on processed image widget
        self.image_label.mousePressEvent = self.getPos
        #self.image_label.connect(self, pyqtSignal("clicked()"), self.getPos)

    def get_layout(self):
        return self._layout

    def getPos(self, event):
        # TODO: Reverse scaling to get closet coordinates...

        if not self.points:
            print('User tried to click point before any existed.')
            return

        selected_x = event.pos().x() - BORDER_SIZE/2
        selected_y = event.pos().y() - BORDER_SIZE/2

        best_x = 10000
        best_y = 10000
        chosen = -1
        # check closest point

        for i in range(0, len(self.points)):
            point = self.points[i]
            x,y = point
            # TODO: fix

            #estimated center of the reticle..
            x += 31
            y += 35

            diff_x = abs(selected_x - x)
            diff_y = abs(selected_x - y)
            diff_sum = diff_x + diff_y
            if diff_sum < best_x+best_y:
                best_x = diff_x
                best_y = diff_y
                print("diff_x: " + str(selected_x - x) + " diff_y: " + str(selected_y - y))
                chosen = i
        print("best_x: " + str(best_x) + " best_y: " + str(best_y))
        self.display_coords.setText("x: " + str(selected_x) + " y: " + str(selected_y))
        self.parent.draw_processed_img(self.image_label.img, self.points, chosen)


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
            p.drawPixmap(QPoint(BORDER_SIZE/2, BORDER_SIZE/2), self.img)
        #print(self.img.size())

    def sizeHint(self):
        return QSize(IMAGE_SIZE_WIDTH + BORDER_SIZE, IMAGE_SIZE_HEIGHT + BORDER_SIZE)

class MainWindow(QMainWindow):
    """
    Main window for application.
    """

    def __init__(self):
        super(QMainWindow, self).__init__()
        #self.resize(1200, 800)

        self.camera = None

        if not FAKE_INPUT_IMG:
            if USING_PI:
                self.camera = PiVideoStream(resolution=(CAMERA_RESOLUTION_WIDTH, CAMERA_RESOLUTION_HEIGHT))
            else:
                if FORWARDING:
                    self.camera = forwarding_server.ForwardingCamera()
                else:
                    self.camera = Camera(0)

            self.camera.start()


        self.processor = get_processor(self.camera)
        self.wid = QWidget(self)
        self.setCentralWidget(self.wid)
        self.setWindowTitle('Project Needle')
        self._layout = QBoxLayout(QBoxLayout.TopToBottom, self.wid)
        self._layout.setSpacing(0)
        self.wid.setLayout(self._layout)

        self.status = QStatusBar()
        self._layout.addWidget(self.status)

        self.checkbox_widget = QWidget()
        self.checkboxes_layout = QHBoxLayout()
        self.checkbox_widget.setLayout(self.checkboxes_layout)
        self.checkbox = QCheckBox("Automatic Mode")
        self.checkbox.setCheckState(Qt.Unchecked)
        self.checkbox2 = QCheckBox("Semiautomatic Mode")
        self.checkbox2.setCheckState(Qt.Checked)
        self.checkbox3 = QCheckBox("Manual Mode")
        self.checkbox3.setCheckState(Qt.Unchecked)
        #self.checkbox.initStyleOption
        self.checkboxes_layout.addWidget(self.checkbox)
        self.checkboxes_layout.addWidget(self.checkbox2)
        self.checkboxes_layout.addWidget(self.checkbox3)
        self._layout.addWidget(self.checkbox_widget)

        #self._layout.addWidget(self.centralWidget)
        self.pic_widget = QImageBox("Image View")
        self.pics_hbox = QHBoxLayout(self.pic_widget)
        self.pics_hbox.setAlignment(Qt.AlignHCenter);
        self.pics_hbox.setSpacing(10)
        self.pic_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.video_frame = QLabel()
        self.input_box = QGroupBox("Input Image") #QImageGroupBox("Input Image", self.video_frame)
        self.input_box_status = QLabel("Change Camera: ")

        input_box_layout = QVBoxLayout()
        self.input_box.setLayout(input_box_layout)

        input_box_layout.addWidget(self.video_frame)
        input_box_layout.addWidget(self.input_box_status)
        self.pics_hbox.addWidget(self.input_box) #(self.lb)
        self.feed = PreviewThread(self.camera, self.video_frame)
        self.feed.start()

        self.status_thread = StatusThread(self.status)
        self.status_thread.start()

        self.output_box = QProcessedImageGroupBox(self, "Processed Image", None)
        self.pics_hbox.addWidget(self.output_box)
        self._layout.addWidget(self.pic_widget)

        # buttons
        btn_process_img = QPushButton("Capture Image")
        btn_process_img.clicked.connect(self.process_image_event)
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
        btn_panel = _createCntrBtn(btn_process_img, btn_reset, btn_calibrate, btn_close)
        self.btn_widget.setLayout(btn_panel)
        self._layout.addWidget(self.btn_widget)

        self.btn_widget2 = QWidget()
        btn_panel2 = _createCntrBtn(btn_settings, btn_debug_cmds)
        self.btn_widget2.setLayout(btn_panel2)
        self._layout.addWidget(self.btn_widget2)

        self.show()


    """
    Events
    """
    def draw_processed_img(self, processed_img_scaled, scaled_points, chosen):
        """

        :param processed_img_scaled: scaled version of image
        :param scaled_points: scaled points
        :param chosen: index of point chosen from list of scaled_points
        :return: currently None
        """
        # Create Overlay Img with Transparency
        overlay_img = QPixmap("assets/transparent_reticle.png")
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
        overlay_scaled = overlay_alpha.scaled(55, 55, Qt.KeepAspectRatio)
        overlay_scaled_green = overlay_alpha_cpy.scaled(55, 55, Qt.KeepAspectRatio)
        result = QPixmap(processed_img_scaled.width(), processed_img_scaled.height())
        result.fill(Qt.transparent)  # force alpha channel
        painter = QPainter(result)
        # Paint final images on result
        painter.drawPixmap(0, 0, processed_img_scaled)
        for i in range(0, len(scaled_points)):
            point = scaled_points[i]
            if i == chosen:
                painter.drawPixmap(point[0] + BORDER_SIZE / 2, point[1] + BORDER_SIZE / 2, overlay_scaled_green)
            else:
                painter.drawPixmap(point[0] + BORDER_SIZE / 2, point[1] + BORDER_SIZE / 2, overlay_scaled)
        painter.end()
        self.output_box.points = scaled_points
        self.output_box.image_label.img = result
        self.output_box.image_label.set_status(True)

    def process_image_event(self):
        """
        Receive processed image and use the received points to display a final image.
        :return: None
        """
        print("Processing...")
        raw = self.camera.get_frame()
        if CROPPING_ENABLED:
            raw = common.cropND(raw, (CROPPED_RESOLUTION_HEIGHT, CROPPED_RESOLUTION_WIDTH))
        cv_img, points = self.processor.process_image(raw)
        cv_img_bgr = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
        height, width, channel = cv_img.shape
        bytes_per_line = 3 * width
        q_img = QImage(cv_img.copy().data, width, height, bytes_per_line, QImage.Format_RGB888)
        if SAVE_RAWIMG:
            cv2.imwrite('gui-rawimg.jpg', cv_img_bgr)
        processed_img = QPixmap.fromImage(q_img)
        processed_img_scaled = processed_img.scaled(IMAGE_SIZE_WIDTH, IMAGE_SIZE_HEIGHT, Qt.IgnoreAspectRatio)
        scaled_points = [(x / SCALE_FACTOR, y / SCALE_FACTOR) for x, y in points]
        self.draw_processed_img(processed_img_scaled, scaled_points, -1)

    def reset_event(self):
        self.status_thread.gc.send_msg(api.REQ_RESET)
        self.status_thread.gc.stop()
        del self.status_thread.gc
        self.status_thread.gc = None
        time.sleep(1) # not okay probably
        self.status_thread.gc = api.GantryController(MOCK_MODE_GANTRY)
        self.status_thread.gc.start()
        #self.output_box.image_label.set_status(False)
        # TODO: actually make this reset the entire state of the GUI

    def calibrate_event(self):
        QMessageBox.information(None, 'Calibration', 'Wow!', QMessageBox.Ok)
        # TODO: deem if this is a necessary functionality or if we will keep it in arduino code

    def close_event(self):
        self.camera.stop()
        gc = self.status_thread.gc
        if gc.arduino:
            if gc.arduino.is_open:
                self.status_thread.gc.arduino.close()
                print("closed serial interface..")
        time.sleep(1)
        qApp.exit()
        # TODO: deem if this is a necessary functionality or if we will keep it in arduino code

    def settings_event(self):
        pass

    def debug_cmds_event(self):
        pass
