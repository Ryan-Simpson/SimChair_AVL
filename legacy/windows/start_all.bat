@echo off
REM start_all.bat — Windows sim-chair one-command launcher
REM Run from: C:\Users\VRX 226\cursor-test\windows\  (exe + DLLs + receivers must stay together)
REM
REM Environment variables (optional):
REM   VIDEO_MODE = udp | jpeg | zed | rtp   (default: udp — chunked JPEG)
REM   HAPTIC_MODE = dbox | test | off (default: dbox)

setlocal
cd /d "%~dp0"

if not defined VIDEO_MODE set VIDEO_MODE=udp
if not defined HAPTIC_MODE set HAPTIC_MODE=dbox

echo ========================================
echo  Marvin Sim Chair — starting all services
echo  VIDEO_MODE=%VIDEO_MODE%  HAPTIC_MODE=%HAPTIC_MODE%
echo ========================================

if /I "%VIDEO_MODE%"=="zed" (
    start "Marvin Video" cmd /k py -3.8 "%~dp0windows_zed_stream_receiver.py" --native-size
) else if /I "%VIDEO_MODE%"=="rtp" (
    start "Marvin Video" cmd /k python "%~dp0windows_gstreamer_rtp_receiver.py"
) else if /I "%VIDEO_MODE%"=="jpeg" (
    start "Marvin Video" cmd /k python "%~dp0windows_camera_receiver.py"
) else (
    rem default udp
    start "Marvin Video" cmd /k python "%~dp0windows_camera_receiver_udp.py"
)

timeout /t 2 /nobreak >nul

if /I "%HAPTIC_MODE%"=="dbox" (
    if exist "%~dp0ImuHapticReceiver.exe" (
        start "Marvin Haptics" cmd /k "%~dp0ImuHapticReceiver.exe"
    ) else (
        echo WARNING: ImuHapticReceiver.exe not found — using washout test listener
        start "Marvin Haptics Test" cmd /k python "%~dp0windows_imu_washout_test.py"
    )
) else if /I "%HAPTIC_MODE%"=="test" (
    start "Marvin Haptics Test" cmd /k python "%~dp0windows_imu_washout_test.py"
)

timeout /t 1 /nobreak >nul
start "Marvin Link Status" cmd /k python "%~dp0windows_control_status.py"
timeout /t 1 /nobreak >nul
start "Marvin Sender" cmd /k "%~dp0simchair_sender_dbox.exe"

echo.
echo All processes launched.
echo Fallback video: set VIDEO_MODE=jpeg
echo.
pause
