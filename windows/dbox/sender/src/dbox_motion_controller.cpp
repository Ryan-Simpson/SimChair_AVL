// dbox_motion_controller.cpp
// Structs and RegisterEvent calls MUST match CalPolyPomonaDevSim Sample.cpp exactly.

#include "simchair/dbox_motion_controller.h"

#include <cstdio>
#include <algorithm>
#include <cmath>

#include "LiveMotion/dboxLiveMotion.h"
#pragma comment(lib, DBOX_LIVEMOTION_LIB)

namespace simchair {

namespace {

// ---------------------------------------------------------------------------
// These three structs are FIXED — must match Sample.cpp from the DevSim
// package exactly (field names, types, and FM_ meanings).
// ---------------------------------------------------------------------------

struct SimConfig {
    dbox::F32 MasterGain;
    dbox::F32 MasterSpectrum;

    DBOX_STRUCTINFO_BEGIN()
        DBOX_STRUCTINFO_FIELD(SimConfig, MasterGain,     dbox::FT_FLOAT32, dbox::FM_MASTER_GAIN_DB)
        DBOX_STRUCTINFO_FIELD(SimConfig, MasterSpectrum, dbox::FT_FLOAT32, dbox::FM_MASTER_SPECTRUM_DB)
    DBOX_STRUCTINFO_END()
};

struct MotionConfig {
    dbox::F32 EngineRpmIdle;
    dbox::F32 EngineRpmMax;
    dbox::F32 EngineTorqueMax;

    DBOX_STRUCTINFO_BEGIN()
        DBOX_STRUCTINFO_FIELD(MotionConfig, EngineRpmIdle,    dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM_IDLE)
        DBOX_STRUCTINFO_FIELD(MotionConfig, EngineRpmMax,     dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM_MAX)
        DBOX_STRUCTINFO_FIELD(MotionConfig, EngineTorqueMax,  dbox::FT_FLOAT32, dbox::FM_ENGINE_TORQUE_MAX)
    DBOX_STRUCTINFO_END()
};

struct MotionData {
    dbox::F32 Roll;          // -1.0 to 1.0
    dbox::F32 Pitch;         // -1.0 to 1.0
    dbox::F32 Heave;         // -1.0 to 1.0
    dbox::F32 EngineRpm;
    dbox::F32 EngineTorque;

