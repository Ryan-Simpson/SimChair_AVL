#pragma once

#include "dboxLiveMotion.h"
#include <future>

// Fixed event identifiers required by the D-BOX hardware API profiles
enum AppEvents
{
    SIM_CONFIG = 1000,
    MOTION_CONFIG = 2000,
    MOTION_DATA = 3000,
};

struct SimConfig
{
    dbox::F32 MasterGain;
    dbox::F32 MasterSpectrum;

    DBOX_STRUCTINFO_BEGIN()
        DBOX_STRUCTINFO_FIELD(SimConfig, MasterGain, dbox::FT_FLOAT32, dbox::FM_MASTER_GAIN_DB)
        DBOX_STRUCTINFO_FIELD(SimConfig, MasterSpectrum, dbox::FT_FLOAT32, dbox::FM_MASTER_SPECTRUM_DB)
    DBOX_STRUCTINFO_END()
};

struct MotionConfig
{
    dbox::F32 EngineRpmIdle;
    dbox::F32 EngineRpmMax;
    dbox::F32 EngineTorqueMax;

    DBOX_STRUCTINFO_BEGIN()
        DBOX_STRUCTINFO_FIELD(MotionConfig, EngineRpmIdle, dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM_IDLE)
        DBOX_STRUCTINFO_FIELD(MotionConfig, EngineRpmMax, dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM_MAX)
        DBOX_STRUCTINFO_FIELD(MotionConfig, EngineTorqueMax, dbox::FT_FLOAT32, dbox::FM_ENGINE_TORQUE_MAX)
    DBOX_STRUCTINFO_END()
};

struct MotionData
{
    dbox::F32 Roll;         
    dbox::F32 Pitch;        
    dbox::F32 Heave;        
    dbox::F32 EngineRpm;
    dbox::F32 EngineTorque;

    DBOX_STRUCTINFO_BEGIN()
        DBOX_STRUCTINFO_FIELD(MotionData, Roll, dbox::FT_FLOAT32, dbox::FM_RAW_ROLL)
        DBOX_STRUCTINFO_FIELD(MotionData, Pitch, dbox::FT_FLOAT32, dbox::FM_RAW_PITCH)
        DBOX_STRUCTINFO_FIELD(MotionData, Heave, dbox::FT_FLOAT32, dbox::FM_RAW_HEAVE)
        DBOX_STRUCTINFO_FIELD(MotionData, EngineRpm, dbox::FT_FLOAT32, dbox::FM_ENGINE_RPM)
        DBOX_STRUCTINFO_FIELD(MotionData, EngineTorque, dbox::FT_FLOAT32, dbox::FM_ENGINE_TORQUE)
    DBOX_STRUCTINFO_END()
};

class DBoxManager
{
public:
    DBoxManager();
    ~DBoxManager();

    dbox::ELiveMotionResult Initialize(const char* appKey, int appBuild);
    dbox::ELiveMotionResult RegisterEvent(int eventId, dbox::EEventMeaning type, const dbox::StructInfo& info);
    dbox::ELiveMotionResult Open();
    dbox::ELiveMotionResult ResetState();

    template <typename T>
    dbox::ELiveMotionResult PostEvent(int eventId, const T& data)
    {
        return dbox::LiveMotion::PostEvent(eventId, data);
    }

    dbox::ELiveMotionResult Start();
    dbox::ELiveMotionResult Stop();
    dbox::ELiveMotionResult Close();
    dbox::ELiveMotionResult Terminate();
    
    void Shutdown();

    // Async tasks
    void StartPeriodicStreaming(int eventId, int periodMs);
    void StopPeriodicStreaming();

    void setTelemetry(float pitch, float roll, float heave, float rpm, float torque);
    void setPitch(float pitch);
    void setRoll(float roll);

    void UpdateTelemetry(float pitch, float roll, float heave, float rpm = 0.0f, float torque = 0.0f);
    bool ReadTelemetry();

    SimConfig& GetSimConfig() { return m_SimConfig; }
    MotionConfig& GetMotionConfig() { return m_MotionConfig; }
    MotionData& GetMotionData() { return m_MotionData; }

private:
    void StreamingLoop(int eventId, int periodMs);

    SimConfig m_SimConfig;
    MotionConfig m_MotionConfig;
    MotionData m_MotionData;

    // Async state tracking
    std::future<void> m_StreamingFuture;
    bool m_IsStreaming;
};