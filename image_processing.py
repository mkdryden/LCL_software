import cv2
import matplotlib.pyplot as plt
import numpy as np

image_loc = r'C:\Users\hedwa\Desktop\the_experiment\miscellaneous___18_10_2017___16.16.01.033705.jpg'

image = cv2.imread(image_loc)
figure, axes = plt.subplots(1,2)
image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
axes[0].set_yticks([])
axes[0].set_xticks([])
axes[0].imshow(image)
image = cv2.medianBlur(image,31)
kernel = np.ones((20,20),np.uint8)
image = cv2.dilate(image,kernel,iterations = 1)
image = cv2.erode(image,kernel,iterations = 1)
_,image = cv2.threshold(image, 60, 255, cv2.THRESH_BINARY)
axes[1].set_yticks([])
axes[1].set_xticks([])
axes[1].imshow(image)


plt.show()