    DBOX_STRUCTINFO_BEGIN()
        DBOX_STRUCTINFO_FIELD(MotionData, Roll,         dbox::FT_FLOAT32, dbox::FM_RAW_ROLL)
        DBOX_STRUCTINFO_FIELD(MotionData, Pitch,        dbox::FT_FLOAT32, dbox::FM_RAW_PITCH)
        DBOX_STRUCTINFO_FIELD(MotionData, Heave,        dbox::FT_FLOAT32, dbox::FM_RAW_HEAVE)
        DBOX_STRUCTINFO_FIELD(MotionData, EngineRpm,    dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM)
        DBOX_STRUCTINFO_FIELD(MotionData, EngineTorque, dbox::FT_FLOAT32, dbox::FM_ENGINE_TORQUE)
    DBOX_STRUCTINFO_END()
};

enum AppEvents : dbox::U32 {
    SIM_CONFIG    = 1000,
    MOTION_CONFIG = 2000,
    MOTION_DATA   = 3000,
};

const char* ResultString(dbox::ELiveMotionResult r) {
    switch (r) {
        case dbox::LMR_SUCCESS:                   return "SUCCESS";
        case dbox::LMR_ERROR:                     return "ERROR (unknown)";
        case dbox::LMR_ERROR_NOT_INITIALIZED:     return "NOT_INITIALIZED";
        case dbox::LMR_ERROR_NOT_OPENED:          return "NOT_OPENED";
        case dbox::LMR_ERROR_NOT_STARTED:         return "NOT_STARTED";
        case dbox::LMR_ERROR_REGISTER_LOCKED:     return "REGISTER_LOCKED";
        case dbox::LMR_ERROR_NO_EVENT_HANDLER:    return "NO_EVENT_HANDLER (D-BOX service not running?)";
        case dbox::LMR_ERROR_DLL_NOT_FOUND:       return "DLL_NOT_FOUND (dbxLive64.dll missing?)";
        case dbox::LMR_ERROR_DLL_ENTRY_NOT_FOUND: return "DLL_ENTRY_NOT_FOUND";
        case dbox::LMR_ERROR_NO_DEVICE_FOUND:     return "NO_DEVICE_FOUND (hardware not connected?)";
        default:                                  return "UNKNOWN";
    }
}

bool CheckResult(dbox::ELiveMotionResult result, const char* context) {
    if (result != dbox::LMR_SUCCESS) {
        fprintf(stderr, "[D-BOX] %s FAILED: %s (code %d)\n",
                context, ResultString(result), static_cast<int>(result));
        return false;
    }
    printf("[D-BOX] %s OK\n", context);
    return true;
}

}  // namespace

// ---------------------------------------------------------------------------

DboxMotionController::DboxMotionController(DboxMotionConfig config)
    : config_(config) {}

DboxMotionController::~DboxMotionController() {
    if (started_)     Stop();
    if (opened_)      Close();
    if (initialized_) Terminate();
}

bool DboxMotionController::Initialize(const char* app_key,
                                       unsigned int build_version) {
    auto result = dbox::LiveMotion::Initialize(
        app_key, static_cast<dbox::U32>(build_version));
    if (!CheckResult(result, "Initialize")) return false;

    result = dbox::LiveMotion::RegisterEvent(
        SIM_CONFIG, dbox::EM_CONFIG_UPDATE, SimConfig::GetStructInfo());
    if (!CheckResult(result, "RegisterEvent(SimConfig)")) return false;

    result = dbox::LiveMotion::RegisterEvent(
        MOTION_CONFIG, dbox::EM_CONFIG_UPDATE, MotionConfig::GetStructInfo());
    if (!CheckResult(result, "RegisterEvent(MotionConfig)")) return false;

    result = dbox::LiveMotion::RegisterEvent(
        MOTION_DATA, dbox::EM_FRAME_UPDATE, MotionData::GetStructInfo());
    if (!CheckResult(result, "RegisterEvent(MotionData)")) return false;

    initialized_ = true;
    return true;
}

bool DboxMotionController::Open() {
    auto result = dbox::LiveMotion::Open();
    if (!CheckResult(result, "Open")) return false;

    dbox::LiveMotion::ResetState();

    SimConfig sc{};
    sc.MasterGain     = 0.0f;  // 0 dB
    sc.MasterSpectrum = 0.0f;  // 0 dB
    dbox::LiveMotion::PostEvent(SIM_CONFIG, sc);

    MotionConfig mc{};
    mc.EngineRpmIdle   = 750.0f;
    mc.EngineRpmMax    = 3420.0f;
    mc.EngineTorqueMax = 447.0f;
    dbox::LiveMotion::PostEvent(MOTION_CONFIG, mc);

    opened_ = true;
    return true;
}

bool DboxMotionController::Start() {
    auto result = dbox::LiveMotion::Start();
    if (!CheckResult(result, "Start")) return false;
    started_ = true;
    return true;
}

void DboxMotionController::Stop() {
    dbox::LiveMotion::Stop();
    started_ = false;
}

void DboxMotionController::Close() {
    dbox::LiveMotion::Close();
    opened_ = false;
}

void DboxMotionController::Terminate() {
    dbox::LiveMotion::Terminate();
    initialized_ = false;
}

bool DboxMotionController::IsStarted() const {
    return started_ && static_cast<bool>(dbox::LiveMotion::IsStarted());
}

void DboxMotionController::PostFrame(const VehicleCommand& cmd) {
    if (!started_) return;

    MotionData d{};

    // steering [-1,1] → roll [-1,1]
    d.Roll  = std::max(-1.0f, std::min(1.0f, cmd.steering * config_.roll_gain));

    // throttle - brake → pitch: forward thrust = positive pitch
    d.Pitch = std::max(-1.0f, std::min(1.0f,
        (cmd.throttle - cmd.brake) * config_.pitch_gain));

    // braking → heave down
    d.Heave = std::max(-1.0f, std::min(1.0f, -cmd.brake * config_.heave_gain));

    // engine feel from throttle
    d.EngineRpm    = 750.0f + cmd.throttle * (3420.0f - 750.0f);
    d.EngineTorque = cmd.throttle * 447.0f;

    dbox::LiveMotion::PostEvent(MOTION_DATA, d);
}

}  // namespace simchair
