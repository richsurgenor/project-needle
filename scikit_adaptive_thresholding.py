import matplotlib.pyplot as plt
from skimage import data
from skimage.filters import threshold_otsu
from skimage.filters.thresholding import threshold_local
from skimage.color import rgb2gray
import os

#image = data.camera()
filename = "fake_images/Screen Shot 2019-08-22 at 11.06.38 AM.png"
from skimage import io
moon = io.imread(filename)

image = rgb2gray(moon)

global_thresh = threshold_otsu(image)
binary_global = image > global_thresh

block_size = 13
binary_adaptive = threshold_local(image, block_size, offset=10)

fig, axes = plt.subplots(nrows=3, figsize=(7, 8))
ax0, ax1, ax2 = axes
plt.gray()

ax0.imshow(image)
ax0.set_title('Image')

ax1.imshow(binary_global)
ax1.set_title('Global thresholding')

ax2.imshow(binary_adaptive)
ax2.set_title('Adaptive thresholding')

for ax in axes:
    ax.axis('off')

plt.show()