# Project Overview: Marvin Sim Chair

**Haptic Sim-Chair-Based Teleoperation System for Autonomous Vehicle Platforms**

Cal Poly Pomona Autonomous Vehicles Laboratory (AVL)  
Team: Ryan Simpson (lead), Tyler Carrasco, Yi-Szen Tang, Kevin Xu, Justin Dang  
Mentor: Dr. Behnam Bahr

---

## The problem

Remote drivers lose the cues that make driving intuitive:

- Peripheral vision and depth from being in the seat
- Body motion and the feel of acceleration, braking, and cornering
- Confident, precise control without those sensory inputs

Flat single-camera teleoperation is not enough for hazardous environments or autonomy safety intervention.

## The goal

Give the operator a human level of sight and realistic physical feedback while driving **Marvin** (go-kart) from a D-BOX sim chair over any internet link:

1. **Vision**: three ZED X cameras → three panoramic monitors
2. **Control**: Thrustmaster wheel/pedals → differential drive in real time
3. **Haptics**: vehicle IMU accelerations → D-BOX chair motion (working since 2026-10-14)

All links run over **Tailscale VPN** (no line-of-sight radio required).

## Platform at a glance

| Side | Hardware |
|------|----------|
| **Operator** (Windows `sim-chair`) | Thrustmaster wheel/pedals, D-BOX motion chair, 3 monitors (Surround: x=0 / 1920 / 3840) |
| **Vehicle** (Jetson Orin `dinosaur`) | 3× ZED X GMSL, Xsens IMU, Teensy 4.1 → REV Spark MAX, Velodyne LiDAR, NTRIP GPS |

Extension of the AVL **IGVC** robotics platform: teleop code lives outside `/home/dinosaur/IGVC/` (never modify that tree).

## Current status (lab-accurate)

| Capability | Status |
|------------|--------|
| Sim-chair wheel/pedal → kart motors | Working |
| Three live JPEG camera streams on monitors | Working (UDP primary ~1280×720 @ 30) |
| D-BOX SDK integrated on Windows | Working |
| Vehicle IMU → D-BOX chair cueing | Working (2026-10-14): wheel-encoder accel + gyro yaw cues, driver-approved |
| Motor drive via sim chair | Working with `--duty` (UL/UR); velocity mode often purple |
| H.265 primary video path | Experimental; UDP JPEG is current primary |

## Near-term objectives

- Median glass-to-glass camera latency under **150 ms** (on direct Tailscale)
- Smooth remote driving feel comparable to sitting in the vehicle
- Cameras + controls + haptic chair running together in one demo

## Technologies

Jetson Orin · ROS 2 Humble · CycloneDDS · ZED X · Xsens MTi · D-BOX LiveMotion · Tailscale · SDL2 · Python / C++ · Teensy 4.1 · REV Spark MAX

---

**See also:** [PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) · [ABSTRACT.md](../ABSTRACT.md) · [CARS poster pack](../../CARS_Poster/README.md)
