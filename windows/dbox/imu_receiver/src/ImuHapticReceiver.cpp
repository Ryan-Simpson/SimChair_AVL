// ImuHapticReceiver.cpp — Phase 3 production IMU → D-BOX receiver
//
// Listens on UDP 5007 for binary packets from imu_bridge.py (Jetson).
// Applies WashoutFilter and drives DBoxManager at 50 Hz.
//
// Build: see windows/dbox/README.md (CMake, links dbxLive64 from the D-BOX SDK)
//
// Run alongside simchair_sender_dbox.exe OR as integrated receiver process.

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iostream>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "DBoxManager.h"
#include "WashoutFilter.h"

#pragma comment(lib, "Ws2_32.lib")

static constexpr const char* kAppKey = "CalPolyPomonaDevSim";
static constexpr int   kAppBuild           = 1000;
static constexpr int   kUdpPort              = 5007;
static constexpr float kImuHz                = 25.0f; // must match run_imu_bridge.sh IMU_HZ
static constexpr int   kDboxStreamMs         = 20;    // 50 Hz
static constexpr int   kWatchdogMs           = 500;
static constexpr int   kSocketPollMs         = 20;
static constexpr float kComfortScale         = 0.5f;  // 50% until Ryan approves tuning

#pragma pack(push, 1)
struct ImuPacket
{
    uint32_t seq;
    uint64_t t_ms;
    float accel_x, accel_y, accel_z;
    float gyro_x, gyro_y, gyro_z;
    float roll, pitch;
};
#pragma pack(pop)

static_assert(sizeof(ImuPacket) == 44, "ImuPacket size must match imu_bridge.py");

namespace
{
    DBoxManager* g_DBox = nullptr;
    std::atomic<bool> g_Running{ true };
    bool g_Engine = false;  // D-BOX engine rumble from accel; off = no idle vibration

    BOOL WINAPI OnConsoleEvent(DWORD)
    {
        g_Running = false;
        return TRUE;
    }
}

// imu_haptic_receiver.exe [--pitch g] [--roll g] [--yaw g] [--heave g] [--tilt-rate r]
//                         [--tilt-hz f] [--heave-hz f] [--comfort c]
//                         [--release r] [--attitude a] [--engine 0|1]
static void ParseArgs(int argc, char* argv[], WashoutGains& g, float& comfort)
{
    for (int i = 1; i + 1 < argc; i += 2)
    {
        const std::string flag = argv[i];
        const float v = static_cast<float>(std::atof(argv[i + 1]));
        if      (flag == "--pitch")     g.pitch = v;
        else if (flag == "--roll")      g.roll = v;
        else if (flag == "--yaw")       g.yaw = v;
        else if (flag == "--heave")     g.heave = v;
        else if (flag == "--tilt-rate") g.tiltRate = v;
        else if (flag == "--release")   g.releaseRate = v;
        else if (flag == "--attitude")  g.attitude = v;
        else if (flag == "--engine")    g_Engine = v != 0.0f;
        else if (flag == "--tilt-hz")   g.tiltCutoff = v;
        else if (flag == "--heave-hz")  g.heaveCutoff = v;
        else if (flag == "--comfort")   comfort = v;
        else std::cerr << "unknown flag " << flag << "\n";
    }
}

