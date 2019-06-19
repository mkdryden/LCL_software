from cffi import FFI
from _pi_cffi import ffi, lib
import numpy as np
import time
assert lib.tl_camera_sdk_dll_initialize() == 0
assert lib.tl_camera_open_sdk() == 0
import sys
import matplotlib.pyplot as plt
print('sdk and dll open successfully!')




def get_camera_ids():
    # returns a handle to a char array of all of the available cameras separated by spaces
    camera_ids = ffi.new('char[1024]')
    assert lib.tl_camera_discover_available_cameras(camera_ids, 1024) == 0
    return camera_ids


@ffi.def_extern()
def tl_camera_frame_available_callback(sender, image_buffer, frame_count, metadata, metadata_size_in_bytes, context):
    # print('CAMERA FRAME AVAILABLE CALLBACK TRIGGERED')
    print(frame_count)
    data = ffi.buffer(image_buffer, 2160*4096*2)
    np_data = np.frombuffer(data, np.uint16)
    # np.save('/home/hedwar/Desktop/out.npy', np_data)

    # print(data[:], int(frame_count))


# @ffi.def_extern()
# def tl_camera_camera_connect_callback(cameraSerialNumber, usb_port_type, context):
#     print('CAMERA CONNECT CALLBACK TRIGGERED')
#     return 0
#
#
# @ffi.def_extern()
# def tl_camera_camera_disconnect_callback(cameraSerialNumber, context):
#     print('CAMERA CONNECT CALLBACK TRIGGERED')
#     return 0


zero_pointer = ffi.new('int*', 0)
# print('setting camera connect callback...',
#       lib.tl_camera_set_camera_connect_callback(lib.tl_camera_camera_connect_callback, zero_pointer))
# print('setting camera disconnect callback...',
#       lib.tl_camera_set_camera_disconnect_callback(lib.tl_camera_camera_disconnect_callback, zero_pointer))

camera_ids = get_camera_ids()  # <-- now we have a pointer to a char array of all cameras
print('available cameras:', ffi.string(camera_ids))

first_camera = ffi.new('char [256]')
first_camera = camera_ids  # <-- now we have a char array of the first camera serial address
print('first camera:', ffi.string(first_camera))

camera_handle_pointer = ffi.new('void **')
# print(camera_handle_pointer)
print('opening camera...', lib.tl_camera_open_camera(first_camera, camera_handle_pointer))

zero_pointer = ffi.new('int*', 0)
camera_handle = camera_handle_pointer[0]
function_pointer = lib.tl_camera_frame_available_callback
print('setting frame available callback...',
      lib.tl_camera_set_frame_available_callback(camera_handle, function_pointer, ffi.new('int*', 0)))
# print(camera_handle_pointer)
# print(camera_handle)



# set the camera exposure time
print('setting exposure...', lib.tl_camera_set_exposure_time(camera_handle, 1000))
# exposure = ffi.new('long long *')
# print(lib.tl_camera_get_exposure_time(camera_handle_pointer[0], exposure))
# print(exposure[0])

height = ffi.new('int*')
width = ffi.new('int*')
print('getting width...', lib.tl_camera_get_image_width(camera_handle, height))
print('getting height...', lib.tl_camera_get_image_height(camera_handle, width))
# print(height[0])
# print(width[0])

# r = ffi.new('enum TL_CAMERA_DATA_RATE *')
# print('getting camera data rate...', lib.tl_camera_get_data_rate(camera_handle, r))
# print(r[0])
print('setting frames per trigger...', lib.tl_camera_set_frames_per_trigger_zero_for_unlimited(camera_handle, 0))
print('arming camera...', lib.tl_camera_arm(camera_handle, 2))
print('triggering camera...', lib.tl_camera_issue_software_trigger(camera_handle))

# print('waiting for callback..')

while True:
     time.sleep(2)
     # print('triggering camera...', lib.tl_camera_issue_software_trigger(camera_handle))



# print(lib.tl_camera_close_camera(camera_handle))
# print(lib.tl_camera_close_sdk())
# print(lib.tl_camera_sdk_dll_terminate())




# # # set the frame trigger to 1
# # print(lib.tl_camera_set_frames_per_trigger_zero_for_unlimited(camera_handle, 1))
# #
# # # set the python callback for when a frame is available
# # zero= ffi.new('int *')
