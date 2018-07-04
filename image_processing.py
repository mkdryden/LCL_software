import cv2
import matplotlib.pyplot as plt
import numpy as np
from sklearn import preprocessing
import cProfile, pstats, io
pr = cProfile.Profile()
pr.enable()
image_loc = r'C:\Users\hedwa\OneDrive\LCL_software\Experiments\experiment_07_11_2017___14.47.43.909354\before_qswitch_fire___07_11_2017___15.02.40.994823.jpg'

image = cv2.imread(image_loc,cv2.IMREAD_GRAYSCALE)
print('shape of image: {}'.format(image.shape))
# image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
# image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

# blur kernel size should relate to cell wall thickness
image = cv2.medianBlur(image,5)
#### PREPROCESSING #####
min_max_scaler = preprocessing.MinMaxScaler(feature_range=(0, 255))
image = image.astype(float).flatten()
image = min_max_scaler.fit_transform(image)
image = image.reshape(822,1024)
image = image.astype(np.uint8)
#### END PREPROCESSING #####
# probably want to erode about half of the cell wall thickness
kernel  = np.ones((5,5))
image = cv2.erode(image,kernel)
# min and max radii will depend on the cell radii
# dp size: very sensitive to this. should relate cell diameter to size of image
circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, 3,200,minRadius = 50,
	maxRadius = 100)
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



