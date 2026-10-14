// controller_reader.h
// Owns the SDL2 joystick lifecycle and exposes normalised input readings.
#ifndef SIMCHAIR_CONTROLLER_READER_H_
#define SIMCHAIR_CONTROLLER_READER_H_

#include <SDL2/SDL.h>
#include <string>

namespace simchair {

/// Raw, normalised state from a single SDL2 joystick.
struct ControllerState {
    float steering      = 0.0f;  // -1.0 (left) .. +1.0 (right)
    float throttle_raw  = 0.0f;  // SDL2 axis value before pedal inversion
    float brake_raw     = 0.0f;  // SDL2 axis value before pedal inversion
    bool  left_shifter  = false;
    bool  right_shifter = false;
};

/// Manages an SDL2 joystick for the sim chair controller.
///
/// Lifecycle: Construct → Open() → Poll() in a loop → destructor closes.
/// RAII: destructor always closes the device and calls SDL_Quit.
class ControllerReader {
 public:
    /// joystick_index: SDL2 device index (0 = first detected joystick).
    explicit ControllerReader(int joystick_index = 0);
    ~ControllerReader();

    // Non-copyable; move is not implemented for simplicity.
    ControllerReader(const ControllerReader&) = delete;
    ControllerReader& operator=(const ControllerReader&) = delete;

    /// Initialises SDL2 and opens the joystick.
    /// Returns false and logs to stderr on failure.
    [[nodiscard]] bool Open();

    /// Returns the display name reported by SDL2.
    [[nodiscard]] std::string DeviceName() const;

    /// Pumps the SDL2 event queue and samples the current axis/button state.
    /// Must be called once per loop iteration before reading State().
    void Poll();

    [[nodiscard]] const ControllerState& State() const { return state_; }

 private:
    int           joystick_index_;
    SDL_Joystick* joystick_ = nullptr;
    ControllerState state_{};
};

}  // namespace simchair

#endif  // SIMCHAIR_CONTROLLER_READER_H_
