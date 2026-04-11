"""
Hall Sensor Calibration Comparison
====================================
Compares the OLD (uncalibrated) speed calculation with the NEW (calibrated)
calculation against known actual wheel speeds.

Outputs a text report and a PNG chart showing:
  - Actual speed profile
  - Old (raw) sensor reading  (km/h mislabelled as MPH, no smoothing)
  - New (calibrated) sensor reading  (true MPH, moving-average smoothed)

Run:  python3 calibration_comparison.py
"""

import math
import collections
import os

# Try to import matplotlib for chart generation
try:
    import matplotlib
    matplotlib.use("Agg")  # headless backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ================================================================
#  CALIBRATION CONSTANTS
# ================================================================
WHEEL_CIRCUMFERENCE = 1.117   # metres (14-inch wheel)
MAGNETS_PER_ROTATION = 1      # magnets on the wheel
MPS_TO_MPH = 2.23694          # m/s -> MPH
SPEED_WINDOW_SIZE = 10        # moving-average window (frames)

# Simulation parameters
FPS = 60
DURATION_S = 20               # seconds of simulated driving
DT = 1.0 / FPS

# ================================================================
#  SPEED PROFILE  — "actual" wheel speed over time
# ================================================================
def actual_speed_mph(t):
    """Sinusoidal 0-35 MPH speed profile."""
    return abs(math.sin(t * 0.5)) * 35


def generate_pulses(speed_mph, dt):
    """Return fractional pulses produced by a hall sensor at the given speed."""
    speed_mps = speed_mph / MPS_TO_MPH
    distance_m = speed_mps * dt
    rotations = distance_m / WHEEL_CIRCUMFERENCE
    return rotations * MAGNETS_PER_ROTATION


# ================================================================
#  OLD (UNCALIBRATED) speed formula  — from original Go_kart_dash22.py
# ================================================================
def old_speed_calc(pulse_count, dt):
    """Original code:  rotations = pulses / 1.0
       speed = (rotations * WHEEL_CIRCUMFERENCE) / dt * 3.6   # <-- km/h!
    Displayed as MPH but actually km/h."""
    rotations = pulse_count / 1.0
    return (rotations * WHEEL_CIRCUMFERENCE) / dt * 3.6  # km/h (mislabelled)


# ================================================================
#  NEW (CALIBRATED) speed formula  — fixed version
# ================================================================
def new_speed_calc(pulse_count, dt):
    """Calibrated: proper unit conversion to MPH."""
    rotations = pulse_count / MAGNETS_PER_ROTATION
    return (rotations * WHEEL_CIRCUMFERENCE) / dt * MPS_TO_MPH  # true MPH


# ================================================================
#  RUN SIMULATION
# ================================================================
times = []
actual_speeds = []
old_speeds = []
new_speeds_raw = []
new_speeds_smoothed = []

pulse_accumulator = 0.0
old_history = collections.deque(maxlen=1)       # no smoothing (original)
new_history = collections.deque(maxlen=SPEED_WINDOW_SIZE)

for frame in range(int(DURATION_S * FPS)):
    t = frame * DT
    a_speed = actual_speed_mph(t)

    # Generate pulses
    pulse_accumulator += generate_pulses(a_speed, DT)
    p = int(pulse_accumulator)
    pulse_accumulator -= p

    # Old calculation
    old_spd = old_speed_calc(p, DT)
    old_history.append(old_spd)

    # New calculation
    new_spd_raw = new_speed_calc(p, DT)
    new_history.append(new_spd_raw)
    new_spd_smooth = sum(new_history) / len(new_history)

    times.append(t)
    actual_speeds.append(a_speed)
    old_speeds.append(old_spd)
    new_speeds_raw.append(new_spd_raw)
    new_speeds_smoothed.append(new_spd_smooth)


# ================================================================
#  ERROR METRICS
# ================================================================
def rmse(predicted, actual):
    return math.sqrt(sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(actual))

def mae(predicted, actual):
    return sum(abs(p - a) for p, a in zip(predicted, actual)) / len(actual)

def max_error(predicted, actual):
    return max(abs(p - a) for p, a in zip(predicted, actual))


old_rmse  = rmse(old_speeds, actual_speeds)
old_mae   = mae(old_speeds, actual_speeds)
old_max   = max_error(old_speeds, actual_speeds)

new_raw_rmse  = rmse(new_speeds_raw, actual_speeds)
new_raw_mae   = mae(new_speeds_raw, actual_speeds)
new_raw_max   = max_error(new_speeds_raw, actual_speeds)

new_smooth_rmse = rmse(new_speeds_smoothed, actual_speeds)
new_smooth_mae  = mae(new_speeds_smoothed, actual_speeds)
new_smooth_max  = max_error(new_speeds_smoothed, actual_speeds)


