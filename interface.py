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
from PyQt5.QtGui import QPixmap, QPainter, QImage
#from PyQt5.QtCore import QFile, QTextStream, QPoint
from pyqtgraph import ImageView
from cv2 import VideoCapture
#import numpy as np
import sys
import processor_interface
import time

MOCK_MODE = 1

IMAGE_SIZE_WIDTH = 400
IMAGE_SIZE_HEIGHT = 300
BORDER_SIZE = 10

def ui_main():
    app = QApplication(sys.argv)
    #app.setStyle(QStyleFactory.create('Cleanlooks'))
    #app.setStyleSheet("QLineEdit:disabled{background-color: gray;}
    file = QFile("./dark.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())
    ui = MainWindow()
    sys.exit(app.exec_())

def _createCntrBtn(*args):
    l = QHBoxLayout()
    for arg in args:
        l.addStretch()
        l.addWidget(arg)
    l.addStretch()
    return l

def get_processor(camera):
    if MOCK_MODE:
        return processor_interface.ProcessorMock(camera)
    else:
        return processor_interface.Processor(camera)


class Camera:
    def __init__(self, camera_num):
        self.cap = None
        self.camera_num = camera_num
        self.last_frame = None
        self.opened = False

    def initialize(self):
        self.cap = VideoCapture(self.camera_num)
        self.opened = True

    def is_open(self):
        return self.opened

    def get_frame(self):
        pass

    def set_brightness(self, value):
        pass

    def get_frame(self):
        ret, self.last_frame = self.cap.read()
        return self.last_frame

    #def get_preview(self):
    #    self.cap.g

    def close_camera(self):
        self.cap.release()

    def __str__(self):
        return 'OpenCV Camera {}'.format(self.camera_num)


class PreviewThread(QThread):
    def __init__(self, camera, image_view):
        super().__init__()
        self.camera = camera
        self.image_view = image_view

    def run(self):
        while self.camera.is_open():
            frame = self.camera.get_frame()
            self.image_view.setImage(frame.T)
            self.msleep(100)
            qApp.processEvents()


class QImageBox(QGroupBox):

    def __init__(self, text):
        super(QGroupBox, self).__init__(text)
        #self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

class QImageGroupBox(QGroupBox):
    def __init__(self, text, img):
        super(QGroupBox, self).__init__(text)
        _layout = QHBoxLayout()
        self.image_label = QImageLabel("", img)
        _layout.addWidget(self.image_label)
        self.setLayout(_layout)

class QImageLabel(QLabel):
    def __init__(self, _, img):
        super(QLabel, self).__init__(_)
        self.setFrameShape(QFrame.Panel)
        #self.setFrameStyle("background-color: rgb(255, 255, 255")
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(3)
        self.setMidLineWidth(3)
        self.mousePressEvent = self.getPos
        self.img = img
        self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.done = False

    #def paintEvent(self, e):
    #    QLabel.paintEvent
    def enable(self):
        self.done = True
        self.repaint()
        #self.pain
        #p = QPainter(self)
        #p.drawPixmap(QPoint(BORDER_SIZE / 2, BORDER_SIZE / 2), self.img)

    def paintEvent(self, e):
        QLabel.paintEvent(self, e)
        p = QPainter(self)

        if self.done:
            p.drawPixmap(QPoint(BORDER_SIZE/2, BORDER_SIZE/2), self.img)
        #print(self.img.size())

    def getPos(self, event):
        # TODO: Reverse scaling to get closet coordinates...
        print("x: " + str(event.pos().x()) + "\ny: " + str(event.pos().y()))

    def sizeHint(self):
        return QSize(IMAGE_SIZE_WIDTH + BORDER_SIZE, IMAGE_SIZE_HEIGHT + BORDER_SIZE)

class MainWindow(QMainWindow):
    """
    Main window for application.
    """

    def __init__(self):
        super(QMainWindow, self).__init__()
        #self.resize(1200, 800)
        self.camera = Camera(0)
        self.camera.initialize()
        self.processor = get_processor(self.camera)
        self.wid = QWidget(self)
        self.setCentralWidget(self.wid)
        self.setWindowTitle('Project Needle')
        self._layout = QBoxLayout(QBoxLayout.TopToBottom, self.wid)
        self._layout.setSpacing(0)
        self.wid.setLayout(self._layout)

        self.status = QStatusBar()
        self.status.showMessage("STATUS: pending user input..")
        self._layout.addWidget(self.status)

        #self._layout.addWidget(self.centralWidget)
        self.pic_widget = QImageBox("Image View")
        self.pics_hbox = QHBoxLayout(self.pic_widget)
        self.pics_hbox.setAlignment(Qt.AlignHCenter);
        self.pics_hbox.setSpacing(100)
        self.pic_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        #self.image_box = QImageBox()
        #_layout = QLayout()

        #_img = QPixmap("image3.jpg")
        #img = _img.scaled(400, 400, Qt.KeepAspectRatio)
        #self.lb = QImageLabel(self, img)
        #pixmap_og = QPixmap("image3.jpg")
        #pixmap_og_scaled = pixmap_og.scaled(400,400, Qt.KeepAspectRatio)


        #self.lb.setPixmap(pixmap_og_scaled)


        self.image_view = ImageView()
        self.pics_hbox.addWidget(self.image_view) #(self.lb)
        self.feed = PreviewThread(self.camera, self.image_view)
        self.feed.start()
        x = self.camera.get_frame().T

        # Convert numpy img to pixmap
        cv_img = self.camera.get_frame().T
        height, width, channel = cv_img.shape
        bytes_per_line = 3 * width
        q_img = QImage(cv_img.copy().data, width, height, bytes_per_line, QImage.Format_RGB888)
        processed_img = QPixmap.fromImage(q_img)
        # Create Overlay Img with Transparency
        overlay_img = QPixmap("transparent_reticle.png")
        overlay_alpha = QPixmap(overlay_img.size())
        overlay_alpha.fill(Qt.transparent)  # force alpha channel
        # Paint overlay_img onto overlay_alpha
        painter = QPainter(overlay_alpha)
        painter.drawPixmap(0, 0, overlay_img)
        painter.end()

        #processed_img = QPixmap("image3_results_n1.jpg")
        processed_img_scaled = processed_img.scaled(IMAGE_SIZE_WIDTH, IMAGE_SIZE_HEIGHT, Qt.IgnoreAspectRatio)
        overlay_scaled = overlay_alpha.scaled(55, 55, Qt.KeepAspectRatio)
        result = QPixmap(processed_img_scaled.width(), processed_img_scaled.height())
        result.fill(Qt.transparent) # force alpha channel
        painter = QPainter(result)
        # Paint final images on result
        painter.drawPixmap(0, 0, processed_img_scaled)
        painter.drawPixmap(100, 100, overlay_scaled)
        painter.end()

        self.output_box = QImageGroupBox("Processed Image", result)
       #self.lb2.setPixmap(self.result)
        #self.lb2.setObjectName("lb2")

        #self.lb2.resize(400,400)
        self.pics_hbox.addWidget(self.output_box)
        self._layout.addWidget(self.pic_widget)
        # buttons
        
        btn_process_img = QPushButton("Process Image")
        btn_process_img.clicked.connect(self.process_image_event)
        btn_reset = QPushButton("Reset")
        btn_calibrate = QPushButton("Calibrate")

        self.btn_widget = QWidget()
        btn_panel = _createCntrBtn(btn_process_img, btn_reset, btn_calibrate)
        self.btn_widget.setLayout(btn_panel)

        self._layout.addWidget(self.btn_widget)

        self.show()

    def process_image_event(self):
        self.processor.process_image(self.camera.get_frame()) # TODO : add input img from camera
        self.output_box.image_label.enable()
            
        print("Processing...")



        #self.lb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #self.lb.setSizeP
        #self.pics_hbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #self.pics_hbox.addWidget(self.lb)




        #self._layout.addLayout(_createCntrBtn())
