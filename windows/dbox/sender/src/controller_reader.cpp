// Shared with v2_production — identical implementation.
// See cpp/v2_production/src/controller_reader.cpp for comments.
#include "simchair/controller_reader.h"
#include <SDL2/SDL.h>
#include <cstdio>

namespace simchair {

static constexpr int kAxisSteering = 0;
static constexpr int kAxisBrake    = 1;
static constexpr int kAxisThrottle = 6;
static constexpr int kButtonLeft   = 0;
static constexpr int kButtonRight  = 1;

static float NormalizeAxis(Sint16 raw) {
    return static_cast<float>(raw) / 32767.0f;
}

ControllerReader::ControllerReader(int joystick_index)
    : joystick_index_(joystick_index) {}

ControllerReader::~ControllerReader() {
    if (joystick_) SDL_JoystickClose(joystick_);
    SDL_Quit();
}

bool ControllerReader::Open() {
    if (SDL_Init(SDL_INIT_JOYSTICK) < 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return false;
    }
    if (SDL_NumJoysticks() == 0) {
        fprintf(stderr, "No controller found!\n");
        return false;
    }
    joystick_ = SDL_JoystickOpen(joystick_index_);
    if (!joystick_) {
        fprintf(stderr, "Failed to open joystick %d: %s\n",
                joystick_index_, SDL_GetError());
        return false;
    }
    return true;
}

std::string ControllerReader::DeviceName() const {
    if (!joystick_) return "<not opened>";
    const char* name = SDL_JoystickName(joystick_);
    return name ? name : "<unknown>";
}

void ControllerReader::Poll() {
    SDL_JoystickUpdate();
    state_.left_shifter  = SDL_JoystickGetButton(joystick_, kButtonLeft)  != 0;
    state_.right_shifter = SDL_JoystickGetButton(joystick_, kButtonRight) != 0;
    state_.steering      = NormalizeAxis(SDL_JoystickGetAxis(joystick_, kAxisSteering));
    state_.throttle_raw  = NormalizeAxis(SDL_JoystickGetAxis(joystick_, kAxisThrottle));
    state_.brake_raw     = NormalizeAxis(SDL_JoystickGetAxis(joystick_, kAxisBrake));
}

}  // namespace simchair