# ================================================================
#  TEXT REPORT
# ================================================================
report = f"""
================================================================================
  HALL SENSOR CALIBRATION COMPARISON REPORT
================================================================================

  Simulation: {DURATION_S}s at {FPS} FPS ({len(times)} frames)
  Speed profile: sinusoidal 0-35 MPH
  Wheel circumference: {WHEEL_CIRCUMFERENCE} m  (14-inch wheel)
  Magnets per rotation: {MAGNETS_PER_ROTATION}

--------------------------------------------------------------------------------
  ISSUES FOUND IN ORIGINAL CODE (Go_kart_dash22.py)
--------------------------------------------------------------------------------
  1. UNIT MISMATCH: Speed computed as km/h (* 3.6) but displayed as "MPH".
     The original formula:
       speed = (rotations * WHEEL_CIRCUMFERENCE) / dt * 3.6   # km/h
     ... is displayed on the HUD as "MPH", making the readout ~60% too high
     at all speeds (1 km/h = 0.621 mph; the ratio 3.6/2.237 = 1.609).

  2. NO SMOOTHING: Each frame calculates speed from integer pulse counts over
     a ~16 ms window.  A single extra or missing pulse causes huge spikes.

  3. PER-FRAME NOISE: At 60 FPS the time window is only 16.7 ms.  For a
     14-inch wheel at 10 MPH, only ~0.47 pulses arrive per frame, so the
     reading alternates between 0 and a large value every frame.

--------------------------------------------------------------------------------
  CALIBRATION FIXES APPLIED
--------------------------------------------------------------------------------
  1. Replaced * 3.6 (m/s -> km/h) with * 2.23694 (m/s -> MPH).
  2. Added MAGNETS_PER_ROTATION constant (divides pulse count correctly).
  3. Added {SPEED_WINDOW_SIZE}-frame moving-average smoothing on speed.

--------------------------------------------------------------------------------
  ERROR METRICS  (vs. actual speed)
--------------------------------------------------------------------------------
  Method                       RMSE (MPH)   MAE (MPH)   Max Error (MPH)
  -------------------------    ----------   ---------   ---------------
  OLD  (raw, km/h as MPH)     {old_rmse:10.2f}   {old_mae:9.2f}   {old_max:15.2f}
  NEW  (calibrated, raw)       {new_raw_rmse:10.2f}   {new_raw_mae:9.2f}   {new_raw_max:15.2f}
  NEW  (calibrated, smoothed)  {new_smooth_rmse:10.2f}   {new_smooth_mae:9.2f}   {new_smooth_max:15.2f}

--------------------------------------------------------------------------------
  SAMPLE READINGS  (every 2 seconds)
--------------------------------------------------------------------------------
  Time(s)   Actual(MPH)   Old(km/h->"MPH")   New-Raw(MPH)   New-Smooth(MPH)
  -------   -----------   ----------------   ------------   ---------------"""

for i in range(0, len(times), FPS * 2):
    report += (
        f"\n  {times[i]:7.1f}   {actual_speeds[i]:11.1f}   "
        f"{old_speeds[i]:16.1f}   {new_speeds_raw[i]:12.1f}   "
        f"{new_speeds_smoothed[i]:15.1f}"
    )

report += """

================================================================================
  CONCLUSION
================================================================================
  The calibrated + smoothed speed closely tracks the actual wheel speed in MPH.
  The old formula read ~61% too high because it used km/h conversion (3.6)
  while labelling the output as MPH (should use 2.23694).
  Smoothing eliminates the pulse-quantisation noise inherent in per-frame
  calculation with low pulse counts.
================================================================================
"""

print(report)

# Save report to file
report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "calibration_report.txt")
with open(report_path, "w") as f:
    f.write(report)
print(f"Report saved to: {report_path}")


# ================================================================
#  CHART  (if matplotlib available)
# ================================================================
if HAS_MATPLOTLIB:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Top panel: speed comparison
    ax1.plot(times, actual_speeds, "g-", linewidth=2, label="Actual Speed (MPH)")
    ax1.plot(times, old_speeds, "r-", alpha=0.5, linewidth=1,
             label='Old Reading (km/h shown as "MPH")')
    ax1.plot(times, new_speeds_smoothed, "c-", linewidth=2,
             label="New Calibrated + Smoothed (MPH)")
    ax1.set_ylabel("Speed (MPH)")
    ax1.set_title("Hall Sensor Calibration: Actual vs Sensor Readings")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)

    # Bottom panel: error
    old_error = [o - a for o, a in zip(old_speeds, actual_speeds)]
    new_error = [n - a for n, a in zip(new_speeds_smoothed, actual_speeds)]
    ax2.plot(times, old_error, "r-", alpha=0.5, linewidth=1, label="Old Error")
    ax2.plot(times, new_error, "c-", linewidth=1, label="New Calibrated Error")
    ax2.axhline(y=0, color="g", linestyle="--", alpha=0.5)
    ax2.set_ylabel("Error (MPH)")
    ax2.set_xlabel("Time (seconds)")
    ax2.set_title("Speed Error Over Time")
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    chart_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "calibration_chart.png")
    plt.savefig(chart_path, dpi=150)
    print(f"Chart saved to: {chart_path}")
else:
    print("matplotlib not available — chart not generated.")
    print("Install with: pip3 install matplotlib")
