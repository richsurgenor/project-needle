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

if not os.name == 'ut':
    USING_PI = os.uname()[4][:3] == 'arm'
else:
    USING_PI = False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'forwarder':
        if USING_PI:
            print("Initializing with forwarding client (Pi)...")
            import forwarding
            fwder = forwarding.Forwarder()
        else:
            print("Initializing with forwarding server (PC)...")
            ui_main(True)
    else:
        ui_main()


