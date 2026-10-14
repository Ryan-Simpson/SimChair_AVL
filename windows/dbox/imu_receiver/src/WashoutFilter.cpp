#include "WashoutFilter.h"
#include <cmath>

namespace
{
    constexpr float kRadToNorm = 1.0f / 0.35f;  // ~20 deg full scale → normalize
}

WashoutFilter::WashoutFilter(float sampleHz, float comfortScale)
    : m_SampleHz(sampleHz)
    , m_Dt(1.0f / sampleHz)
    , m_ComfortScale(comfortScale)
{
}

float WashoutFilter::AlphaFromCutoff(float cutoffHz) const
{
    const float tau = 1.0f / (2.0f * 3.14159265f * cutoffHz);
    return m_Dt / (tau + m_Dt);
}

float WashoutFilter::Clamp(float v, float lo, float hi) const
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

float WashoutFilter::Lpf(float input, float& state, float alpha)
{
    state += alpha * (input - state);
    return state;
}

float WashoutFilter::Hpf(float input, float& state, float& prevInput, float alpha)
{
    state = alpha * (state + input - prevInput);
    prevInput = input;
    return state;
}

float WashoutFilter::RateLimit(float target, float& current, float maxRatePerSec, float dt)
{
    const float maxDelta = maxRatePerSec * dt;
    const float delta = target - current;
    if (delta > maxDelta) current += maxDelta;
    else if (delta < -maxDelta) current -= maxDelta;
    else current = target;
    return current;
}

void WashoutFilter::Update(
    float accelX, float accelY, float accelZ,
    float rollRad, float pitchRad,
    float& outPitch, float& outRoll, float& outHeave)
{
    const float alphaTilt  = AlphaFromCutoff(kTiltCutoff);
    const float alphaHeave = AlphaFromCutoff(kHeaveCutoff);

    // Tilt coordination: sustained longitudinal/lateral accel
    const float axLow = Lpf(accelX, m_LpfAx, alphaTilt);
    const float ayLow = Lpf(accelY, m_LpfAy, alphaTilt);

    // Pitch: braking (decel) → pitch forward; accel → pitch back
    float pitchTarget = -kPitchGain * axLow * kRadToNorm;
    // Roll: cornering lateral accel → roll into turn
    float rollTarget  =  kRollGain  * ayLow * kRadToNorm;

    // Blend with fused attitude for sustained turns (optional light mix)
    pitchTarget = 0.7f * pitchTarget + 0.3f * Clamp(pitchRad * kRadToNorm, -1.0f, 1.0f);
    rollTarget  = 0.7f * rollTarget  + 0.3f * Clamp(rollRad  * kRadToNorm, -1.0f, 1.0f);

    // Heave: high-pass vertical accel (bumps)
    const float heaveTarget = kHeaveGain * Hpf(accelZ, m_HpfAz, m_PrevAz, alphaHeave);

    const float limit = m_ComfortScale;
    pitchTarget = Clamp(pitchTarget, -limit, limit);
    rollTarget  = Clamp(rollTarget,  -limit, limit);
    const float heaveClamped = Clamp(heaveTarget, -limit, limit);

    // Rate-limit tilt so operator feels force, not snap rotation
    const float normRate = kMaxTiltRate / 20.0f;  // normalized units per second
    m_OutPitch = RateLimit(pitchTarget, m_OutPitch, normRate, m_Dt);
    m_OutRoll  = RateLimit(rollTarget,  m_OutRoll,  normRate, m_Dt);
    m_OutHeave = heaveClamped;  // heave can be faster

    outPitch = m_OutPitch;
    outRoll  = m_OutRoll;
    outHeave = m_OutHeave;
}

void WashoutFilter::RampToNeutral(float dt)
{
    const float rampRate = m_ComfortScale / 1.0f;  // reach zero in ~1 s
    m_OutPitch = RateLimit(0.0f, m_OutPitch, rampRate, dt);
    m_OutRoll  = RateLimit(0.0f, m_OutRoll,  rampRate, dt);
    m_OutHeave = RateLimit(0.0f, m_OutHeave, rampRate, dt);
}

void WashoutFilter::Reset()
{
    m_LpfAx = m_LpfAy = m_LpfAz = 0.0f;
    m_HpfAz = m_PrevAz = 0.0f;
    m_OutPitch = m_OutRoll = m_OutHeave = 0.0f;
}
