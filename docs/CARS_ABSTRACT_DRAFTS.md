# CARS 2026 Abstract Drafts — Marvin Sim Chair Teleoperation

---

## ✅ FINAL — Submission Version (based on Draft 2)

**Title:** Haptic Sim-Chair-Based Teleoperation System for Autonomous Vehicle Platforms
*(pending PI approval — Dr. Bahr to confirm title)*

**Authors (CARS registration order):** Ryan Simpson, Tyler Carrasco, Yi-Szen Tang, Kevin Xu, Justin Dang

**Faculty Mentor:** Dr. Behnam Bahr (bbahr@cpp.edu)

**Program:** Other — AVL  
**Category:** Engineering and Computer Science  
**Presentation:** Poster or Creative Work Showcase  
**Team:** 5 (1 graduate, 4 undergraduate)

**Submitted abstract (as filed — poster should match):**

Remote operation of ground vehicles presents fundamental challenges in situational awareness. An operator who is not physically present in the vehicle loses the sensory feedback that enables precise and confident driving, including peripheral vision and the perception of acceleration. Conventional teleoperation systems provide only a flat video feed, which limits their effectiveness in applications such as hazardous-environment operations and safety intervention for autonomous vehicles.

The Cal Poly Pomona Autonomous Vehicles Lab has developed a bidirectional haptic teleoperation system that restores this missing feedback. The test platform carries three ZED X stereo cameras and an Xsens MTi-680G IMU, managed by an onboard NVIDIA Jetson Orin. The operator is seated in a D-BOX motion-enabled simulation chair fitted with a Thrustmaster racing wheel and pedals, facing three monitors arranged to reproduce a driver's natural field of view. Steering and pedal inputs are transmitted to the vehicle in real time, while the vehicle's measured accelerations drive the motion chair so that the operator physically experiences the forces acting on the vehicle.

All communication is carried over a Tailscale VPN rather than line-of-sight radio, allowing the operator and vehicle to be separated by any distance. The complete system is fully operational, and the operator drives the vehicle remotely through live panoramic video while receiving motion feedback in real time. This poster presents the system architecture, examines the engineering challenges of low-latency video and control over the internet, and discusses applications of immersive teleoperation to autonomous vehicle development.

*(Note: submission text had typo "carrys" — corrected to "carries" above for the poster.)*

---

12th Annual Creative Activities and Research Symposium (CPP CARS)
August 6, 2026 · Bronco Student Center · 1-hour interactive poster session

---

## Draft 1 — Balanced (recommended starting point, ~240 words)

**Title:** Feeling the Road from Miles Away: A Haptic Teleoperation System for Remote Vehicle Driving

When a driver operates a vehicle remotely, they lose the sensory cues that make driving intuitive — peripheral vision, the feeling of acceleration, the vibration of the road. This loss of physical feedback makes remote driving slow, imprecise, and fatiguing, limiting its use in applications such as hazardous-environment operations, remote vehicle recovery, and autonomous vehicle safety backup.

This project, developed in the Cal Poly Pomona Autonomous Vehicles Lab, restores those missing senses through a bidirectional haptic teleoperation system for a go-kart named Marvin. An operator sits in a simulation chair equipped with a racing wheel, pedals, and a D-BOX motion platform, facing three monitors arranged panoramically. On the vehicle, an NVIDIA Jetson Orin computer streams live video from three stereoscopic cameras positioned to replicate a driver's field of view, while an onboard inertial measurement unit captures the vehicle's real motion — acceleration, braking, and cornering forces. That motion data drives the operator's chair, so the operator physically feels what the vehicle experiences. All communication travels over a secure VPN, allowing operation across any internet connection rather than requiring line-of-sight radio.

The system currently achieves full remote driving control with live three-camera video, and ongoing work targets sub-150-millisecond video latency and full motion feedback integration. This work demonstrates that consumer simulation hardware can be combined with robotics platforms to build immersive, low-cost teleoperation systems.

---

## Draft 2 — General-audience / impact-led (~230 words)

**Title:** Driving a Go-Kart from a Chair: Building Human Presence into Remote Vehicles

Imagine driving a vehicle that is miles away — and feeling every turn, bump, and brake as if you were in the driver's seat. Remote vehicle operation is increasingly important for dangerous environments, disaster response, mining, and as a safety fallback for autonomous vehicles, but today's teleoperation systems give operators only a flat video feed, stripping away the physical sensations that make human driving skillful.

The Cal Poly Pomona Autonomous Vehicles Lab is building a teleoperation system that puts those sensations back. Our test vehicle, a go-kart named Marvin, carries three wide-angle stereoscopic cameras, motion sensors, and an onboard computer. Miles away, an operator sits in a motion-enabled simulation chair with a racing wheel and pedals, surrounded by three screens that recreate the driver's natural field of view. When the operator steers, the kart steers; when the kart accelerates, corners, or brakes, the chair tilts and moves so the operator feels the same forces the vehicle experiences.

The system communicates entirely over the internet through a secure VPN, meaning the operator and vehicle can be anywhere in the world relative to each other. Remote driving control and live panoramic video are fully operational, with motion feedback integration underway. Our poster presents the system architecture, the engineering challenges of low-latency video and control, and a roadmap toward fully immersive remote driving.

---

## Draft 3 — Compact version (~150 words, if word limit is tight)

**Title:** Bidirectional Haptic Teleoperation of a Ground Vehicle Using a Motion Simulation Chair

Remote vehicle operators lose the physical cues — peripheral vision, motion, vibration — that make driving intuitive. This project, from the Cal Poly Pomona Autonomous Vehicles Lab, restores them through a bidirectional haptic teleoperation system for a go-kart named Marvin. The operator drives from a simulation chair with a racing wheel, pedals, and D-BOX motion platform, viewing live video from three vehicle-mounted stereoscopic cameras across three panoramic monitors. An onboard NVIDIA Jetson Orin streams video and receives control commands over a secure VPN, while an inertial measurement unit captures the vehicle's real accelerations to drive the motion chair — letting the operator feel cornering, braking, and road forces remotely. Remote driving and live three-camera video are fully functional; current work targets sub-150-millisecond latency and complete motion feedback. The system demonstrates low-cost, internet-scale immersive teleoperation using consumer simulation hardware.

---

## Open questions before submitting

1. **Word limit** — what does the CARS submission form specify? (Commonly 250 words; Draft 3 covers a tighter limit.)
2. **Faculty mentor** — abstracts typically require the faculty advisor's name; whose name goes on it?
3. **Author list** — just the presenter, or the full team (Kevin Xu, Yi-Szen Tang, Tyler Carrasco, Justin Dang, Ryan Simpson)?
4. **Summer program affiliation** — CARS highlights students in summer research programs (e.g., RSCA, OUR-SPP, McNair). Which program is this under? Some forms ask.
5. **Status by August 6** — will IMU→D-BOX haptics be working by then? Drafts say "underway"; if it'll be done, we should claim it as a result instead.
6. **Results/metrics** — any measured numbers by submission time (actual latency, frame rate, range tested)? Even one real number strengthens the abstract.
