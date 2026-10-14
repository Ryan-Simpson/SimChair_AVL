// input_processor.h
// Converts raw ControllerState into vehicle command values.
#ifndef SIMCHAIR_INPUT_PROCESSOR_H_
#define SIMCHAIR_INPUT_PROCESSOR_H_

#include "simchair/controller_reader.h"

namespace simchair {

/// Processed, vehicle-ready values derived from raw controller state.
struct VehicleCommand {
    float steering      = 0.0f;  // -1.00 .. +1.00
    float throttle      = 0.0f;  //  0.00 .. +1.00
    float brake         = 0.0f;  //  0.00 .. +1.00
    int   driving_mode  = 0;     //  0=N 1=D 2=S 3=R
};

/// Stateful processor: applies axis normalisation and drive-mode state machine.
///
/// The drive-mode state machine mirrors simchair_sender.py exactly:
///   - left_shifter  decrements mode, clamped at 0
///   - right_shifter increments mode, clamped at 3
///   - Returns true when a mode change occurred (caller should debounce)
class InputProcessor {
 public:
    InputProcessor() = default;

    /// Processes a raw ControllerState and updates the internal VehicleCommand.
    /// Returns true if the driving mode changed this call (signals debounce need).
    bool Process(const ControllerState& raw);

    [[nodiscard]] const VehicleCommand& Command() const { return command_; }

 private:
    static float NormalizePedal(float raw_axis);

    VehicleCommand command_{};
};

}  // namespace simchair

#endif  // SIMCHAIR_INPUT_PROCESSOR_H_
