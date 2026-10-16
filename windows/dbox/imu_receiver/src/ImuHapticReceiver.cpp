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
#include <cstdint>
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
//                         [--log path.csv | --log off]
static void ParseArgs(int argc, char* argv[], WashoutGains& g, float& comfort, std::string& logPath)
{
    for (int i = 1; i + 1 < argc; i += 2)
    {
        const std::string flag = argv[i];
        if (flag == "--log") { logPath = argv[i + 1]; continue; }
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

static int64_t WallMs()
{
    using namespace std::chrono;
    return duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count();
}

// One-way delay log (2026-10-15 latency study). t_ms is the Jetson wall clock at
// send, so owd_raw_ms = arrival - t_ms includes the (near-constant) clock offset;
// the rise above the run's minimum is the queue on Marvin's cellular upload.
// Default file: logs\imu_owd_YYYYMMDD_HHMMSS.csv next to the exe.
static FILE* OpenOwdLog(std::string path)
{
    if (path == "off") return nullptr;
    if (path.empty())
    {
        char exe[MAX_PATH];
        GetModuleFileNameA(nullptr, exe, MAX_PATH);
        std::string dir(exe);
        dir = dir.substr(0, dir.find_last_of("\\/")) + "\\logs";
        CreateDirectoryA(dir.c_str(), nullptr);
        SYSTEMTIME st;
        GetLocalTime(&st);
        char name[64];
        snprintf(name, sizeof(name), "\\imu_owd_%04d%02d%02d_%02d%02d%02d.csv",
                 st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        path = dir + name;
    }
    FILE* f = fopen(path.c_str(), "w");
    if (!f) { std::cerr << "cannot open log " << path << "\n"; return nullptr; }
    fprintf(f, "pc_ms,seq,t_ms,owd_raw_ms\n");
    std::cout << "One-way delay log: " << path << "\n";
    return f;
}

int main(int argc, char* argv[])
{
    SetConsoleCtrlHandler(OnConsoleEvent, TRUE);

    WashoutGains gains;
    float comfort = kComfortScale;
    std::string logPath;
    ParseArgs(argc, argv, gains, comfort, logPath);
    FILE* owdLog = OpenOwdLog(logPath);

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
    int64_t owdMin = INT64_MAX, owdLast = 0;

    while (g_Running)
    {
        ImuPacket pkt{};
        sockaddr_in sender{};
        int senderLen = sizeof(sender);
        int n = recvfrom(sock, (char*)&pkt, sizeof(pkt), 0, (SOCKADDR*)&sender, &senderLen);

        const auto now = std::chrono::steady_clock::now();
        const float dt = kSocketPollMs / 1000.0f;

        if (n == sizeof(pkt))
        {
            const int64_t arrive = WallMs();
            owdLast = arrive - static_cast<int64_t>(pkt.t_ms);
            if (owdLast < owdMin) owdMin = owdLast;
            if (owdLog)
                fprintf(owdLog, "%lld,%u,%llu,%lld\n", static_cast<long long>(arrive), pkt.seq,
                        static_cast<unsigned long long>(pkt.t_ms), static_cast<long long>(owdLast));
        }

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
            if (owdLog) fflush(owdLog);
            printf("rx %2u/s  pitch %+.3f  roll %+.3f  heave %+.3f  queue %4lld ms%s\n", rxSincePrint,
                   shownPitch, shownRoll, shownHeave,
                   static_cast<long long>(owdMin == INT64_MAX ? 0 : owdLast - owdMin),
                   rxSincePrint ? "" : "  (no IMU: ramping to neutral)");
            rxSincePrint = 0;
            lastPrint = now;
        }
    }

    dbox.setTelemetry(0, 0, 0, g_Engine ? 750.0f : 0.0f, 0);
    Sleep(1000);
    dbox.StopPeriodicStreaming();
    dbox.Shutdown();
    if (owdLog) fclose(owdLog);
    closesocket(sock);
    WSACleanup();
    g_DBox = nullptr;
    return 0;
}