int main(int argc, char* argv[])
{
    SetConsoleCtrlHandler(OnConsoleEvent, TRUE);

    WashoutGains gains;
    float comfort = kComfortScale;
    ParseArgs(argc, argv, gains, comfort);

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0)
    {
        std::cerr << "WSAStartup failed\n";
        return 1;
    }

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET)
    {
        std::cerr << "socket failed\n";
        WSACleanup();
        return 1;
    }

    DWORD timeout = kSocketPollMs;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(kUdpPort);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(sock, (SOCKADDR*)&addr, sizeof(addr)) == SOCKET_ERROR)
    {
        std::cerr << "bind failed on port " << kUdpPort << "\n";
        closesocket(sock);
        WSACleanup();
        return 1;
    }

    DBoxManager dbox;
    g_DBox = &dbox;
    WashoutFilter washout(kImuHz, comfort, gains);

    dbox.Initialize(kAppKey, kAppBuild);
    dbox.RegisterEvent(SIM_CONFIG, dbox::EM_CONFIG_UPDATE, SimConfig::GetStructInfo());
    dbox.RegisterEvent(MOTION_CONFIG, dbox::EM_CONFIG_UPDATE, MotionConfig::GetStructInfo());
    dbox.RegisterEvent(MOTION_DATA, dbox::EM_FRAME_UPDATE, MotionData::GetStructInfo());
    dbox.Open();
    Sleep(2000);
    dbox.ResetState();
    dbox.PostEvent(SIM_CONFIG, dbox.GetSimConfig());
    dbox.PostEvent(MOTION_CONFIG, dbox.GetMotionConfig());
    dbox.Start();
    dbox.setTelemetry(0, 0, 0, g_Engine ? 750.0f : 0.0f, 0);
    dbox.StartPeriodicStreaming(MOTION_DATA, kDboxStreamMs);

    std::cout << "IMU haptic receiver on UDP " << kUdpPort << " (" << kImuHz << " Hz washout)\n";
    std::cout << "Watchdog: " << kWatchdogMs << " ms -> ramp to neutral\n";
    printf("Gains: pitch %.2f roll %.2f yaw %.2f heave %.2f  tilt-rate %.2f/s  tilt-hz %.2f  heave-hz %.2f  comfort %.2f\n",
           gains.pitch, gains.roll, gains.yaw, gains.heave, gains.tiltRate, gains.tiltCutoff,
           gains.heaveCutoff, comfort);
    printf("       release %.2f/s  attitude %.2f  engine %s\n",
           gains.releaseRate, gains.attitude, g_Engine ? "on" : "off");

    auto lastPacket = std::chrono::steady_clock::now();
    uint32_t lastSeq = 0;
    auto lastPrint = lastPacket;
    uint32_t rxSincePrint = 0;
    float shownPitch = 0, shownRoll = 0, shownHeave = 0;

    while (g_Running)
    {
        ImuPacket pkt{};
        sockaddr_in sender{};
        int senderLen = sizeof(sender);
        int n = recvfrom(sock, (char*)&pkt, sizeof(pkt), 0, (SOCKADDR*)&sender, &senderLen);

        const auto now = std::chrono::steady_clock::now();
        const float dt = kSocketPollMs / 1000.0f;

        // A big drop in seq means imu_bridge restarted (it counts from 1 again)
        if (n == sizeof(pkt) && (pkt.seq > lastSeq || pkt.seq + 1000 < lastSeq))
        {
            lastSeq = pkt.seq;
            lastPacket = now;

            float pitch, roll, heave;
            washout.Update(
                pkt.accel_x, pkt.accel_y, pkt.accel_z,
                pkt.roll, pkt.pitch, pkt.gyro_z,
                pitch, roll, heave);

            // Engine feel from forward accel
            float load = (pkt.accel_x > 0) ? pkt.accel_x / 4.0f : 0.0f;
            if (load > 1.0f) load = 1.0f;
            float rpm = g_Engine ? 750.0f + load * (3500.0f - 750.0f) : 0.0f;
            float torque = g_Engine ? load * 450.0f : 0.0f;

            dbox.setTelemetry(pitch, roll, heave, rpm, torque);
            shownPitch = pitch; shownRoll = roll; shownHeave = heave;
            ++rxSincePrint;
        }
        else
        {
            const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                now - lastPacket).count();
            if (elapsed >= kWatchdogMs)
            {
                washout.RampToNeutral(dt);
                float p, r, h;
                washout.Update(0, 0, 0, 0, 0, 0, p, r, h);
                dbox.setTelemetry(p, r, h, g_Engine ? 750.0f : 0.0f, 0);
                shownPitch = p; shownRoll = r; shownHeave = h;
            }
        }

        if (now - lastPrint >= std::chrono::seconds(1))
        {
            printf("rx %2u/s  pitch %+.3f  roll %+.3f  heave %+.3f%s\n", rxSincePrint,
                   shownPitch, shownRoll, shownHeave,
                   rxSincePrint ? "" : "  (no IMU: ramping to neutral)");
            rxSincePrint = 0;
            lastPrint = now;
        }
    }

    dbox.setTelemetry(0, 0, 0, g_Engine ? 750.0f : 0.0f, 0);
    Sleep(1000);
    dbox.StopPeriodicStreaming();
    dbox.Shutdown();
    closesocket(sock);
    WSACleanup();
    g_DBox = nullptr;
    return 0;
}
