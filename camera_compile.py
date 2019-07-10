from cffi import FFI

ffibuilder = FFI()

# ffibuilder.cdef("#include <sys/types.h>;")

# cdef() expects a single string declaring the C types, functions and
# globals needed to use the shared object. It must be in valid C syntax.
ffibuilder.cdef("""    
    int tl_camera_sdk_dll_initialize(void);
    int tl_camera_open_sdk();
    int tl_camera_close_sdk();
    int tl_camera_sdk_dll_terminate();
    int tl_camera_discover_available_cameras(char *, int); 
    int tl_camera_open_camera(char *, void **);
    int tl_camera_set_exposure_time(void *, long long);
    int tl_camera_get_exposure_time(void *, long long *);    

    int tl_camera_set_gain(void *, int);
    int tl_camera_get_gain(void *, int *);
    int tl_camera_get_gain_range(void *, int *, int *) ;
    
    int tl_camera_get_firmware_version(void *, char *, int);
    int tl_camera_close_camera(void *);
    
    typedef enum TL_CAMERA_DATA_RATE
    {
	TL_CAMERA_DATA_RATE_RESERVED1 ///< A RESERVED value (DO NOT USE).
    , TL_CAMERA_DATA_RATE_RESERVED2 ///< A RESERVED value (DO NOT USE).
    , TL_CAMERA_DATA_RATE_FPS_30 ///< Sets the device to deliver images at 30 frames per second.
    , TL_CAMERA_DATA_RATE_FPS_50 ///< Sets the device to deliver images at 50 frames per second.
    , TL_CAMERA_DATA_RATE_MAX ///< A sentinel value (DO NOT USE).
    };
    
    int tl_camera_get_data_rate (void *, enum TL_CAMERA_DATA_RATE * );
    
    int tl_camera_set_frames_per_trigger_zero_for_unlimited(void *, unsigned int);
    
    typedef enum TL_CAMERA_USB_PORT_TYPE
    {
	TL_CAMERA_USB_PORT_TYPE_USB1_0 ///< The device is connected to a USB 1.0/1.1 port (1.5 Mbits/sec or 12 Mbits/sec).
    , TL_CAMERA_USB_PORT_TYPE_USB2_0 ///< The device is connected to a USB 2.0 port (480 Mbits/sec).
    , TL_CAMERA_USB_PORT_TYPE_USB3_0 ///< The device is connected to a USB 3.0 port (5000 Mbits/sec).
    , TL_CAMERA_USB_PORT_TYPE_MAX ///< A sentinel value (DO NOT USE).
    };
    
    typedef void TL_CAMERA_CONNECT_CALLBACK (char *, enum TL_CAMERA_USB_PORT_TYPE,  void *); //done 
    extern "Python" void tl_camera_camera_connect_callback(char *, enum TL_CAMERA_USB_PORT_TYPE, void *);//done
    int tl_camera_set_camera_connect_callback(TL_CAMERA_CONNECT_CALLBACK,  void *); //done 
    
    typedef void TL_CAMERA_FRAME_AVAILABLE_CALLBACK (void *, unsigned short *, int, unsigned char *, int, void *); //done
    extern "Python" void tl_camera_frame_available_callback(void *, unsigned short *, int, unsigned char *, int, void *); //done
    int tl_camera_set_frame_available_callback(void *, TL_CAMERA_FRAME_AVAILABLE_CALLBACK, void *);    
    
    
    int tl_camera_set_camera_disconnect_callback(void *, void *);
    extern "Python" void tl_camera_camera_disconnect_callback(char *, void *);

    int tl_camera_arm(void *, int); //done 
    int tl_camera_issue_software_trigger(void *);
    
    int tl_camera_get_image_width(void *, int *);
    int tl_camera_get_image_height(void *, int *);                
    
    
""")
# set_source() gives the name of the python extension module to
# produce, and some C source code as a string.  This C code needs
# to make the declarated functions, types and globals available,
# so it is often just the "#include".
ffibuilder.set_source("_pi_cffi",
                      """
                          #include <sys/types.h>
                          #include "/home/wheeler/include/tl_camera_sdk.h"
                          #include "/home/wheeler/include/tl_camera_sdk_load.c"
                          #include "/home/wheeler/include/tl_camera_sdk_load.h"                          
                      """,
                      libraries=['thorlabs_unified_sdk_main'])  # library name, for the linker

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
