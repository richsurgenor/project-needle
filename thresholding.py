import cv2
import numpy as np
from matplotlib import pyplot as plt
import time

img = cv2.imread('fake_images/Screen Shot 2019-08-22 at 11.37.45 AM.png',0)
img = cv2.medianBlur(img,5)

plt.ion()
for i in range(11, 100):
    ret,th1 = cv2.threshold(img,160,255,cv2.THRESH_BINARY)
    if i % 2 != 1:
        continue
    th2 = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_MEAN_C,\
                cv2.THRESH_BINARY,i,2)
    th3 = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
                cv2.THRESH_BINARY,i,2)

    titles = ['Original Image', 'Global Thresholding (v = 127)',
                'Adaptive Mean Thresholding', 'Adaptive Gaussian Thresholding']
    images = [img, th1, th2, th3]

    print(i)
    for i in range(0, 4):
        plt.subplot(2,2,i+1),plt.imshow(images[i],'gray')
        plt.pause(0.0001)
        plt.title(titles[i])
        plt.pause(0.0001)
        plt.xticks([]),plt.yticks([])
        plt.pause(0.0001)
    plt.show()
    time.sleep(1)
    plt.clf()