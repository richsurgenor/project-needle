import cv2
import numpy as np
from matplotlib import pyplot as plt
import numpy as np
import time

img = cv2.imread('fake_images/Screen Shot 2019-08-22 at 11.37.45 AM.png',0)
img = cv2.medianBlur(img,5) # needed?

THRESHOLD = 25

#plt.ion()
laplacian = cv2.Laplacian(img,cv2.CV_8UC1)
sobelx = cv2.Sobel(img,cv2.CV_8UC1,1,0,ksize=5)
#sobely = cv2.Sobel(img,cv2.CV_8UC1,0,1,ksize=5)

th2 = cv2.adaptiveThreshold(sobelx,255,cv2.ADAPTIVE_THRESH_MEAN_C,\
            cv2.THRESH_BINARY,THRESHOLD,2)

titles = ['Original Image', 'laplacian',
            'sobelx', 'sobelx-post-thresholding']
images = [img, laplacian, sobelx, th2]

for i in range(0, 4):
    plt.subplot(2,2,i+1),plt.imshow(images[i],'gray')
    plt.pause(0.0001)
    plt.title(titles[i])
    plt.pause(0.0001)
    plt.xticks([]),plt.yticks([])
    plt.pause(0.0001)
plt.show()
#time.sleep(1)
#plt.clf()