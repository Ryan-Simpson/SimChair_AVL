cmake_minimum_required(VERSION 3.16)
project(simchair_sender_dbox LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# -----------------------------------------------------------------------
# This version targets Windows (D-BOX SDK is Windows-only).
# -----------------------------------------------------------------------
if(NOT WIN32)
    message(FATAL_ERROR
        "v3_dbox requires Windows (D-BOX LiveMotion SDK is Windows-only).\n"
        "For Ubuntu, use v1_direct_port or v2_production instead.")
endif()

# -----------------------------------------------------------------------
# SDL2 — joystick input (works on Windows too)
# Either install via vcpkg: vcpkg install sdl2:x64-windows
# Or set SDL2_ROOT to your SDL2 directory
# -----------------------------------------------------------------------
find_package(SDL2 REQUIRED)

# -----------------------------------------------------------------------
# D-BOX LiveMotion SDK
# Set DBOX_SDK_ROOT to the LiveMotionSdk directory, e.g.:
#   cmake -DDBOX_SDK_ROOT="C:/path/to/DBOX_SDK/LiveMotionSdk" ..
# Default is the SDK installed on the sim chair PC
# -----------------------------------------------------------------------
set(DBOX_SDK_ROOT "C:/Program Files/DBOX-SDK-Package/LiveMotionSdk"
    CACHE PATH "Path to the D-BOX LiveMotionSdk directory")

if(NOT EXISTS "${DBOX_SDK_ROOT}/include/LiveMotion/dboxLiveMotion.h")
    message(FATAL_ERROR
        "D-BOX SDK headers not found at ${DBOX_SDK_ROOT}/include\n"
        "Set DBOX_SDK_ROOT to the LiveMotionSdk directory.")
endif()

set(SOURCES
    src/controller_reader.cpp
    src/input_processor.cpp
    src/udp_sender_win.cpp
    src/dbox_motion_controller.cpp
    src/main.cpp
)

add_executable(simchair_sender_dbox ${SOURCES})

target_include_directories(simchair_sender_dbox
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../../cpp/v2_production/include  # reuse shared headers
        ${SDL2_INCLUDE_DIRS}
        ${DBOX_SDK_ROOT}/include
)

# Tell the linker where to find the D-BOX .lib files.
# The #pragma comment(lib, DBOX_LIVEMOTION_LIB) in dbox_motion_controller.cpp
# resolves the filename; this directory tells the linker where to search.
target_link_directories(simchair_sender_dbox
    PRIVATE
        ${DBOX_SDK_ROOT}/lib/windows
)

target_link_libraries(simchair_sender_dbox
    PRIVATE
        SDL2::SDL2main
        SDL2::SDL2
        ws2_32
)

# Copy dbxLive64.dll next to the executable after build
# (The DLL ships in DBOX_SDK/LiveMotionSdk/Samples/)
set(DBOX_DLL "${DBOX_SDK_ROOT}/Samples/dbxLive64.dll")
if(EXISTS "${DBOX_DLL}")
    add_custom_command(TARGET simchair_sender_dbox POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${DBOX_DLL}"
            "$<TARGET_FILE_DIR:simchair_sender_dbox>"
        COMMENT "Copying dbxLive64.dll to output directory")
endif()
