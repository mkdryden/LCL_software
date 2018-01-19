import cv2
import matplotlib.pyplot as plt
import numpy as np

img_loc = r'C:\Users\Harrison\Dropbox\experiment_14_11_2017___11.33.45.915560\before_qswitch_fire___14_11_2017___12.12.48.307360.jpg'

img = cv2.imread(img_loc,0)
plt.subplot(221),plt.imshow(img,cmap='gray')
plt.subplot(222),plt.hist(img.flatten(),bins=100)
print(np.mean(img))
# plt.imshow(img,cmap='gray')
# plt.show()

dst = cv2.fastNlMeansDenoising(img,None,3,7,7)


plt.subplot(223),plt.imshow(dst,cmap='gray')
plt.subplot(224),plt.hist(dst.flatten(),bins=100)
print(np.mean(dst))
plt.show()