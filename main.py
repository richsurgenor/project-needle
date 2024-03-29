"""
Project Needle
Auburn University
Senior Design |  Fall 2019

Team Members:
Andrea Walker, Rich Surgenor, Jackson Solley, Jacob Hagewood,
Justin Sutherland, Laura Grace Ayers.
"""

from gui import ui_main
import sys
import os
import platform
import time


if not platform.uname()[0] == 'Windows':
    USING_PI = os.uname()[4][:3] == 'arm'
else:
    USING_PI = False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'forwarder':
        if USING_PI:
            print("Initializing with forwarding client (Pi)...")
            import forwarding
            fwder = forwarding.Forwarder()
            while True:
                if not fwder or fwder.closed:
                    if fwder:
                        del fwder
                        fwder = None
                    print("Attempting to recreate connection..")
                    try:
                        fwder = forwarding.Forwarder()
                    except Exception as e:
                        print("failed..")
                    time.sleep(2)
                pass

        else:
            print("Initializing with forwarding server (PC)...")
            ui_main(True)
    else:
        ui_main()


