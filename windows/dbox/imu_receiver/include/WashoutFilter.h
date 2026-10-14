#pragma once

/**
 * Classical washout motion cueing filter (Phase 3).
 *
 * Per-axis single-pole filters at 50 Hz:
 *   - LPF (~0.8 Hz): sustained accel → tilt coordination (roll/pitch)
 *   - HPF (~1.5 Hz): transient vertical accel → heave
 *   - Output washout via high-pass on commanded position (implicit decay)
 *
 * All outputs clamped to comfort envelope (default 50% of full range).
 */

class WashoutFilter
{
public:
    WashoutFilter(float sampleHz = 50.0f, float comfortScale = 0.5f);

    /**
     * Update with IMU body-frame linear acceleration (m/s²) and roll/pitch (rad).
     * Returns normalized D-BOX commands in [-comfortScale, +comfortScale].
     */
    void Update(
        float accelX, float accelY, float accelZ,
        float rollRad, float pitchRad,
        float& outPitch, float& outRoll, float& outHeave);

    /** Ramp outputs toward zero (call on packet loss). dt in seconds. */
    void RampToNeutral(float dt);

    void Reset();

    void SetComfortScale(float scale) { m_ComfortScale = scale; }

private:
    float AlphaFromCutoff(float cutoffHz) const;
    float Lpf(float input, float& state, float alpha);
    float Hpf(float input, float& state, float& prevInput, float alpha);
    float RateLimit(float target, float& current, float maxRatePerSec, float dt);
    float Clamp(float v, float lo, float hi) const;

    float m_SampleHz;
    float m_Dt;
    float m_ComfortScale;

    // LPF states (tilt coordination)
    float m_LpfAx{};
    float m_LpfAy{};
    float m_LpfAz{};

    // HPF state (heave)
    float m_HpfAz{};
    float m_PrevAz{};

    // Rate-limited outputs
    float m_OutPitch{};
    float m_OutRoll{};
    float m_OutHeave{};

    // Gains (tune on stands)
    static constexpr float kPitchGain   = 0.15f;  // forward/brake accel → pitch
    static constexpr float kRollGain    = 0.20f;  // lateral accel → roll
    static constexpr float kHeaveGain   = 0.25f;  // vertical transients → heave
    static constexpr float kTiltCutoff  = 0.8f;   // Hz
    static constexpr float kHeaveCutoff = 1.5f;   // Hz
    static constexpr float kMaxTiltRate = 3.0f;   // deg/s equivalent (normalized/s)
};
