import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import time
import smbus
import RPi.GPIO as GPIO
import board, busio
from adafruit_ina219 import INA219
import cv2
import numpy as np

# ---------------- DISPLAY ----------------
WIDTH, HEIGHT = 800, 480
pygame.init()
pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
pygame.display.set_caption("Go-Kart Full Dashboard")

# ---------------- OPENGL ----------------
glViewport(0, 0, WIDTH, HEIGHT)
gluPerspective(45, WIDTH / HEIGHT, 0.1, 50.0)
glEnable(GL_DEPTH_TEST)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
glTranslatef(-1.6, -0.6, -6)  # move 3D car left

# ---------------- FONTS ----------------
pygame.font.init()
font_big = pygame.font.SysFont("Arial", 48, bold=True)
font_mid = pygame.font.SysFont("Arial", 28)
font_small = pygame.font.SysFont("Arial", 20)

# ---------------- MPU-6050 ----------------
bus = smbus.SMBus(1)
MPU_ADDR = 0x68
bus.write_byte_data(MPU_ADDR, 0x6B, 0)

def read_word(reg):
    h = bus.read_byte_data(MPU_ADDR, reg)
    l = bus.read_byte_data(MPU_ADDR, reg+1)
    val = (h << 8) + l
    if val >= 0x8000:
        val -= 65536
    return val

def read_gyro():
    gx = read_word(0x43) / 131.0
    gy = read_word(0x45) / 131.0
    gz = read_word(0x47) / 131.0
    return gx, gy, gz

def read_accel():
    ax = read_word(0x3B) / 16384.0
    ay = read_word(0x3D) / 16384.0
    az = read_word(0x3F) / 16384.0
    return ax, ay, az

# ---------------- HALL SENSOR ----------------
SENSOR_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
pulses = 0
WHEEL_CIRCUMFERENCE = 1.117  # meters (14in wheel)

def pulse(channel):
    global pulses
    pulses += 1

GPIO.add_event_detect(SENSOR_PIN, GPIO.FALLING, callback=pulse)

# ---------------- INA219 BATTERY ----------------
i2c = busio.I2C(board.SCL, board.SDA)
ina = INA219(i2c)

def read_battery_percent():
    voltage = ina.bus_voltage + ina.shunt_voltage
    percent = max(0, min(100, int((voltage-22)/(29.2-22)*100)))
    return percent

# ---------------- CAMERA ----------------
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 180)

# ---------------- 3D CAR ----------------
def draw_car():
    glBegin(GL_QUADS)

    glColor3f(0.0, 0.9, 1.0)
    glVertex3f(-1, 0.3, -2)
    glVertex3f(1, 0.3, -2)
    glVertex3f(1, 0.3, 2)
    glVertex3f(-1, 0.3, 2)

    glColor3f(0.0, 0.25, 0.4)
    glVertex3f(-1, 0, -2)
    glVertex3f(1, 0, -2)
    glVertex3f(1, 0, 2)
    glVertex3f(-1, 0, 2)

    glColor3f(0.0, 0.6, 0.85)
    glVertex3f(-1, 0, -2)
    glVertex3f(-1, 0.3, -2)
    glVertex3f(-1, 0.3, 2)
    glVertex3f(-1, 0, 2)

    glVertex3f(1, 0, -2)
    glVertex3f(1, 0.3, -2)
    glVertex3f(1, 0.3, 2)
    glVertex3f(1, 0, 2)

    glEnd()

# ---------------- HUD TEXT ----------------
def draw_text(text, font, x, y):
    surface = font.render(text, True, (0, 255, 255))
    data = pygame.image.tostring(surface, "RGBA", True)
    glWindowPos2d(x, y)
    glDrawPixels(surface.get_width(), surface.get_height(),
                 GL_RGBA, GL_UNSIGNED_BYTE, data)

# ---------------- VARIABLES ----------------
roll = pitch = 0.0
speed = 0.0
miles = 0.0
t = 0.0

clock = pygame.time.Clock()
running = True

# ---------------- MAIN LOOP ----------------
while running:
    dt = clock.tick(60) / 1000
    t += dt

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False

    # ---------------- SENSOR READINGS ----------------
    # MPU-6050
    gx, gy, gz = read_gyro()
    ax, ay, az = read_accel()
    target_roll = gx
    target_pitch = gy
    roll += (target_roll - roll) * 0.1
    pitch += (target_pitch - pitch) * 0.1

    # Speed & miles
    rotations = pulses / 1.0  # 1 pulse per rotation
    speed = (rotations * WHEEL_CIRCUMFERENCE) / dt * 3.6  # km/h
    miles += speed * dt / 3600
    pulses = 0

    # Battery
    battery = read_battery_percent()

    # ---------------- OPENGL RENDER ----------------
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # 3D CAR
    glPushMatrix()
    glRotatef(roll, 0, 0, 1)
    glRotatef(pitch, 1, 0, 0)
    draw_car()
    glPopMatrix()

    # HUD OVERLAY
    glDisable(GL_DEPTH_TEST)

    draw_text(f"BATTERY {battery}%", font_mid, 320, 455)
    draw_text(f"{int(speed)} MPH", font_big, 420, 310)
    draw_text(f"Miles {miles:.1f}", font_mid, 430, 270)

    # Camera preview
    ret, frame = cap.read()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.flip(frame, 0)
        glDrawPixels(frame.shape[1], frame.shape[0], GL_RGB, GL_UNSIGNED_BYTE, frame)

    glEnable(GL_DEPTH_TEST)
    pygame.display.flip()

cap.release()
GPIO.cleanup()
pygame.quit()
