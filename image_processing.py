import cv2
import matplotlib.pyplot as plt
import numpy as np
from sklearn import preprocessing
import cProfile, pstats, io
pr = cProfile.Profile()
pr.enable()
image_loc = r'C:\Users\hedwa\OneDrive\the_experiment\miscellaneous___18_10_2017___16.18.10.465411.jpg'

image = cv2.imread(image_loc,cv2.IMREAD_GRAYSCALE)
print('shape of image: {}'.format(image.shape))
# image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
# image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

# blur kernel size should relate to cell wall thickness
image = cv2.medianBlur(image,11)
#### PREPROCESSING #####
min_max_scaler = preprocessing.MinMaxScaler(feature_range=(0, 255))
image = image.astype(float).flatten()
image = min_max_scaler.fit_transform(image)
image = image.reshape(1644,2048)
image = image.astype(np.uint8)
#### END PREPROCESSING #####
# probably want to erode about half of the cell wall thickness
kernel  = np.ones((15,15))
image = cv2.erode(image,kernel)
# min and max radii will depend on the cell radii
# dp size: very sensitive to this. should relate cell diameter to size of image
circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, 3,200,minRadius = 100,
	maxRadius = 200)
final_image = image
print('Cells detected: {}'.format(len(circles[0])))
fig,ax = plt.subplots(1,2)
image = cv2.imread(image_loc)
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
for i in circles[0,:]:
    # draw the outer circle
    # cv2.circle(image,(i[0],i[1]),i[2],(255,255,0),2)
    cv2.circle(image,(i[0],i[1]),2,(0,255,255),20)
ax[0].imshow(image)
ax[1].imshow(final_image)
pr.disable()
plt.show()
s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats()
print(s.getvalue())



