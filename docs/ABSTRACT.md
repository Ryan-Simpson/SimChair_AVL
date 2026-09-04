# Project Abstract — Marvin Sim Chair Teleoperation System

## Overview

This project develops a full bidirectional haptic teleoperation system enabling a human operator to remotely drive a go-kart named Marvin from a simulation chair station. The system is being developed by the Cal Poly Pomona Autonomous Vehicles Lab (AVL) as an extension of their existing IGVC (Intelligent Ground Vehicle Competition) robotics platform.

## Motivation

Teleoperating a ground vehicle remotely presents fundamental challenges in situational awareness and physical feedback. A driver controlling a vehicle without being physically present loses the natural sensory inputs — peripheral vision, body motion, vibration — that enable confident, precise vehicle control. This project addresses those gaps by:

1. Providing a wide-angle three-camera view replicating the driver's field of vision
2. Feeding real vehicle motion data (G-forces, acceleration) into a D-BOX motion chair so the operator physically feels what the vehicle is doing
3. Delivering low-latency control input so the vehicle responds naturally to the operator's inputs

## System Design

The operator station consists of a Thrustmaster racing wheel and pedals connected to a Windows PC, paired with a D-BOX motion chair and three monitors arranged in a panoramic layout. The vehicle (Marvin) is a go-kart equipped with a NVIDIA Jetson Orin compute platform, three Stereolabs ZED X stereoscopic cameras, a Velodyne LiDAR, an Xsens IMU, and REV Spark MAX brushless motor controllers driven through a Teensy 4.1 motor bridge.

All communication between the operator station and the vehicle runs over Tailscale VPN, enabling operation over any internet connection without requiring a local network.

**Control path:** Wheel/pedal inputs are read via SDL2, encoded as UDP packets, transmitted over Tailscale to the Jetson, converted to differential-drive RPM commands via a Python controller, and delivered over USB serial to the Teensy which drives the Spark MAX controllers.

**Video path:** ZED X cameras publish compressed JPEG frames via ROS2. A Python sender forwards these frames over TCP to the Windows station where they are displayed across three monitors in a panoramic arrangement matching the physical camera placement on the vehicle.

**Haptic path (in development):** The Xsens IMU on the vehicle will provide real-time acceleration and orientation data that will be transmitted to the D-BOX chair's SDK, causing the chair to physically simulate the vehicle's motion — leaning into turns, pitching under acceleration and braking.

## Current Status (as of July 2026)

- ✅ Full remote driving control functional via sim chair wheel and pedals
- ✅ Three live camera streams displaying on operator monitors
- ✅ D-BOX SDK integrated and chair ready to receive motion data
- 🔄 Camera quality improvement in progress (targeting H.264 streaming)
- 🔄 Kart driving smoothness being tuned (motor controller behavior under investigation)
- ❌ IMU → D-BOX haptic feedback not yet wired

## Near-Term Goals

- Under 150ms end-to-end camera latency
- Smooth, natural vehicle control feel matching manual driving behavior
- Full simultaneous operation: cameras + controls + haptic chair
- Live demonstration with operator driving kart remotely while seated in sim chair

## Technologies Used

- **Compute:** NVIDIA Jetson Orin (Ubuntu 22.04, ROS2 Humble, CycloneDDS)
- **Cameras:** Stereolabs ZED X GMSL stereo cameras
- **Networking:** Tailscale VPN, UDP/TCP sockets
- **Video:** ZED SDK compressed JPEG, GStreamer (in progress)
- **Motor control:** Teensy 4.1, REV Spark MAX, differential drive mixing
- **Haptics:** D-BOX LiveMotion SDK
- **Input:** SDL2 (Thrustmaster wheel/pedals)
- **Languages:** Python (Jetson controllers), C++ (Windows sim chair + D-BOX)
