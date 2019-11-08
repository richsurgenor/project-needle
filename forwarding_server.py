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

# Start a socket listening for connections on 0.0.0.0:8000

class ForwardingCamera(threading.Thread):
    def __init__(self):
        server_socket = socket.socket()
        server_socket.bind(('0.0.0.0', 8000))
        server_socket.listen(0)

        self.frame = None

    def run(self):
        # TODO: add auto-reconnecting..

        # Accept a single connection and make a file-like object out of it
        connection = self.server_socket.accept()[0].makefile('rb')
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
                print('Image is %dx%d' % image.size)
                image.verify()
                print('Image is verified')
                self.frame = numpy.array(image)
        finally:
            connection.close()
            self.server_socket.close()

    def start(self):
        pass

    def stop(self):
        pass

    def get_frame(self):
        return self.frame


