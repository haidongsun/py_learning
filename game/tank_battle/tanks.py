"""Tank, PlayerTank, and EnemyTank classes for Tank Battle."""

import random
import pygame

from .config import (
    TILE, PLAYFIELD_W, PLAYFIELD_H, MAP_W, MAP_H,
    DIR_VECTORS, DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT,
    BRICK, STEEL, BASE, EMPTY, WATER, TREE, ICE,
    PLAYER_SPEED, PLAYER_LIVES, PLAYER_SHOOT_COOLDOWN,
    INVINCIBLE_TIME, ENEMY_BASE_SPEED, ENEMY_FAST_SPEED,
    ENEMY_SHOOT_COOLDOWN, MAX_PLAYER_BULLETS,
    COLOR_PLAYER, COLOR_PLAYER_DARK,
    COLOR_PLAYER_STAR1, COLOR_PLAYER_STAR2, COLOR_PLAYER_STAR3,
    COLOR_ENEMY_BASIC, COLOR_ENEMY_FAST,
    COLOR_ENEMY_POWER, COLOR_ENEMY_ARMOR,
    COLOR_ENEMY_SCOUT, COLOR_ENEMY_HEAVY,
    COLOR_ENEMY_SNIPER, COLOR_ENEMY_BOSS,
)
from .entities import Bullet


