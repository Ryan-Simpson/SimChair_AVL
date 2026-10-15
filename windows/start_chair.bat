@echo off
REM start_chair.bat — sim chair side for relay teleop (2026-10-14 setup)
REM   1. simchair_sender_dbox.exe --no-dbox  wheel/pedals -> Marvin UDP 5006 (no chair motion)
REM   2. imu_haptic_receiver.exe             Marvin IMU/odom cues UDP 5007 -> D-BOX chair
REM   3. viewer                              http://100.93.121.3:8090/
REM Keep the exes next to dbxLive64.dll and SDL2.dll.
REM Marvin side first: bash ~/SimChair_AVL/jetson/relay_teleop/start_all.sh
REM Old behaviour (chair rocks from the wheel): run simchair_sender_dbox.exe with no flags
REM and do not start imu_haptic_receiver.exe; only one program can drive the chair.
REM Receiver tuning flags: see dbox\README.md
setlocal
cd /d "%~dp0"
start "Marvin Sender (no D-BOX)" /D "%~dp0" "%~dp0simchair_sender_dbox.exe" --no-dbox
timeout /t 2 /nobreak >nul
start "IMU Chair" /D "%~dp0" "%~dp0imu_haptic_receiver.exe" %*
timeout /t 1 /nobreak >nul
start "" "http://100.93.121.3:8090/"
echo Put the chair in park (0) once to arm Marvin, then paddle 1 = diff, 2 = ackermann.
