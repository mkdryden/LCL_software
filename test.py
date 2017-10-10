import numpy as np 
import cv2

cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW) 
# backends = [CAP_VFW,
# CAP_V4L,
# CAP_FIREWIRE,
# CAP_QT,
# CAP_UNICAP,
# CAP_DSHOW,]
while(1):
    ret, frame = cap.read()
    #print(height)
    #cv2.imshow("Cropped Image", crop_img)
    #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # cv2.imshow('frame',frame)
    print(type(frame))
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release() 
cv2.destroyAllWindows()