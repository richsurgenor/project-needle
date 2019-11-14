"""
Project Needle
Auburn  University
Senior Design |  Fall 2019

Team Members:
Andrea Walker, Rich Surgenor, Jackson Solley, Jacob Hagewood,
Justin Sutherland, Laura Grace Ayers.
"""

import socket
import struct
import time
import threading
import picamera
import io

IP = "192.168.0.1"

# TODO: auto try to reconnect if disconnected from server...

class ImageStreamer(threading.Thread):
    def __init__(self, connection, client_socket, pool):
        super(ImageStreamer, self).__init__()
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()

        self.connection = connection
        self.client_socket = client_socket
        self.pool = pool

    def run(self):
        # This method runs in a background thread
        while not self.terminated:
            # Wait for the image to be written to the stream
            if self.event.wait(1):
                try:
                    with self.connection_lock:
                        # < = little endian, L = unsigned int
                        self.connection.write(struct.pack('<L', self.stream.tell()))
                        self.connection.flush()
                        self.stream.seek(0)
                        self.connection.write(self.stream.read())
                finally:
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    with self.pool_lock:
                        self.pool.append(self)

