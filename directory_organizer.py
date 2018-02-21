import os
import shutil
experiment_folder_location = os.path.join(os.path.dirname(os.path.abspath(__file__)),'Experiments')

# first lets delete all experiments with no pictures in them
for name in os.listdir(experiment_folder_location):
	if 'sd' not in name:
		files = ''.join(os.listdir(os.path.join(experiment_folder_location,name)))
		if '.tif' not in files:		
			response = input('WARNING directory {} found not to have files. Type Y to Delete\n'.format(name))
			if response == 'Y':
				shutil.rmtree(os.path.join(experiment_folder_location,name))
				print('deleting:',name)

def get_480mb_worth_of_files(directory):
	paths_out = []
	running_total = 0
	# files = filter(os.path.isfile, os.listdir(directory))
	# print(files)
	files = [os.path.join(directory, f) for f in os.listdir(directory)] # add path to each file
	files.sort(key=lambda x: os.path.getmtime(x),reverse = True)
	for file in files:
		size = os.path.getsize(os.path.join(directory,file))
		running_total += size/10**6
		paths_out.append(file)
		if running_total > 480:
			return paths_out
	return paths_out

# next lets sort the pictures into groups of < 500mb so they can be uploaded to owncloud
directories = os.listdir(experiment_folder_location)
directories = [name for name in directories if 'sd' not in name]
directoryies_out = [os.path.join(experiment_folder_location,'sd_' + name) for name in directories]
for name in directoryies_out:
	os.makedirs(name)

print(os.getcwd())
for i,directory in enumerate(directories):
	subdirectory = os.path.join(experiment_folder_location,directory)
	print('fixing directory:',subdirectory)
	subdirectory_int = 0
	while len(os.listdir(subdirectory)) > 0:		
		new_dir = os.path.join(directoryies_out[i],str(subdirectory_int))
		os.makedirs(new_dir)
		from_paths = get_480mb_worth_of_files(subdirectory)	
		for path in from_paths:
			file_name = path.split('\\')[-1]
			shutil.move(path,os.path.join(new_dir,file_name))
		subdirectory_int += 1
print('done')