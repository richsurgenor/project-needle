import api
from time import sleep
import os

class Forwarder:
    def __init__(self):
        print("Initializing forwarder..")

        self.gc = api.GantryController()
        self.gc.start()
        sleep(1)

        while True:
            self.gc.send_msg(api.REQ_ECHO_MSG, "123 echo 123\n")
            sleep(1)