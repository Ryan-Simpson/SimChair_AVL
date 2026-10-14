// main.cpp — D-BOX integrated sim chair sender (Windows)
//
// Extends the production sender with D-BOX LiveMotion SDK support.
// Runs on the Windows PC where the sim chair hardware and D-BOX motion
// platform are physically connected.
//
// Responsibilities:
//   1. Read controller inputs via SDL2 (same mapping as simchair_sender.py)
//   2. Send vehicle commands over UDP to the Ubuntu vehicle platform
//   3. Drive the D-BOX sim chair actuators in sync with driver inputs
//
// Prerequisites (Windows):
//   - SDL2 installed (https://libsdl.org)
//   - D-BOX G4 Motion System driver installed
//   - dbxLive64.dll in PATH or same directory as executable
//
// Build: see CMakeLists.txt
// Run:   simchair_sender_dbox.exe [--ip <addr>] [--port <n>]

#include <windows.h>  // for Sleep()

#include <cstdio>
#include <cstdlib>
#include <csignal>
#include <atomic>
#include <string>

static std::atomic<bool> g_running{true};

static void OnSignal(int) {
    g_running = false;
}

#include "simchair/controller_reader.h"
#include "simchair/dbox_motion_controller.h"
#include "simchair/input_processor.h"
#include "simchair/udp_sender_win.h"

// D-BOX application key — replace with your project-specific key from D-BOX.
// This string is permanent; it must not change between releases.
static constexpr const char* kDboxAppKey      = "CalPolyPomonaDevSim";
static constexpr unsigned int kDboxBuildVer   = 1000;

static const char* kDefaultIp      = "100.93.121.3";
static const int   kDefaultPort    = 5006;
static const int   kLoopIntervalMs = 50;   // 20 Hz
static const int   kShiftDelayMs   = 250;  // mode change debounce

struct Config {
    std::string ip   = kDefaultIp;
    int         port = kDefaultPort;
};

static bool g_test_mode = false;

static Config ParseArgs(int argc, char* argv[]) {
    Config cfg;
    for (int i = 1; i < argc; ++i) {
        std::string flag = argv[i];
        if      (flag == "--ip"   && i + 1 < argc) cfg.ip   = argv[++i];
        else if (flag == "--port" && i + 1 < argc) cfg.port = std::atoi(argv[++i]);
        else if (flag == "--test") g_test_mode = true;
    }
    return cfg;
}

// Sends a single hardcoded command to the D-BOX for a set duration,
// printing what it's doing so you can feel each axis individually.
static void PostStep(simchair::DboxMotionController& dbox,
                     const char* label,
                     float steering, float throttle, float brake,
                     int duration_ms)
{
    simchair::VehicleCommand cmd;
    cmd.steering = steering;
    cmd.throttle = throttle;
    cmd.brake    = brake;
    cmd.driving_mode = 1;

    printf("  %-30s  S:% .2f  T:%.2f  B:%.2f\n",
           label, steering, throttle, brake);

    const int steps = duration_ms / 50;
    for (int i = 0; i < steps; ++i) {
        dbox.PostFrame(cmd);
        Sleep(50);
    }
}

