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
#include <cstring>

#include "DBoxManager.h"
#include "WashoutFilter.h"

#pragma comment(lib, "Ws2_32.lib")

static constexpr const char* kAppKey = "CalPolyPomonaDevSim";
static constexpr int   kAppBuild           = 1000;
static constexpr int   kUdpPort              = 5007;
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

    BOOL WINAPI OnConsoleEvent(DWORD)
    {
        g_Running = false;
        return TRUE;
    }
}

int main()
{
    SetConsoleCtrlHandler(OnConsoleEvent, TRUE);

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
    WashoutFilter washout(50.0f, kComfortScale);

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
    dbox.setTelemetry(0, 0, 0, 750.0f, 0);
    dbox.StartPeriodicStreaming(MOTION_DATA, kDboxStreamMs);

    std::cout << "IMU haptic receiver on UDP " << kUdpPort << " (50 Hz washout)\n";
    std::cout << "Watchdog: " << kWatchdogMs << " ms → ramp to neutral\n";

    auto lastPacket = std::chrono::steady_clock::now();
    uint32_t lastSeq = 0;

    while (g_Running)
    {
        ImuPacket pkt{};
        sockaddr_in sender{};
        int senderLen = sizeof(sender);
        int n = recvfrom(sock, (char*)&pkt, sizeof(pkt), 0, (SOCKADDR*)&sender, &senderLen);

        const auto now = std::chrono::steady_clock::now();
        const float dt = kSocketPollMs / 1000.0f;

        if (n == sizeof(pkt) && pkt.seq > lastSeq)
        {
            lastSeq = pkt.seq;
            lastPacket = now;

            float pitch, roll, heave;
            washout.Update(
                pkt.accel_x, pkt.accel_y, pkt.accel_z,
                pkt.roll, pkt.pitch,
                pitch, roll, heave);

            // Engine feel from forward accel
            float load = (pkt.accel_x > 0) ? pkt.accel_x / 4.0f : 0.0f;
            if (load > 1.0f) load = 1.0f;
            float rpm = 750.0f + load * (3500.0f - 750.0f);
            float torque = load * 450.0f;

            dbox.setTelemetry(pitch, roll, heave, rpm, torque);
        }
        else
        {
            const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                now - lastPacket).count();
            if (elapsed >= kWatchdogMs)
            {
                washout.RampToNeutral(dt);
                float p, r, h;
                washout.Update(0, 0, 0, 0, 0, p, r, h);
                dbox.setTelemetry(p, r, h, 750.0f, 0);
            }
        }
    }

    dbox.setTelemetry(0, 0, 0, 750.0f, 0);
    Sleep(1000);
    dbox.StopPeriodicStreaming();
    dbox.Shutdown();
    closesocket(sock);
    WSACleanup();
    g_DBox = nullptr;
    return 0;
}
