"""
Project Needle
Auburn  University
Senior Design |  Fall 2019

Team Members:
Andrea Walker, Rich Surgenor, Jackson Solley, Jacob Hagewood,
Justin Sutherland, Laura Grace Ayers.
"""

import io
import socket
import struct
import threading
from PIL import Image
import numpy
import cv2

# Start a socket listening for connections on 0.0.0.0:8000

class ForwardingCamera(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.server_socket = socket.socket()
        self.server_socket.bind(('0.0.0.0', 8002))
        self.server_socket.listen(0)

        self.frame = None

    def run(self):
        # TODO: add auto-reconnecting..

        # Accept a single connection and make a file-like object out of it
        print("Initializing ForwardingCamera Thread...")
        connection = self.server_socket.accept()[0].makefile('rb')
        print("Connection estabilshed...") # TODO: pick up dropped connection...
        try:
            while True:
                # Read the length of the image as a 32-bit unsigned int. If the
                # length is zero, quit the loop
                image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
                if not image_len:
                    break
                # Construct a stream to hold the image data and read the image
                # data from the connection
                image_stream = io.BytesIO()
                image_stream.write(connection.read(image_len))
                # Rewind the stream, open it as an image with PIL and do some
                # processing on it
                image_stream.seek(0)

                # TODO: change to pass numpy images back via frame
                image = Image.open(image_stream)
                #image.show()
                #print('Image is %dx%d' % image.size)
                #image.verify()
                #print('Image is verified')
                #print("received img..!")

                self.frame = image
        finally:
            connection.close()
            self.server_socket.close()

    def stop(self):
        pass

    def get_frame(self):
        if self.frame:
            image = numpy.array(self.frame)
            #note if png format is used then conversion is needed...
            #image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            return image
        else:
            return None