# ── Tank base class ──────────────────────────────────────
class Tank:
    def __init__(self, x, y, direction, color, color_dark):
        self.x = x
        self.y = y
        self.direction = direction
        self.size = TILE * 2
        self.half = self.size // 2
        self.color = color
        self.color_dark = color_dark
        self.speed = PLAYER_SPEED
        self.alive = True
        self.spawning = False
        self.spawn_timer = 0

    def rect(self):
        return pygame.Rect(int(self.x - self.half), int(self.y - self.half),
                           self.size, self.size)

    def collides_with(self, other):
        return self.rect().colliderect(other.rect())

    def can_move_to(self, new_x, new_y, game_map, tanks):
        """Check if tank can be at (new_x, new_y)."""
        half = self.half
        cx, cy = round(new_x), round(new_y)
        left = cx - half
        top = cy - half
        right = cx + half - 1
        bottom = cy + half - 1

        if left < 0 or right >= PLAYFIELD_W or top < 0 or bottom >= PLAYFIELD_H:
            return False

        tl_col = max(0, left // TILE)
        tl_row = max(0, top // TILE)
        br_col = min(MAP_W - 1, right // TILE)
        br_row = min(MAP_H - 1, bottom // TILE)

        for r in range(tl_row, br_row + 1):
            for c in range(tl_col, br_col + 1):
                if game_map[r][c] in (BRICK, STEEL, BASE, WATER):
                    return False

        tmp_rect = pygame.Rect(left, top, self.size, self.size)
        for t in tanks:
            if t is not self and t.alive and tmp_rect.colliderect(t.rect()):
                return False

        return True

    def snap_to_grid(self):
        """Align tank to tile grid on axis perpendicular to movement."""
        if self.direction in (DIR_UP, DIR_DOWN):
            self.x = round(self.x / TILE) * TILE
        else:
            self.y = round(self.y / TILE) * TILE

    def move(self, dt, game_map, tanks):
        dx, dy = DIR_VECTORS[self.direction]
        new_x = self.x + dx * self.speed * dt
        new_y = self.y + dy * self.speed * dt

        if self.can_move_to(new_x, new_y, game_map, tanks):
            self.x = new_x
            self.y = new_y
        if dx != 0:
            self.y = round(self.y / TILE) * TILE
        else:
            self.x = round(self.x / TILE) * TILE

    def draw(self, surface, offset_x=0, offset_y=0):
        rect = self.rect()
        rect.x += offset_x
        rect.y += offset_y
        # Tracks
        pygame.draw.rect(surface, self.color_dark,
                         rect.inflate(-self.size * 0.7, -4))
        pygame.draw.rect(surface, self.color_dark,
                         rect.inflate(-self.size * 0.7, -4).move(0, 0))
        # Body
        body_rect = rect.inflate(-8, -8)
        pygame.draw.rect(surface, self.color, body_rect)
        pygame.draw.rect(surface, self.color_dark, body_rect, 2)
        # Turret
        cx, cy = rect.centerx, rect.centery
        turret_r = self.size // 6
        pygame.draw.circle(surface, self.color_dark, (cx, cy), turret_r)
        pygame.draw.circle(surface, self.color, (cx, cy), turret_r - 2)
        # Barrel
        barrel_len = self.size // 2
        barrel_w = 5
        dx, dy = DIR_VECTORS[self.direction]
        end_x = cx + dx * barrel_len
        end_y = cy + dy * barrel_len
        perp = (-dy, dx)
        pts = [
            (cx + perp[0] * barrel_w, cy + perp[1] * barrel_w),
            (cx - perp[0] * barrel_w, cy - perp[1] * barrel_w),
            (end_x - perp[0] * barrel_w, end_y - perp[1] * barrel_w),
            (end_x + perp[0] * barrel_w, end_y + perp[1] * barrel_w),
        ]
        pygame.draw.polygon(surface, self.color_dark, pts)
        inner_pts = [
            (cx + perp[0] * (barrel_w - 1), cy + perp[1] * (barrel_w - 1)),
            (cx - perp[0] * (barrel_w - 1), cy - perp[1] * (barrel_w - 1)),
            (end_x - perp[0] * (barrel_w - 1), end_y - perp[1] * (barrel_w - 1)),
            (end_x + perp[0] * (barrel_w - 1), end_y + perp[1] * (barrel_w - 1)),
        ]
        pygame.draw.polygon(surface, self.color, inner_pts)

    def shoot(self):
        dx, dy = DIR_VECTORS[self.direction]
        bx = self.x + dx * (self.half + 6)
        by = self.y + dy * (self.half + 6)
        return Bullet(bx, by, self.direction, self)


# ── Player Tank ──────────────────────────────────────────
class PlayerTank(Tank):
    def __init__(self, x, y):
        super().__init__(x, y, DIR_UP, COLOR_PLAYER, COLOR_PLAYER_DARK)
        self.lives = PLAYER_LIVES
        self.level = 0
        self.invincible = False
        self.invincible_timer = 0
        self.shoot_cooldown = 0
        self.speed = PLAYER_SPEED
        self.spawning = True
        self.spawn_timer = 1.5

    def upgrade(self):
        if self.level < 2:
            self.level += 1
            if self.level == 1:
                self.color = COLOR_PLAYER_STAR1
                self.color_dark = COLOR_PLAYER_STAR2
            elif self.level == 2:
                self.color = COLOR_PLAYER_STAR3
                self.color_dark = (40, 160, 40)

    def reset_position(self, x, y):
        self.x = x
        self.y = y
        self.direction = DIR_UP
        self.alive = True
        self.spawning = True
        self.spawn_timer = 1.5
        self.invincible = True
        self.invincible_timer = INVINCIBLE_TIME
        self.level = 0
        self.color = COLOR_PLAYER
        self.color_dark = COLOR_PLAYER_DARK

    def update(self, dt):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt
        if self.spawn_timer > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawning = False
        if self.invincible:
            self.invincible_timer -= dt
            if self.invincible_timer <= 0:
                self.invincible = False

    def draw(self, surface, offset_x=0, offset_y=0):
        if self.spawning:
            if int(self.spawn_timer * 10) % 2 == 0:
                super().draw(surface, offset_x, offset_y)
        elif self.invincible:
            if int(self.invincible_timer * 10) % 2 == 0:
                super().draw(surface, offset_x, offset_y)
        else:
            super().draw(surface, offset_x, offset_y)

    def max_bullets(self):
        if self.level >= 2:
            return 2
        return MAX_PLAYER_BULLETS

    def can_shoot(self):
        return self.shoot_cooldown <= 0 and not self.spawning

    def shoot(self):
        self.shoot_cooldown = PLAYER_SHOOT_COOLDOWN
        dx, dy = DIR_VECTORS[self.direction]
        bx = self.x + dx * (self.half + 6)
        by = self.y + dy * (self.half + 6)
        return Bullet(bx, by, self.direction, self, power=(self.level >= 1))


# ── Enemy Tank ───────────────────────────────────────────
ENEMY_DEFS = {
    'basic': {
        'speed': 60, 'hp': 1, 'power': False, 'score': 100,
        'color': COLOR_ENEMY_BASIC, 'dark': (140, 140, 150),
        'shoot_cooldown': (0.8, 1.5), 'dir_change': (1.0, 3.5),
        'prefer_base': True, 'prefer_player': False, 'erratic': False,
    },
    'fast': {
        'speed': 100, 'hp': 1, 'power': False, 'score': 200,
        'color': COLOR_ENEMY_FAST, 'dark': (60, 120, 200),
        'shoot_cooldown': (0.6, 1.2), 'dir_change': (0.5, 1.5),
        'prefer_base': True, 'prefer_player': False, 'erratic': True,
    },
    'power': {
        'speed': 60, 'hp': 1, 'power': True, 'score': 300,
        'color': COLOR_ENEMY_POWER, 'dark': (60, 200, 60),
        'shoot_cooldown': (0.7, 1.4), 'dir_change': (1.0, 3.0),
        'prefer_base': True, 'prefer_player': False, 'erratic': False,
    },
    'armor': {
        'speed': 55, 'hp': 4, 'power': False, 'score': 400,
        'color': COLOR_ENEMY_ARMOR, 'dark': (180, 180, 50),
        'shoot_cooldown': (1.0, 2.0), 'dir_change': (1.5, 4.0),
        'prefer_base': True, 'prefer_player': False, 'erratic': False,
    },
    'scout': {
        'speed': 130, 'hp': 1, 'power': False, 'score': 150,
        'color': COLOR_ENEMY_SCOUT, 'dark': (50, 160, 160),
        'shoot_cooldown': (0.4, 0.8), 'dir_change': (0.3, 0.8),
        'prefer_base': False, 'prefer_player': True, 'erratic': True,
    },
    'heavy': {
        'speed': 45, 'hp': 3, 'power': True, 'score': 350,
        'color': COLOR_ENEMY_HEAVY, 'dark': (140, 40, 40),
        'shoot_cooldown': (1.2, 2.2), 'dir_change': (2.0, 5.0),
        'prefer_base': True, 'prefer_player': False, 'erratic': False,
    },
    'sniper': {
        'speed': 55, 'hp': 1, 'power': False, 'score': 250,
        'color': COLOR_ENEMY_SNIPER, 'dark': (120, 80, 160),
        'shoot_cooldown': (0.5, 1.0), 'dir_change': (1.5, 4.0),
        'prefer_base': False, 'prefer_player': True, 'erratic': False,
    },
    'boss': {
        'speed': 70, 'hp': 6, 'power': True, 'score': 500,
        'color': COLOR_ENEMY_BOSS, 'dark': (170, 130, 20),
        'shoot_cooldown': (0.3, 0.6), 'dir_change': (0.8, 2.0),
        'prefer_base': True, 'prefer_player': True, 'erratic': False,
    },
}
TYPES = list(ENEMY_DEFS.keys())


class EnemyTank(Tank):
    def __init__(self, x, y, enemy_type='basic'):
        self.enemy_type = enemy_type
        d = ENEMY_DEFS[enemy_type]
        self.speed = d['speed']
        self.hp = d['hp']
        self.max_hp = d['hp']
        self.power_bullet = d['power']
        self.score = d['score']
        self._shoot_range = d['shoot_cooldown']
        self._dir_range = d['dir_change']
        self._prefer_base = d['prefer_base']
        self._prefer_player = d['prefer_player']
        self._erratic = d['erratic']

        super().__init__(x, y, DIR_DOWN, d['color'], d['dark'])
        self.spawning = True
        self.spawn_timer = 1.5
        self.shoot_timer = random.uniform(*self._shoot_range)
        self.direction_change_timer = random.uniform(*self._dir_range)

    def update(self, dt, game_map, tanks, player):
        if self.spawn_timer > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawning = False
            return False

        self.shoot_timer -= dt
        self.direction_change_timer -= dt

        # Smarter direction change
        if self.direction_change_timer <= 0:
            self._smart_dir_change(game_map, tanks, player)
            self.direction_change_timer = random.uniform(*self._dir_range)

        # Shooting logic
        want_shoot = False
        if self.shoot_timer <= 0:
            self.shoot_timer = random.uniform(*self._shoot_range)
            # Sniper: high chance when aligned with player
            if self.enemy_type == 'sniper' and self._aligned_with(player):
                want_shoot = random.random() < 0.9
            elif self.enemy_type == 'boss':
                want_shoot = random.random() < 0.8
            elif self._is_facing(player) and random.random() < 0.7:
                want_shoot = True
            elif random.random() < 0.25:
                want_shoot = True

        # Movement
        old_x, old_y = self.x, self.y
        self.move(dt, game_map, tanks)
        if abs(self.x - old_x) < 0.5 and abs(self.y - old_y) < 0.5:
            # Blocked — force faster direction change
            self.direction_change_timer -= dt * 4
            if self.direction_change_timer <= 0:
                self._smart_dir_change(game_map, tanks, player)
                self.direction_change_timer = random.uniform(*self._dir_range)

        return want_shoot

    def _smart_dir_change(self, game_map, tanks, player):
        """Pick best available direction using actual collision check."""
        available = []
        for d in (DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT):
            dx, dy = DIR_VECTORS[d]
            test_x = self.x + dx * TILE
            test_y = self.y + dy * TILE
            if self.can_move_to(test_x, test_y, game_map, tanks):
                available.append(d)

        if not available:
            return  # stuck, try next frame

        # Determine target coordinates
        if self._prefer_player:
            tx, ty = player.x, player.y
        else:
            # Target the base (bottom center of map)
            tx = (MAP_W // 2) * TILE
            ty = (MAP_H - 2) * TILE

        ideal_dir = self._direction_toward(tx, ty)
        opposite = {DIR_UP: DIR_DOWN, DIR_DOWN: DIR_UP,
                    DIR_LEFT: DIR_RIGHT, DIR_RIGHT: DIR_LEFT}

        # Prefer ideal direction, then perpendicular, then opposite
        if self._erratic:
            # Erratic types prefer random valid directions
            self.direction = random.choice(available)
        else:
            if ideal_dir in available and random.random() < 0.6:
                self.direction = ideal_dir
            else:
                # Try perpendicular directions to ideal
                side_dirs = [d for d in available
                             if d not in (ideal_dir, opposite.get(ideal_dir))]
                if side_dirs and random.random() < 0.7:
                    self.direction = random.choice(side_dirs)
                elif available:
                    self.direction = random.choice(available)
        self.snap_to_grid()

    def _direction_toward(self, tx, ty):
        dx = tx - self.x
        dy = ty - self.y
        if abs(dx) > abs(dy):
            return DIR_RIGHT if dx > 0 else DIR_LEFT
        return DIR_DOWN if dy > 0 else DIR_UP

    def _is_facing(self, other):
        return self.direction == self._direction_toward(other.x, other.y)

    def _aligned_with(self, other):
        """Check if tank is on same row or column as other."""
        return (abs(self.x - other.x) < TILE * 1.5 or
                abs(self.y - other.y) < TILE * 1.5)

    def shoot(self):
        dx, dy = DIR_VECTORS[self.direction]
        bx = self.x + dx * (self.half + 6)
        by = self.y + dy * (self.half + 6)
        return Bullet(bx, by, self.direction, self, power=self.power_bullet)

    def draw(self, surface, offset_x=0, offset_y=0):
        if self.spawning:
            if int(self.spawn_timer * 10) % 2 == 0:
                super().draw(surface, offset_x, offset_y)
        else:
            super().draw(surface, offset_x, offset_y)
            if self.max_hp > 1:
                rect = self.rect()
                rect.x += offset_x
                rect.y += offset_y
                hp_bar_w = self.size
                hp_bar_h = 3
                hp_x = rect.x
                hp_y = rect.y - 8
                pygame.draw.rect(surface, (50, 50, 50),
                                 (hp_x, hp_y, hp_bar_w, hp_bar_h))
                fill_w = int(hp_bar_w * (self.hp / self.max_hp))
                pygame.draw.rect(surface, (200, 50, 50),
                                 (hp_x, hp_y, fill_w, hp_bar_h))
