cmake_minimum_required(VERSION 3.16)
project(imu_haptic_receiver LANGUAGES CXX)

# Jetson imu_bridge.py (UDP :5007) -> washout -> D-BOX LiveMotion. Windows only.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(DBOX_SDK_ROOT "C:/Program Files/DBOX-SDK-Package/LiveMotionSdk"
    CACHE PATH "Path to the D-BOX LiveMotionSdk directory")
if(NOT EXISTS "${DBOX_SDK_ROOT}/include/LiveMotion/dboxLiveMotion.h")
    message(FATAL_ERROR "D-BOX SDK headers not found at ${DBOX_SDK_ROOT}/include/LiveMotion")
endif()

add_executable(imu_haptic_receiver
    src/ImuHapticReceiver.cpp
    src/WashoutFilter.cpp
    src/DBoxManager.cpp
)
target_include_directories(imu_haptic_receiver PRIVATE
    include
    "${DBOX_SDK_ROOT}/include/LiveMotion"
)
# DBoxManager.cpp picks the .lib name with #pragma comment(lib, DBOX_LIVEMOTION_LIB)
target_link_directories(imu_haptic_receiver PRIVATE "${DBOX_SDK_ROOT}/lib/windows")
target_link_libraries(imu_haptic_receiver PRIVATE ws2_32)
