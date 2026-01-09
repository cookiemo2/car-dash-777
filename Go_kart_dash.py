import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math

# ---------------- DISPLAY ----------------
WIDTH, HEIGHT = 800, 480
pygame.init()
pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
pygame.display.set_caption("Go-Kart Dashboard")

# ---------------- OPENGL ----------------
glViewport(0, 0, WIDTH, HEIGHT)
gluPerspective(45, WIDTH / HEIGHT, 0.1, 50.0)
glEnable(GL_DEPTH_TEST)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

# ---------------- FONTS ----------------
pygame.font.init()
font_big = pygame.font.SysFont("Arial", 48, bold=True)
font_mid = pygame.font.SysFont("Arial", 28)
font_small = pygame.font.SysFont("Arial", 20)

# ---------------- CAMERA ----------------
glTranslatef(-1.6, -0.6, -6)  # Move car LEFT

# ---------------- 3D CAR MODEL ----------------
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
battery = 92
miles = 12.4
t = 0.0

clock = pygame.time.Clock()
running = True

# ---------------- MAIN LOOP ----------------
while running:
    dt = clock.tick(60) / 1000
    t += dt * 2

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False

    # Simulated IMU
    target_roll = math.sin(t) * 12
    target_pitch = math.cos(t * 0.7) * 8

    roll += (target_roll - roll) * 0.1
    pitch += (target_pitch - pitch) * 0.1

    # Simulated speed & mileage
    speed = abs(math.sin(t)) * 45
    miles += speed * dt / 3600

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # -------- 3D CAR --------
    glPushMatrix()
    glRotatef(roll, 0, 0, 1)
    glRotatef(pitch, 1, 0, 0)
    draw_car()
    glPopMatrix()

    # -------- HUD --------
    glDisable(GL_DEPTH_TEST)

    # Battery (TOP CENTER)
    draw_text(f"BATTERY {battery}%", font_mid, 320, 455)

    # Speed & mileage (RIGHT)
    draw_text(f"{int(speed)} MPH", font_big, 420, 310)
    draw_text(f"Miles {miles:.1f}", font_mid, 430, 270)

    # Camera preview (BOTTOM RIGHT)
    glColor4f(0.0, 0.2, 0.3, 0.85)
    glBegin(GL_QUADS)
    glVertex2f(520, 40)
    glVertex2f(780, 40)
    glVertex2f(780, 200)
    glVertex2f(520, 200)
    glEnd()

    draw_text("CAMERA", font_small, 610, 125)

    glEnable(GL_DEPTH_TEST)

    pygame.display.flip()

pygame.quit()
