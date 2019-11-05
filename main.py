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
import forwarding

if __name__ == "__main__":
    if sys.argv[1] != 'forwarding':
        ui_main()
    else:
        import forwarding
        fwder = forwarding.Forwarder()


