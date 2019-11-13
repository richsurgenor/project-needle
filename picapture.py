import time
import picamera
import numpy as np
import cv2

with picamera.PiCamera() as camera:
    camera.resolution = (3280, 2464)
    camera.framerate = 24
    time.sleep(2)
    output = np.empty((2464, 3280, 3), dtype=np.uint8)
    camera.capture(output, 'rgb')
    cv2.imwrite('picam.jpg', output)
