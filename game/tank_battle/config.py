"""Constants, colors, and sound synthesis for Tank Battle."""

import os
import pygame

# ── Font ────────────────────────────────────────────────────
_FONT_PATH = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'),
                          'Fonts', 'simhei.ttf')
if not os.path.exists(_FONT_PATH):
    _FONT_PATH = None  # fallback to default


def get_font(size):
    """Return a pygame Font, preferring SimHei for Chinese support."""
    if _FONT_PATH:
        return pygame.font.Font(_FONT_PATH, size)
    return pygame.font.Font(None, size)

# ── Grid & Display ──────────────────────────────────────────
TILE = 20
MAP_W = 26
MAP_H = 26
PLAYFIELD_W = MAP_W * TILE
PLAYFIELD_H = MAP_H * TILE
SIDEBAR_W = 240
SCREEN_W = PLAYFIELD_W + SIDEBAR_W
SCREEN_H = PLAYFIELD_H

# ── Timing & Gameplay ──────────────────────────────────────
FPS = 60
PLAYER_SPEED = 100
BULLET_SPEED = 200
ENEMY_BASE_SPEED = 60
ENEMY_FAST_SPEED = 100
MAX_PLAYER_BULLETS = 1
MAX_ENEMY_BULLETS = 1
MAX_ENEMIES_ON_FIELD = 4
ENEMIES_PER_LEVEL = 20
PLAYER_LIVES = 3
SPAWN_INTERVAL = 3.0
ENEMY_SHOOT_COOLDOWN = 1.5
PLAYER_SHOOT_COOLDOWN = 0.4
INVINCIBLE_TIME = 3.0
BASE_PROTECT_TIME = 10.0
FREEZE_TIME = 6.0

# ── Tile Types ──────────────────────────────────────────────
EMPTY = 0
BRICK = 1
STEEL = 2
BASE = 3
WATER = 4
TREE = 5
ICE = 6

# ── Directions ──────────────────────────────────────────────
DIR_UP = 0
DIR_RIGHT = 1
DIR_DOWN = 2
DIR_LEFT = 3

DIR_VECTORS = {
    DIR_UP: (0, -1),
    DIR_RIGHT: (1, 0),
    DIR_DOWN: (0, 1),
    DIR_LEFT: (-1, 0),
}

# ── Colors ─────────────────────────────────────────────────
COLOR_BG = (15, 15, 15)
COLOR_PLAYFIELD_BG = (40, 40, 40)
COLOR_BRICK = (180, 80, 40)
COLOR_BRICK_MORTAR = (140, 60, 30)
COLOR_STEEL = (160, 160, 170)
COLOR_STEEL_DARK = (120, 120, 130)
COLOR_BASE = (200, 180, 20)
COLOR_WATER = (40, 80, 180)
COLOR_WATER_LIGHT = (60, 110, 210)
COLOR_TREE = (30, 120, 40)
COLOR_TREE_DARK = (20, 90, 30)
COLOR_ICE = (180, 210, 230)
COLOR_ICE_LINE = (150, 180, 200)
COLOR_SIDEBAR = (30, 30, 30)
COLOR_TEXT = (220, 220, 220)
COLOR_TEXT_DIM = (150, 150, 150)
COLOR_PLAYER = (255, 220, 60)
COLOR_PLAYER_DARK = (200, 170, 40)
COLOR_PLAYER_STAR1 = (100, 255, 100)
COLOR_PLAYER_STAR2 = (80, 220, 80)
COLOR_PLAYER_STAR3 = (60, 200, 60)
COLOR_ENEMY_BASIC = (200, 200, 210)
COLOR_ENEMY_FAST = (100, 180, 255)
COLOR_ENEMY_POWER = (100, 255, 100)
COLOR_ENEMY_ARMOR = (240, 240, 100)
COLOR_ENEMY_SCOUT = (80, 220, 220)
COLOR_ENEMY_HEAVY = (200, 70, 70)
COLOR_ENEMY_SNIPER = (180, 130, 220)
COLOR_ENEMY_BOSS = (220, 180, 40)
COLOR_BULLET = (255, 255, 200)
COLOR_BULLET_POWER = (255, 100, 100)

# ── Sound (lazy-initialised after pygame.mixer.init) ───────
snd_shoot = None
snd_shoot_player = None
snd_explosion = None
snd_brick = None
snd_steel = None
snd_powerup = None
snd_gameover = None
snd_stage_start = None
snd_base_hit = None


def _make_sound(freq, duration, volume=0.3):
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = bytearray()
    period = int(sample_rate / freq)
    for i in range(n_samples):
        if (i % period) < period // 2:
            buf.append(int(128 + 127 * volume))
        else:
            buf.append(int(128 - 127 * volume))
    return pygame.mixer.Sound(bytes(buf))


def init_sounds():
    global snd_shoot, snd_shoot_player, snd_explosion, snd_brick, snd_steel
    global snd_powerup, snd_gameover, snd_stage_start, snd_base_hit
    snd_shoot = _make_sound(800, 0.06, 0.2)
    snd_shoot_player = _make_sound(600, 0.08, 0.25)
    snd_explosion = _make_sound(80, 0.2, 0.3)
    snd_brick = _make_sound(200, 0.1, 0.15)
    snd_steel = _make_sound(400, 0.06, 0.1)
    snd_powerup = _make_sound(1200, 0.12, 0.25)
    snd_gameover = _make_sound(150, 0.5, 0.3)
    snd_stage_start = _make_sound(500, 0.3, 0.25)
    snd_base_hit = _make_sound(60, 0.4, 0.35)