static void RunMotionTest(simchair::DboxMotionController& dbox) {
    printf("\n=== D-BOX ACTUATOR TEST (gains at 100%%) ===\n");
    printf("Each step holds for 3 seconds.\n\n");

    // Centre — all neutral
    PostStep(dbox, "CENTRE (neutral)",        0.0f, 0.0f, 0.0f, 3000);

    // Roll axis (steering)
    PostStep(dbox, "ROLL LEFT  (steer left)", -1.0f, 0.0f, 0.0f, 3000);
    PostStep(dbox, "CENTRE",                   0.0f, 0.0f, 0.0f, 1500);
    PostStep(dbox, "ROLL RIGHT (steer right)", 1.0f, 0.0f, 0.0f, 3000);
    PostStep(dbox, "CENTRE",                   0.0f, 0.0f, 0.0f, 1500);

    // Pitch axis (throttle = forward lean, brake = backward lean)
    PostStep(dbox, "PITCH FWD  (full throttle)", 0.0f, 1.0f, 0.0f, 3000);
    PostStep(dbox, "CENTRE",                      0.0f, 0.0f, 0.0f, 1500);
    PostStep(dbox, "PITCH BACK (full brake)",     0.0f, 0.0f, 1.0f, 3000);
    PostStep(dbox, "CENTRE",                      0.0f, 0.0f, 0.0f, 1500);

    // Heave axis (brake compresses down)
    PostStep(dbox, "HEAVE DOWN (brake impact)",  0.0f, 0.0f, 1.0f, 3000);
    PostStep(dbox, "CENTRE",                      0.0f, 0.0f, 0.0f, 1500);

    // Combined — hard left turn under braking
    PostStep(dbox, "COMBINED   (left+brake)",   -1.0f, 0.0f, 1.0f, 3000);
    PostStep(dbox, "CENTRE",                      0.0f, 0.0f, 0.0f, 3000);

    printf("\n=== TEST COMPLETE ===\n\n");
}

int main(int argc, char* argv[]) {
    signal(SIGINT,  OnSignal);
    signal(SIGTERM, OnSignal);

    const Config cfg = ParseArgs(argc, argv);

    // -----------------------------------------------------------------------
    // Controller
    // -----------------------------------------------------------------------
    simchair::ControllerReader reader(0);
    if (!reader.Open()) return 1;
    printf("Controller: %s\n", reader.DeviceName().c_str());

    // -----------------------------------------------------------------------
    // UDP sender (WinSock2)
    // -----------------------------------------------------------------------
    simchair::UdpSenderWin sender(cfg.ip, cfg.port);
    if (!sender.Open()) return 1;
    printf("Sending to: %s:%d\n", cfg.ip.c_str(), cfg.port);

    // -----------------------------------------------------------------------
    // D-BOX motion controller
    // -----------------------------------------------------------------------
    simchair::DboxMotionConfig dbox_cfg;
    // Full strength in test mode, normal gains otherwise
    if (g_test_mode) {
        dbox_cfg.roll_gain  = 1.0f;
        dbox_cfg.pitch_gain = 1.0f;
        dbox_cfg.heave_gain = 1.0f;
    } else {
        dbox_cfg.roll_gain  = 0.5f;
        dbox_cfg.pitch_gain = 0.4f;
        dbox_cfg.heave_gain = 0.3f;
    }

    simchair::DboxMotionController dbox(dbox_cfg);
    if (!dbox.Initialize(kDboxAppKey, kDboxBuildVer)) {
        fprintf(stderr, "D-BOX initialization failed — continuing without motion\n");
    } else if (!dbox.Open()) {
        fprintf(stderr, "D-BOX open failed — continuing without motion\n");
    } else {
        if (dbox.Start()) {
            printf("D-BOX motion platform: ACTIVE\n");
        } else {
            fprintf(stderr, "D-BOX start failed — continuing without motion\n");
        }
    }

    // -----------------------------------------------------------------------
    // Input processor
    // -----------------------------------------------------------------------
    // Run actuator test sequence and exit if --test was passed
    if (g_test_mode) {
        RunMotionTest(dbox);
        return 0;
    }

    simchair::InputProcessor processor;

    printf("Running at 20 Hz. Press Ctrl+C to quit.\n");

    while (g_running) {
        reader.Poll();

        const bool mode_changed = processor.Process(reader.State());
        const simchair::VehicleCommand& cmd = processor.Command();

        printf("S: %.2f T: %.2f B: %.2f M: %d\n",
               cmd.steering, cmd.throttle, cmd.brake, cmd.driving_mode);

        // Send vehicle command to Ubuntu platform
        sender.Send(cmd);

        // Drive D-BOX actuators from same command
        dbox.PostFrame(cmd);

        if (mode_changed) {
            // Blocking debounce — matches Python time.sleep(0.25)
            Sleep(kShiftDelayMs);
        }

        Sleep(kLoopIntervalMs);
    }

    printf("\nShutting down...\n");
    // dbox destructor calls Stop → Close → Terminate automatically (RAII)
    return 0;
}
