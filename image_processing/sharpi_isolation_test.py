"""
Brief script to test the functionality of the Sharpie isolation function
of prostick_lib.py
"""
import image_processing.prostick_lib as iv
from image_processing.thresholding import *
import cv2


grid_horizontal, grid_vertical = iv.initialize_grids('../assets/coord_static_x_revised.png',
                                                     '../assets/coord_static_y.png')
sharpie_img = cv2.imread('../sharpie_images/sharpie15.png', 0)
sharpie_mask = cv2.imread('../sharpie_images/sharpie_mask.png', 0)

gv = grid_vertical
# gv = cv2.resize(grid_vertical, dsize=(img.shape[0], img.shape[1]))

#  Use 200 for when the sharpie is hardly visible and in the middle
#  Use 175 when the sharpie is in any other areas
#  If the sharpie is up high don't go larger than
pos, mask, masked_img = iv.isolate_sharpie(sharpie_img, sharpie_mask, 175, 0.7, 73, grid_vertical, True)
plt.subplot(1, 3, 1)
plt.title("Mask")
plt.imshow(mask, 'gray')
plt.subplot(1, 3, 2)
plt.title("Masked Image")
plt.imshow(masked_img, 'gray')
plt.scatter(pos[1], pos[0], c='red', s=10, alpha=0.5)
plt.subplot(1, 3, 3)
plt.title("Sharpie Image with Result")
plt.imshow(sharpie_img, 'gray')
plt.scatter(pos[1], pos[0], c='red', s=10, alpha=0.5)