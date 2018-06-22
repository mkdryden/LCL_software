import cv2,os
import matplotlib.pyplot as plt
import numpy as np
import argparse
import pickle
import sys

global fill_val, last_x, last_y
last_x = -1
last_y = -1

# we want to load images, and receive a mask that will be the GT

#Not used?
test_file_path = r'C:\Users\Harrison\ownCloud\sd_experiment_26_02_2018___11.47.48.277723\2\before_qswitch___26_02_2018___13.59.55.413329.tif'


# python image_annotator_backup.py "Multiplicity Test Small" out.p 14

def fill_contour(mask):
	im2, contours, hierarchy = cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
	for cnt in contours:
		cv2.drawContours(mask,[cnt],0,fill_val,-1)
		#print(cnt)
	#cv2.drawContours(mask,0,fill_val,-1)
	mask = cv2.bitwise_not(mask)	

def mouse_event(event, x, y, flags, param):
	global last_x, last_y, mask_final, mask, mask_display 
	if event == 0 and flags == 1:
		if (last_x == -1 and last_y == -1):  # Branch for the very first point
			mask[y,x] = fill_val
			#mask_final[y,x] = fill_val
			mask_display[y,x] = fill_val
			last_x = x
			last_y = y
			mask_display = cv2.add(mask_display, mask_final)
			cv2.imshow('ground_truth',mask_display)
			# cv2.circle(mask,(x,y),5,(255,255,255),thickness = -1)
		else:							# Branch for all other points to draw a line
			mask[y,x] = fill_val
			#mask_final[y,x]
			mask_display[y,x]
			lineThickness = 2	
			cv2.line(mask, (last_x, last_y), (x, y), (fill_val,fill_val,fill_val), lineThickness)
			#cv2.line(mask_final, (last_x, last_y), (x, y), (fill_val,fill_val,fill_val), lineThickness)
			cv2.line(mask_display, (last_x, last_y), (x, y), (fill_val,fill_val,fill_val), lineThickness)
			last_x = x
			last_y = y
			mask_display = cv2.add(mask_display, mask_final)
			cv2.imshow('ground_truth',mask_display)
	if event == 4:
		fill_contour(mask)
		mask_final = cv2.add(mask, mask_final)
		#mask_display = mask_final
		mask = np.uint8(np.zeros((img.shape[0],img.shape[1])))
		#mask_display = np.uint8(np.zeros((img.shape[0],img.shape[1])))
		last_x = -1
		last_y = -1
		cv2.imshow('ground_truth', mask_final)
	#cv2.imshow('ground_truth',mask_final)		

 


if __name__ == '__main__':
	global mask_to_store, mask_final, mask, mask_display

	parser = argparse.ArgumentParser(description='Input file path to create ground truth from.')
	parser.add_argument('data_path', help='path for image files')
	parser.add_argument('output_path', help='path for output GT files')
	parser.add_argument('multiplicity', help='number of repeated images')
	args = parser.parse_args()
	x_train = np.zeros((1,500,500))
	y_train = np.zeros((1,500,500))
	mult = int(args.multiplicity)+1
	count = mult
	fill_val = 255
	for f in os.listdir(args.data_path):
		annotating = True		
		if (('.tif' in f)&(count%mult==0)):		# Branch for first image in set
			im_path = os.path.join(args.data_path,f)
			print('\nTrace the cell outline for:', f)
			img = cv2.imread(im_path,0)
			img = cv2.resize(img,(500,500))
			y = np.copy(img)
			mask = np.uint8(np.zeros((img.shape[0],img.shape[1])))
			mask_final = np.uint8(np.zeros((img.shape[0],img.shape[1])))
			mask_display = np.uint8(np.zeros((img.shape[0],img.shape[1])))
			cv2.namedWindow('image')
			cv2.setMouseCallback('image', mouse_event)		#MOUSE EVENT
			cv2.imshow('image',img)
			cv2.namedWindow('ground_truth')
			cv2.imshow('ground_truth',mask_display)
			while (annotating == True):
				res = cv2.waitKey(0)
				#print('Waitkey pressed = ',res)
				#print(x_train.shape,y_train.shape)
				if res == 32: 				# 'Spacebar'
					x = np.copy(mask_final)
					mask_to_store = np.copy(mask_final)
					cv2.destroyAllWindows()
					# f = f.split('.tif')[0] + '_ANNOTATED.tif'
					# out_path = os.path.join(args.output_path,f)
					# cv2.imwrite(out_path,mask)
					x = np.expand_dims(x,axis = 0)			
					y = np.expand_dims(y,axis = 0)			
					x_train = np.concatenate((x_train,x),axis=0)
					y_train = np.concatenate((y_train,y),axis=0)
					print('     ', x_train.shape,y_train.shape)
					annotating = False
					count = count+1
				elif res == 101:				# 'E' key
					mask = np.uint8(np.zeros((img.shape[0],img.shape[1])))
					mask_final = np.uint8(np.zeros((img.shape[0],img.shape[1])))
					mask_display = np.uint8(np.zeros((img.shape[0],img.shape[1])))
					cv2.imshow('ground_truth',mask)
					cv2.imshow('image',img)
					#cv2.setMouseCallback('image', mouse_event)		#MOUSE EVENT
					print('\n     Erased.\n')
					mask_to_store = np.copy(mask)
				elif res ==27:				# 'ESC' key
					print('\n     ESC key pressed. Program terminated.')
					sys.exit()
					cv2.destroyAllWindows()
					break
				elif res ==49:     			# '1' key
					fill_val = 255
					print('\n     Cell type 1.\n')
				elif res ==50:				# '2' key
					fill_val = 85
					print('\n     Cell type 2.\n')
				elif res ==51:				# '3' key
					fill_val = 170
					print('\n     Cell type 3.\n')
				else:
					print('\n     You pressed Waitkey',res)
					print('     That key does nothing.')
				
		elif (('.tif' in f)&(count%mult!=0)):				# Branch for remaining images in set
			x = mask_to_store				# Copy in the stored mask
			im_path = os.path.join(args.data_path,f)
			print('     copying GT for:', f)
			img = cv2.imread(im_path,0)
			img = cv2.resize(img,(500,500))
			y = np.copy(img)
			x = np.expand_dims(x,axis = 0)			
			y = np.expand_dims(y,axis = 0)			
			x_train = np.concatenate((x_train,x),axis=0)
			y_train = np.concatenate((y_train,y),axis=0)
			print(x_train.shape,y_train.shape)
			count = count+1
			annotating = False
			
			
		pass
		#print('Moving to next file.')
		
	x_train = y_train[1:,:,:]			
	y_train = x_train[1:,:,:]			
	pickle.dump((x_train,y_train),open(args.output_path,'wb'))
	print('\n     Done.')