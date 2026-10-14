// dbox_motion_controller.h
// Wraps the D-BOX LiveMotion SDK for sim chair motion feedback.
//
// PLATFORM NOTE: The D-BOX LiveMotion SDK ships Windows .lib files only.
// This class must be compiled and linked on Windows.
// The dbxLive64.dll (or dbxLive32.dll) must be present at runtime.
//
// Design rationale:
//   simchair_sender.py has no motion feedback because ctypes + Python overhead
//   made it impractical. This class provides native C++ integration without
//   that overhead. It lives in the same process as the controller reader and
//   UDP sender, adding zero inter-process latency.
//
// Motion strategy (feedforward):
//   Since the vehicle's real physics are not yet available in this process,
//   we derive synthetic motion cues directly from the driver's inputs:
//     - Steering         → lateral roll (FM_RAW_ROLL)
//     - Throttle - Brake → longitudinal pitch (FM_RAW_PITCH)
//     - |Brake|          → heave down (FM_RAW_HEAVE)
//
//   When vehicle telemetry is available (future ROS2 integration), replace
//   this feedforward model with real acceleration data via FM_ACCELERATION_XYZ.

#ifndef SIMCHAIR_DBOX_MOTION_CONTROLLER_H_
#define SIMCHAIR_DBOX_MOTION_CONTROLLER_H_

#include "simchair/input_processor.h"

namespace simchair {

/// Configuration parameters for D-BOX motion scaling.
struct DboxMotionConfig {
    float roll_gain  = 0.5f;   // steering  → roll  amplitude  (0..1)
    float pitch_gain = 0.4f;   // accel/brake → pitch amplitude (0..1)
    float heave_gain = 0.3f;   // brake intensity → heave amplitude (0..1)
};

/// Wraps dbox::LiveMotion and drives the sim chair actuators from VehicleCommand.
///
/// Lifecycle:
///   DboxMotionController ctrl;
///   ctrl.Initialize("MyAppKey", 1000);
///   ctrl.Open();
///   ctrl.Start();                    // call when simulation begins
///   ctrl.PostFrame(cmd);             // call every loop iteration
///   ctrl.Stop();                     // call when simulation ends
///   // destructor calls Close() + Terminate()
class DboxMotionController {
 public:
    explicit DboxMotionController(DboxMotionConfig config = {});
    ~DboxMotionController();

    DboxMotionController(const DboxMotionController&) = delete;
    DboxMotionController& operator=(const DboxMotionController&) = delete;

    /// Calls dbox::LiveMotion::Initialize and registers the frame event.
    /// app_key must be the string assigned by D-BOX for your project.
    /// Returns false on failure.
    [[nodiscard]] bool Initialize(const char* app_key, unsigned int build_version);

    /// Calls dbox::LiveMotion::Open — prepares the motion platform.
    [[nodiscard]] bool Open();

    /// Calls dbox::LiveMotion::Start — begins motion output with fade-in.
    /// Call this when the simulation/drive session begins.
    [[nodiscard]] bool Start();

    /// Calls dbox::LiveMotion::Stop — ends motion output with fade-out.
    /// Call this when the simulation/drive session ends or is paused.
    void Stop();

    /// Posts one frame of motion data derived from the VehicleCommand.
    /// Call every loop iteration after Process().
    void PostFrame(const VehicleCommand& cmd);

    [[nodiscard]] bool IsStarted() const;

 private:
    void Close();
    void Terminate();

    DboxMotionConfig config_;
    bool initialized_ = false;
    bool opened_      = false;
    bool started_     = false;
};

}  // namespace simchair

#endif  // SIMCHAIR_DBOX_MOTION_CONTROLLER_H_
