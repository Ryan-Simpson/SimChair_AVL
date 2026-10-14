#include "DBoxManager.h"
#pragma comment(lib, DBOX_LIVEMOTION_LIB)
#include <chrono>

DBoxManager::DBoxManager() : m_IsStreaming(false)
{
    m_SimConfig.MasterGain = 0.0f;      
    m_SimConfig.MasterSpectrum = 0.0f;  

    m_MotionConfig.EngineRpmIdle = 750.0f;
    m_MotionConfig.EngineRpmMax = 3500.0f;
    m_MotionConfig.EngineTorqueMax = 450.0f;

    m_MotionData.Roll = 0.0f;
    m_MotionData.Pitch = 0.0f;
    m_MotionData.Heave = 0.0f;
    m_MotionData.EngineRpm = 1200.0f;
    m_MotionData.EngineTorque = 175.0f;
}

DBoxManager::~DBoxManager()
{
    Shutdown();
}

dbox::ELiveMotionResult DBoxManager::Initialize(const char* appKey, int appBuild)
{
    return dbox::LiveMotion::Initialize(appKey, appBuild);
}

dbox::ELiveMotionResult DBoxManager::RegisterEvent(int eventId, dbox::EEventMeaning type, const dbox::StructInfo& info)
{
    return dbox::LiveMotion::RegisterEvent(eventId, type, info);
}

dbox::ELiveMotionResult DBoxManager::Open()
{
    return dbox::LiveMotion::Open();
}

dbox::ELiveMotionResult DBoxManager::ResetState()
{
    return dbox::LiveMotion::ResetState();
}

dbox::ELiveMotionResult DBoxManager::Start()
{
    return dbox::LiveMotion::Start();
}

dbox::ELiveMotionResult DBoxManager::Stop()
{
    return dbox::LiveMotion::Stop();
}

dbox::ELiveMotionResult DBoxManager::Close()
{
    return dbox::LiveMotion::Close();
}

dbox::ELiveMotionResult DBoxManager::Terminate()
{
    return dbox::LiveMotion::Terminate();
}

void DBoxManager::setTelemetry(float pitch, float roll, float heave, float rpm, float torque)
{
    m_MotionData.Pitch = pitch;
    m_MotionData.Roll = roll;
    m_MotionData.Heave = heave;
    m_MotionData.EngineRpm = rpm;
    m_MotionData.EngineTorque = torque;
}

void DBoxManager::setPitch(float pitch)
{
    m_MotionData.Pitch = pitch;
}

void DBoxManager::setRoll(float roll)
{
    m_MotionData.Roll = roll;
}

void DBoxManager::StartPeriodicStreaming(int eventId, int periodMs)
{
    if (m_IsStreaming) return; 

    m_IsStreaming = true;
    // Launching asynchronously without explicit thread setup
    m_StreamingFuture = std::async(std::launch::async, &DBoxManager::StreamingLoop, this, eventId, periodMs);
}

void DBoxManager::StopPeriodicStreaming()
{
    if (!m_IsStreaming) return;

    m_IsStreaming = false;
    if (m_StreamingFuture.valid())
    {
        m_StreamingFuture.wait(); // Block until loop yields
    }
}

void DBoxManager::UpdateTelemetry(float pitch, float roll, float heave, float rpm, float torque)
{
    m_MotionData.Pitch = pitch;
    m_MotionData.Roll = roll;
    m_MotionData.Heave = heave;
    m_MotionData.EngineRpm = rpm;
    m_MotionData.EngineTorque = torque;
}

bool DBoxManager::ReadTelemetry()
{
    return true; 
}

void DBoxManager::StreamingLoop(int eventId, int periodMs)
{
    while (m_IsStreaming)
    {
        dbox::LiveMotion::PostEvent(eventId, m_MotionData);
        std::this_thread::sleep_for(std::chrono::milliseconds(periodMs));
    }
}

void DBoxManager::Shutdown()
{
    StopPeriodicStreaming(); 
    dbox::LiveMotion::Stop();
    dbox::LiveMotion::Close();
    dbox::LiveMotion::Terminate();
}
