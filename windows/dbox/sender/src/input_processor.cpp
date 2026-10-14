// Shared with v2_production — identical implementation.
#include "simchair/input_processor.h"
#include <algorithm>

namespace simchair {

static constexpr int kModeMin = 0;
static constexpr int kModeMax = 3;

float InputProcessor::NormalizePedal(float raw_axis) {
    return std::clamp(-raw_axis + 1.0f, 0.0f, 1.0f);
}

bool InputProcessor::Process(const ControllerState& raw) {
    const int prev_mode = command_.driving_mode;

    if (raw.left_shifter) {
        command_.driving_mode = std::max(command_.driving_mode - 1, kModeMin);
    }
    if (raw.right_shifter) {
        command_.driving_mode = std::min(command_.driving_mode + 1, kModeMax);
    }

    command_.steering = raw.steering;
    command_.throttle = NormalizePedal(raw.throttle_raw);
    command_.brake    = NormalizePedal(raw.brake_raw);

    return command_.driving_mode != prev_mode;
}

}  // namespace simchair
