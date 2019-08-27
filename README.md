# Project Overview 

The vein-detection system utilizes a webcam, near-IR LEDs, and a Raspberry Pi. Cameras generally have an IR filter in
front of the CCD to block IR light; however, in this project, the near-IR light is desired. A Raspberry Pi NoIR Camera
will be used as it does not have an infrared filter. Based on the absorption curve for oxygenated hemoglobin shown in
Figure 1, 850nm IR light provides the best balance between absorptivity and skin permeability, so 850nm IR LEDs will be
used to illuminate the patient’s veins. Coupling the IR camera with an 850nm IR bandpass filter, the camera will be able
to image the veins in the patient’s dorsum region.

The IR camera will send a continuous video stream to a Raspberry Pi for image processing. Using Python’s OpenCV library,
the image processing algorithm will determine which vein has the largest diameter and locate the most parallel portion
of the vein relative to the gantry. The coordinate of insertion will be displayed on a monitor and the technician will
verify the pending vein. Upon verification, the Pi will send the coordinate to an Arduino Mega, which controls the IV
gantry.
