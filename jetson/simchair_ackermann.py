"""
simchair_ackermann.py — car-style (Ackermann-feel) mapping for a diff-drive kart.

The chair wheel picks a curvature, not a spin rate:  ω = v · steer / R_min.
Stopped → no turn; inner track slows but never reverses (R_min > track/2).

Pedals drive a speed state with momentum (all speeds in m/s, REP-103, left = +):
  forward:  gas    → accelerate toward gas · max_fwd; release → coast down
            brake  → decelerate (brake · brake_decel)
  stopped:  brake held (no gas) for rev_hold_s → reverse; gas → forward
  reverse:  brake  → reverse toward brake · max_rev; gas brakes
            gas held at 0 for rev_hold_s → forward

Pure Python (no ROS) so it can be tested anywhere:  python3 simchair_ackermann.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass

PEDAL_ON = 0.05  # pedal travel below this counts as released


def _approach(x: float, target: float, step: float) -> float:
    if x < target:
        return min(target, x + step)
    return max(target, x - step)


@dataclass
class AckermannParams:
    min_radius_m: float = 1.5     # full-lock turn radius
    max_fwd_mps: float = 1.5      # gas fully down
    max_rev_mps: float = 0.5      # brake fully down while in reverse
    accel_mps2: float = 0.3       # ≤ actuator max_linear_accel_mps2 (keeps the arc exact)
    brake_decel_mps2: float = 1.3  # full brake; ≤ actuator max_linear_decel_mps2
    coast_decel_mps2: float = 0.3  # pedals released ("engine drag")
    rev_hold_s: float = 0.5       # hold brake at a stop this long to engage reverse
    lat_accel_mps2: float = 1.0   # speed-sensitive steering cap, 0 = off
    pivot_rps: float = 0.0        # turn rate allowed at a standstill, 0 = pure car
    min_turn_rps: float = 0.06    # keep small turns above actuator heading-hold (0.05)
    max_w_rps: float = 1.5        # actuator max_angular_rps
    track_m: float = 0.7366


class AckermannMapper:
    def __init__(self, p: AckermannParams):
        self.p = p
        self.v = 0.0            # speed state (m/s), + forward
        self.reverse = False    # gear: False = forward, True = reverse
        self._held = 0.0        # time a direction-change pedal has been held at 0

    def reset(self):
        self.v = 0.0
        self.reverse = False
        self._held = 0.0

    def _update_speed(self, gas: float, brake: float, dt: float) -> float:
        p = self.p
        gas = gas if gas > PEDAL_ON else 0.0
        brake = brake if brake > PEDAL_ON else 0.0

        if not self.reverse:
            drive, stop, vmax = gas, brake, p.max_fwd_mps
        else:
            drive, stop, vmax = brake, gas, p.max_rev_mps
        speed = abs(self.v)

        if stop > 0.0:
            # Braking (the pedal that opposes this gear) wins over driving.
            speed = max(0.0, speed - stop * p.brake_decel_mps2 * dt)
            if speed == 0.0 and drive == 0.0:
                self._held += dt
                if self._held >= p.rev_hold_s:
                    self.reverse = not self.reverse
                    self._held = 0.0
            else:
                self._held = 0.0
        else:
            self._held = 0.0
            target = drive * vmax
            if speed < target:
                speed = min(target, speed + p.accel_mps2 * dt)
            else:
                speed = max(target, speed - p.coast_decel_mps2 * dt)

        self.v = -speed if self.reverse else speed
        return self.v

    def _turn_rate(self, steer: float, v: float) -> float:
        p = self.p
        if abs(v) < 0.05:
            return steer * p.pivot_rps
        kappa = steer / p.min_radius_m
        if p.lat_accel_mps2 > 0.0:
            kmax = p.lat_accel_mps2 / (v * v)
            kappa = max(-kmax, min(kmax, kappa))
        w = v * kappa
        if abs(steer) > PEDAL_ON and abs(w) < p.min_turn_rps:
            w = math.copysign(p.min_turn_rps, w)
        return max(-p.max_w_rps, min(p.max_w_rps, w))

    def step(self, steer: float, gas: float, brake: float, dt: float):
        """steer in [-1, 1] REP-103 (left = +). Returns (v, w) in m/s, rad/s."""
        dt = max(0.0, min(dt, 0.2))
        v = self._update_speed(gas, brake, dt)
        return v, self._turn_rate(steer, v)

    def tracks(self, v: float, w: float):
        half = w * self.p.track_m / 2.0
        return v - half, v + half


def _selftest():
    p = AckermannParams()
    m = AckermannMapper(p)
    dt = 0.05

    def run(steer, gas, brake, secs):
        out = (0.0, 0.0)
        for _ in range(int(round(secs / dt))):
            out = m.step(steer, gas, brake, dt)
        return out

    v, w = run(1.0, 0.0, 0.0, 1.0)
    assert v == 0.0 and w == 0.0, 'stopped + full lock must not turn'

    v, w = run(0.0, 1.0, 0.0, 1.0)
    assert abs(v - 0.3) < 1e-6, f'1 s of full gas at 0.3 m/s² → 0.3 m/s, got {v}'
    v, w = run(0.0, 1.0, 0.0, 10.0)
    assert abs(v - p.max_fwd_mps) < 1e-6

    v, w = run(1.0, 0.5, 0.0, 10.0)  # half gas → settle at 0.75 m/s, full left
    assert abs(v - 0.75) < 1e-6
    assert abs(w - 0.75 / p.min_radius_m) < 1e-6, f'ω = v/R, got {w}'
    left, right = m.tracks(v, w)
    assert 0.0 < left < right, 'left turn: inner (left) track slower but still forward'

    v, w = run(0.0, 1.0, 0.0, 10.0)
    v, w = run(1.0, 1.0, 0.0, 0.1)
    assert abs(w) <= p.lat_accel_mps2 / v + 1e-6, 'lateral cap at speed'

    v, w = run(0.0, 0.0, 0.0, 1.0)
    assert abs(v - (1.5 - 0.3)) < 1e-6, 'coast 0.3 m/s²'

    v, w = run(0.0, 0.0, 1.0, 1.2)  # 1.2 m/s stops in 0.92 s, held 0.28 s < rev_hold
    assert v == 0.0 and not m.reverse
    v, w = run(0.0, 0.0, 1.0, 0.3)
    assert m.reverse, 'brake held at a stop → reverse gear'
    v, w = run(0.0, 0.0, 1.0, 5.0)
    assert abs(v + p.max_rev_mps) < 1e-6, f'reverse speed, got {v}'

    v, w = run(1.0, 0.0, 1.0, 0.1)  # reversing + wheel left → body swings right (ω < 0)
    assert w < 0.0

    v, w = run(0.0, 1.0, 0.0, 0.5)  # gas brakes while reversing
    assert v > -p.max_rev_mps and m.reverse
    v, w = run(0.0, 1.0, 0.0, 3.0)
    assert not m.reverse and v > 0.0, 'gas held at a stop → back to forward'

    m.reset()
    run(0.0, 0.3, 0.0, 10.0)
    v, w = run(0.05 + 1e-3, 0.3, 0.0, 0.1)  # tiny steer at 0.45 m/s
    assert abs(w) >= p.min_turn_rps, 'small turns stay above heading-hold deadband'
    print('simchair_ackermann self-test OK')


if __name__ == '__main__':
    _selftest()
