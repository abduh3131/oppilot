cmake_minimum_required(VERSION 3.15)
project(astra_depth_c C)

# Set this to your OpenNI2 install if not auto-detected
# Example: -DOPENNI2_DIR="C:/Program Files/OpenNI2"
if(NOT DEFINED OPENNI2_DIR)
  set(OPENNI2_DIR "C:/Program Files/OpenNI2")
endif()

set(OPENNI2_INCLUDE "${OPENNI2_DIR}/Include")
set(OPENNI2_LIBDIR  "${OPENNI2_DIR}/Lib")

include_directories(${OPENNI2_INCLUDE})
link_directories(${OPENNI2_LIBDIR})

add_executable(astra_depth_c main.c)

# On Windows the lib is OpenNI2.lib; on Linux it's libOpenNI2.so
if(WIN32)
  target_link_libraries(astra_depth_c OpenNI2)
else()
  target_link_libraries(astra_depth_c OpenNI2)
endif()
