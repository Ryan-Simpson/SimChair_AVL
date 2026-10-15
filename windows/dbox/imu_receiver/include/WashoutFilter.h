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

// Defaults from the 2026-10-14 drive: heave 0.25 buried acceleration under
// track buzz, and pitch 0.15 at 3 deg/s gave only ~0.09 for Marvin's
// 0.3 m/s^2 ramp. Override per run with imu_haptic_receiver.exe flags.
struct WashoutGains
{
    float pitch       = 0.60f;  // forward/brake accel -> pitch (negative flips direction)
    float roll        = 0.40f;  // lateral accel -> roll
    float yaw         = 0.30f;  // yaw rate (rad/s) -> roll, so pivot turns are felt
    float heave       = 0.0f;   // vertical transients -> heave (off: felt as constant buzz)
    float tiltCutoff  = 0.8f;   // Hz, LPF on accel for tilt
    float heaveCutoff = 1.5f;   // Hz, HPF on vertical accel
    float tiltRate    = 0.6f;   // normalized units/s, tilting away from centre
    float releaseRate = 0.15f;  // normalized units/s, tilting back: a 1.3 s speed-up
                                // holds ~2-3 s and feels like a push, not a bump
    float attitude    = 0.0f;   // share of ground roll/pitch copied (was 0.3: random pitching)
};

class WashoutFilter
{
public:
    WashoutFilter(float sampleHz = 50.0f, float comfortScale = 0.5f,
                  const WashoutGains& gains = WashoutGains{});

    /**
     * Update with IMU body-frame linear acceleration (m/s²) and roll/pitch (rad).
     * Returns normalized D-BOX commands in [-comfortScale, +comfortScale].
     */
    void Update(
        float accelX, float accelY, float accelZ,
        float rollRad, float pitchRad, float yawRate,
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
    float m_LpfYaw{};

    // HPF state (heave)
    float m_HpfAz{};
    float m_PrevAz{};

    // Rate-limited outputs
    float m_OutPitch{};
    float m_OutRoll{};
    float m_OutHeave{};

    WashoutGains m_Gains;
};
