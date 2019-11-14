import api
from time import sleep
import os
import pinetworkvideostream
import socket
from pinetworkvideostream import ImageStreamer
import time
import struct
import threading
import picamera


def streams(pool, pool_lock):
    while True:
        with pool_lock:
            if pool:
                streamer = pool.pop()
            else:
                streamer = None
        if streamer:
            yield streamer.stream
            streamer.event.set()
        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.1)

class Forwarder:
    def __init__(self):
        print("Initializing forwarder..")

        try:
            self.client_socket = socket.socket()
            self.client_socket.connect((pinetworkvideostream.IP, 8002))
            self.connection = self.client_socket.makefile('wb')

            self.connection_lock = threading.Lock()
            self.pool_lock = threading.Lock()
            self.pool = []
            self.closed = False

            with picamera.PiCamera() as camera:
                # ...maintain a queue of objects to store the captures
                pool = [ImageStreamer(self.connection, self.client_socket, self.pool, self.connection_lock, self.pool_lock) for i in range(4)]
                camera.resolution = (1000, 1000)
                camera.framerate = 10  # should be raised??
                camera.awb_mode = 'tungsten'
                time.sleep(2)
                start = time.time()
                camera.capture_sequence(streams(pool, self.pool_lock), 'jpeg', use_video_port=True)

            # Shut down the streamers in an orderly fashion
            while pool:
                streamer = pool.pop()
                streamer.terminated = True
                streamer.join()

            # Write the terminating 0-length to the connection to let the server
            # know we're done
            with self.connection_lock:
                self.connection.write(struct.pack('<L', 0))

        finally:
            self.closed = True
            self.connection.close()
            self.client_socket.close()


        #cam = pinetworkvideostream.ImageStreamer(connection, client_socket)
        #cam.start()

        """
        self.gc = api.GantryController()
        self.gc.start()
        sleep(1)

        while True:
            self.gc.send_msg(api.REQ_ECHO_MSG, "123 echo 123\n")
            sleep(1)
        """