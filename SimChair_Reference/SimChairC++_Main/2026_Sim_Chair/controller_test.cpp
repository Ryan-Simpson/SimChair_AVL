#include <SDL.h>

#include <algorithm>
#include <iomanip>
#include <iostream>

static double axisToDouble(int value) {
    // SDL raw joystick axes are usually -32768 to +32767.
    // Convert to approximately -1.0 to +1.0.
    if (value < 0) {
        return static_cast<double>(value) / 32768.0;
    }
    return static_cast<double>(value) / 32767.0;
}

int main() {
    if (SDL_Init(SDL_INIT_JOYSTICK | SDL_INIT_EVENTS) != 0) {
        std::cerr << "SDL_Init failed: " << SDL_GetError() << '\n';
        return 1;
    }

    if (SDL_NumJoysticks() == 0) {
        std::cout << "No controller found!\n";
        SDL_Quit();
        return 0;
    }

    SDL_Joystick* controller = SDL_JoystickOpen(0);

    if (!controller) {
        std::cerr << "Failed to open joystick: " << SDL_GetError() << '\n';
        SDL_Quit();
        return 1;
    }

    std::cout << "Connected to: " << SDL_JoystickName(controller) << '\n';
    std::cout << "Axes: " << SDL_JoystickNumAxes(controller) << '\n';
    std::cout << "Buttons: " << SDL_JoystickNumButtons(controller) << '\n';
    std::cout << "Hats: " << SDL_JoystickNumHats(controller) << '\n';

    bool running {true};

    static int steering_raw;
    static int throttle_raw;
    static int brake_raw;
    static double steering;
    static double throttle;
    static double brake;
    static double throttle_norm;
    static double brake_norm;
    while (running) {
        SDL_Event event;

        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                running = false;
            }

            if (event.type == SDL_JOYDEVICEREMOVED) {
                SDL_JoystickID instance_id = SDL_JoystickInstanceID(controller);

                if (event.jdevice.which == instance_id) {
                    std::cout << "Controller disconnected.\n";
                    running = false;
                }
            }
        }

        SDL_JoystickUpdate();

        int now = SDL_GetTicks();

        // steering = controller.get_axis(0)
        // throttle = controller.get_axis(6)
        // brake = controller.get_axis(1)
        steering_raw = SDL_JoystickGetAxis(controller, 0);
        throttle_raw = SDL_JoystickGetAxis(controller, 6);
        brake_raw = SDL_JoystickGetAxis(controller, 1);

        steering = axisToDouble(steering_raw);
        throttle = axisToDouble(throttle_raw);
        brake = axisToDouble(brake_raw);

        // Safer clamp, in case the device behaves strangely.
        throttle_norm = std::clamp(throttle_norm, 0.0, 1.0);
        brake_norm = std::clamp(brake_norm, 0.0, 1.0);

        std::cout << std::fixed << std::setprecision(2)
                  << "S: " << steering << '\n'
                  << "T: " << throttle_norm << '\n'
                  << "B: " << brake_norm << '\n'
                  << "M: " << driving_mode << '\n'
                  << " | raw axes: "
                  << steering_raw << " "
                  << throttle_raw << " "
                  << brake_raw << '\n';

        SDL_Delay(100);
    }

    SDL_JoystickClose(controller);
    SDL_Quit();

    return 0;
}
