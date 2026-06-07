"""Visual effects and bullets for Tank Battle."""

import random
import pygame

from .config import (
    TILE, PLAYFIELD_W, PLAYFIELD_H, MAP_W, MAP_H,
    BRICK, STEEL, BASE, EMPTY, WATER, TREE, ICE,
    DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT,
    BULLET_SPEED, COLOR_BRICK, COLOR_BULLET, COLOR_BULLET_POWER,
    get_font,
)


# ── Particle ──────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, life=0.5):
        self.x = x
        self.y = y
        self.vx = random.uniform(-80, 80)
        self.vy = random.uniform(-120, -40)
        self.life = life
        self.max_life = life
        self.color = color
        self.size = random.randint(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 300 * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    @property
    def alpha(self):
        return int(255 * (self.life / self.max_life))


# ── Explosion ─────────────────────────────────────────────
class Explosion:
    def __init__(self, x, y, big=False):
        self.x = x
        self.y = y
        self.timer = 0.4 if not big else 0.6
        self.max_timer = self.timer
        self.big = big

    @property
    def alive(self):
        return self.timer > 0

    def update(self, dt):
        self.timer -= dt

    def draw(self, surface, offset_x=0, offset_y=0):
        progress = 1 - (self.timer / self.max_timer)
        radius = int(20 * progress) if not self.big else int(35 * progress)
        alpha = int(255 * (1 - progress))
        if radius > 0:
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            colors = [(255, 200, 50, alpha), (255, 100, 0, alpha // 2)]
            for i, c in enumerate(colors):
                r = radius - i * 4
                if r > 0:
                    pygame.draw.circle(s, c, (radius, radius), r)
            surface.blit(s, (int(self.x - radius + offset_x),
                             int(self.y - radius + offset_y)))


# ── Bullet ────────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, direction, owner, power=False):
        self.x = x
        self.y = y
        self.direction = direction
        self.owner = owner
        self.power = power
        self.speed = BULLET_SPEED
        self.size = 4
        self.alive = True

    def rect(self):
        hs = self.size // 2
        return pygame.Rect(int(self.x - hs), int(self.y - hs),
                           self.size, self.size)

    def update(self, dt, game_map):
        from .config import DIR_VECTORS
        dx, dy = DIR_VECTORS[self.direction]
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt

        if (self.x < 0 or self.x > PLAYFIELD_W or
                self.y < 0 or self.y > PLAYFIELD_H):
            self.alive = False
            return 'out'

        tile_x = int(self.x // TILE)
        tile_y = int(self.y // TILE)
        if 0 <= tile_x < MAP_W and 0 <= tile_y < MAP_H:
            tile = game_map[tile_y][tile_x]
            if tile == BRICK:
                self._destroy_brick_strip(game_map, tile_x, tile_y,
                                          self.direction)
                self.alive = False
                return 'brick'
            elif tile == STEEL:
                if self.power:
                    self._destroy_brick_strip(game_map, tile_x, tile_y,
                                              self.direction, STEEL)
                    self.alive = False
                    return 'brick'
                self.alive = False
                return 'steel'
            elif tile == BASE:
                game_map[tile_y][tile_x] = EMPTY
                self.alive = False
                return 'base'
            elif tile in (WATER, TREE, ICE):
                pass  # bullets pass through

    @staticmethod
    def _destroy_brick_strip(game_map, cx, cy, direction, target_tile=BRICK):
        """Destroy 2 tiles perpendicular to bullet direction.
        Vertical bullet -> destroy horizontal strip (2 tiles in same row).
        Horizontal bullet -> destroy vertical strip (2 tiles in same col).
        """
        game_map[cy][cx] = EMPTY
        bx = (cx // 2) * 2
        by = (cy // 2) * 2
        if direction in (DIR_UP, DIR_DOWN):
            other_cx = bx + (1 if cx == bx else 0)
            other_cy = cy
        else:
            other_cx = cx
            other_cy = by + (1 if cy == by else 0)
        if 0 <= other_cx < MAP_W and 0 <= other_cy < MAP_H:
            if game_map[other_cy][other_cx] == target_tile:
                game_map[other_cy][other_cx] = EMPTY


# ── Power-Up ──────────────────────────────────────────────
class PowerUp:
    TYPES = ['tank', 'star', 'bomb', 'clock', 'shovel', 'helmet']

    def __init__(self, x, y, power_type):
        self.x = x
        self.y = y
        self.type = power_type
        self.size = TILE
        self.alive = True
        self.timer = 15.0
        self.blink = False

    def rect(self):
        return pygame.Rect(int(self.x - self.size // 2),
                           int(self.y - self.size // 2),
                           self.size, self.size)

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 3.0:
            self.blink = True
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface):
        if self.blink and int(self.timer * 6) % 2 == 0:
            return
        rect = self.rect()
        colors = {
            'tank': (220, 220, 50),
            'star': (255, 100, 100),
            'bomb': (255, 150, 50),
            'clock': (100, 200, 255),
            'shovel': (180, 140, 100),
            'helmet': (200, 200, 200),
        }
        color = colors.get(self.type, (255, 255, 255))
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (255, 255, 255), rect, 2)
        font_sym = get_font(TILE)
        symbols = {
            'tank': 'T', 'star': '*', 'bomb': 'B',
            'clock': 'C', 'shovel': 'S', 'helmet': 'H',
        }
        sym = symbols.get(self.type, '?')
        text = font_sym.render(sym, True, (0, 0, 0))
        text_rect = text.get_rect(center=rect.center)
        surface.blit(text, text_rect)
