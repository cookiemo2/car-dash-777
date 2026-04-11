"""
Go-Kart Dashboard — Simulation Mode
=====================================
Runs the sensor & display system WITHOUT Raspberry Pi hardware.
All sensors (hall effect, MPU-6050, INA219, camera) are simulated so the
dashboard can be tested and demonstrated on any machine with pygame + OpenGL.

The simulated hall sensor generates pulses that correspond to a known
"actual" speed profile, allowing visual verification that the calibrated
speed readout tracks the real speed accurately.
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import time
import collections

# ================================================================
#  HALL-SENSOR CALIBRATION CONSTANTS  (must match Go_kart_dash22.py)
# ================================================================
WHEEL_CIRCUMFERENCE = 1.117   # metres  (14-inch wheel)
MAGNETS_PER_ROTATION = 1      # magnets on the wheel
MPS_TO_MPH = 2.23694          # m/s  ->  MPH
SPEED_WINDOW_SIZE = 10        # moving-average window (frames)

# ================================================================
#  SIMULATED SENSOR STATE
# ================================================================
pulses = 0
speed_history = collections.deque(maxlen=SPEED_WINDOW_SIZE)

# Simulated IMU state
sim_roll = 0.0
sim_pitch = 0.0

# Simulated battery
sim_battery = 92

# ================================================================
#  DISPLAY SETUP
# ================================================================
WIDTH, HEIGHT = 800, 480
pygame.init()
pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
pygame.display.set_caption("Go-Kart Dashboard  [SIMULATION]")

glViewport(0, 0, WIDTH, HEIGHT)
gluPerspective(45, WIDTH / HEIGHT, 0.1, 50.0)
glEnable(GL_DEPTH_TEST)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
glTranslatef(-1.6, -0.6, -6)

pygame.font.init()
font_big = pygame.font.SysFont("Arial", 48, bold=True)
font_mid = pygame.font.SysFont("Arial", 28)
font_small = pygame.font.SysFont("Arial", 20)

# ================================================================
#  DRAWING HELPERS
# ================================================================
def draw_car():
    glBegin(GL_QUADS)
    glColor3f(0.0, 0.9, 1.0)
    glVertex3f(-1, 0.3, -2); glVertex3f(1, 0.3, -2)
    glVertex3f(1, 0.3,  2); glVertex3f(-1, 0.3,  2)

    glColor3f(0.0, 0.25, 0.4)
    glVertex3f(-1, 0, -2); glVertex3f(1, 0, -2)
    glVertex3f(1, 0,  2); glVertex3f(-1, 0,  2)

    glColor3f(0.0, 0.6, 0.85)
    glVertex3f(-1, 0, -2); glVertex3f(-1, 0.3, -2)
    glVertex3f(-1, 0.3, 2); glVertex3f(-1, 0,  2)

    glVertex3f(1, 0, -2); glVertex3f(1, 0.3, -2)
    glVertex3f(1, 0.3, 2); glVertex3f(1, 0,  2)
    glEnd()


def draw_text(text, font, x, y, color=(0, 255, 255)):
    surface = font.render(text, True, color)
    data = pygame.image.tostring(surface, "RGBA", True)
    glWindowPos2d(x, y)
    glDrawPixels(surface.get_width(), surface.get_height(),
                 GL_RGBA, GL_UNSIGNED_BYTE, data)

# ================================================================
#  SIMULATED SENSOR FUNCTIONS
# ================================================================
def simulate_hall_pulses(actual_speed_mph, dt):
    """Generate the correct number of hall-sensor pulses for a given
    actual wheel speed (MPH) over time interval dt (seconds)."""
    speed_mps = actual_speed_mph / MPS_TO_MPH          # -> m/s
    distance_m = speed_mps * dt                         # metres travelled
    rotations = distance_m / WHEEL_CIRCUMFERENCE        # wheel rotations
    total_pulses = rotations * MAGNETS_PER_ROTATION     # pulses (float)
    return total_pulses  # fractional; we accumulate before rounding


def simulate_imu(t):
    """Return (roll, pitch) in degrees — gentle sinusoidal rocking."""
    roll = math.sin(t) * 12
    pitch = math.cos(t * 0.7) * 8
    return roll, pitch

# ================================================================
#  MAIN LOOP
# ================================================================
roll = pitch = 0.0
speed = 0.0
miles = 0.0
t = 0.0
pulse_accumulator = 0.0   # accumulates fractional pulses

clock = pygame.time.Clock()
running = True

while running:
    dt = clock.tick(60) / 1000.0
    if dt <= 0:
        dt = 1 / 60.0
    t += dt

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False

    # ---------- simulated "actual" speed profile (MPH) ----------
    actual_speed_mph = abs(math.sin(t * 0.5)) * 35  # 0-35 MPH wave

    # ---------- simulate hall sensor pulses ----------------------
    pulse_accumulator += simulate_hall_pulses(actual_speed_mph, dt)
    pulses = int(pulse_accumulator)
    pulse_accumulator -= pulses

    # ---------- CALIBRATED speed calculation (same as Go_kart_dash22) --
    rotations = pulses / MAGNETS_PER_ROTATION
    instant_speed = (rotations * WHEEL_CIRCUMFERENCE) / dt * MPS_TO_MPH
    speed_history.append(instant_speed)
    speed = sum(speed_history) / len(speed_history)   # smoothed MPH
    miles += speed * dt / 3600

    # ---------- simulated IMU -----------------------------------
    target_roll, target_pitch = simulate_imu(t)
    roll += (target_roll - roll) * 0.1
    pitch += (target_pitch - pitch) * 0.1

    # ---------- RENDER ------------------------------------------
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glPushMatrix()
    glRotatef(roll, 0, 0, 1)
    glRotatef(pitch, 1, 0, 0)
    draw_car()
    glPopMatrix()

    glDisable(GL_DEPTH_TEST)

    # HUD
    draw_text(f"BATTERY {sim_battery}%", font_mid, 320, 455)
    draw_text(f"{int(speed)} MPH", font_big, 420, 310)
    draw_text(f"Miles {miles:.1f}", font_mid, 430, 270)

    # Show actual vs measured for debugging
    draw_text("[SIMULATION MODE]", font_small, 10, 455, (255, 200, 0))
    draw_text(f"Actual:  {actual_speed_mph:.1f} MPH", font_small, 10, 90, (0, 255, 100))
    draw_text(f"Sensor:  {speed:.1f} MPH", font_small, 10, 65, (0, 200, 255))
    error = abs(speed - actual_speed_mph)
    draw_text(f"Error:   {error:.1f} MPH", font_small, 10, 40, (255, 100, 100))

    # Camera placeholder
    glColor4f(0.0, 0.2, 0.3, 0.85)
    glBegin(GL_QUADS)
    glVertex2f(520, 40); glVertex2f(780, 40)
    glVertex2f(780, 200); glVertex2f(520, 200)
    glEnd()
    draw_text("CAMERA [SIM]", font_small, 600, 125)

    glEnable(GL_DEPTH_TEST)
    pygame.display.flip()

pygame.quit()
