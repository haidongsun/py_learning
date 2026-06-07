"""Game state and logic for Tank Battle."""

import random
import pygame

from . import config as cfg
from .config import (
    TILE, MAP_W, MAP_H, PLAYFIELD_W, PLAYFIELD_H,
    DIR_VECTORS, DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT,
    BRICK, STEEL, BASE, EMPTY,
    MAX_ENEMIES_ON_FIELD, MAX_ENEMY_BULLETS,
    ENEMIES_PER_LEVEL, SPAWN_INTERVAL,
    BASE_PROTECT_TIME, FREEZE_TIME,
    COLOR_BRICK, COLOR_PLAYER, COLOR_BASE,
)
from .maps import LEVEL_MAPS, expand_map
from .entities import Bullet, PowerUp, Explosion, Particle
from .tanks import PlayerTank, EnemyTank


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.level = 0
        self.score = 0
        self.game_over = False
        self.paused = False
        self.stage_clear = False
        self.stage_clear_timer = 0
        self.load_level(self.level)

    def load_level(self, level_idx):
        map_idx = min(level_idx, len(LEVEL_MAPS) - 1)
        self.game_map = expand_map(LEVEL_MAPS[map_idx])
        self.bullets = []
        self.enemies = []
        self.enemies_spawned = 0
        self.enemies_total = ENEMIES_PER_LEVEL
        self.spawn_timer = 2.0
        self.spawn_index = 0
        self.power_ups = []
        self.explosions = []
        self.particles = []
        self._shovel_tiles = []
        self.base_alive = True
        self.player = PlayerTank(11 * TILE, 25 * TILE)
        self.frozen = False
        self.frozen_timer = 0
        self.base_protected = False
        self.base_protect_timer = 0
        self.helmet_active = False
        self.helmet_timer = 0
        self.stage_clear = False
        self.stage_clear_timer = 0
        self.enemy_icons = ENEMIES_PER_LEVEL
        self.spawn_points_13 = [0, 6, 12]
        cfg.snd_stage_start.play()

    def spawn_enemy(self):
        if len(self.enemies) >= MAX_ENEMIES_ON_FIELD:
            return
        if self.enemies_spawned >= self.enemies_total:
            return

        sp_13 = self.spawn_points_13[self.spawn_index % 3]
        self.spawn_index += 1
        sp_col_26 = sp_13 * 2
        spawn_x = sp_col_26 * TILE + TILE
        spawn_y = 0 * TILE + TILE

        tmp_rect = pygame.Rect(
            int(spawn_x - TILE), int(spawn_y - TILE), TILE * 2, TILE * 2)
        blocked = False
        for e in self.enemies:
            if e.alive and tmp_rect.colliderect(e.rect()):
                blocked = True
                break
        if self.player.alive and tmp_rect.colliderect(self.player.rect()):
            blocked = True
        if blocked:
            return

        r = random.random()
        # Progressive difficulty: later enemies are harder types
        progress = self.enemies_spawned / max(self.enemies_total, 1)
        if r < 0.30 - progress * 0.1:
            etype = 'basic'
        elif r < 0.48:
            etype = 'fast'
        elif r < 0.60:
            etype = 'scout'
        elif r < 0.72:
            etype = 'power'
        elif r < 0.82:
            etype = 'sniper'
        elif r < 0.90:
            etype = 'heavy'
        elif r < 0.96:
            etype = 'armor'
        else:
            etype = 'boss'

        enemy = EnemyTank(spawn_x, spawn_y, etype)
        self.enemies.append(enemy)
        self.enemies_spawned += 1
        self.enemy_icons = max(0, self.enemies_total - self.enemies_spawned)

    def update(self, dt):
        if self.game_over or self.paused:
            return

        if self.stage_clear:
            self.stage_clear_timer -= dt
            if self.stage_clear_timer <= 0:
                self.level += 1
                self.load_level(self.level)
            return

        if self.frozen:
            self.frozen_timer -= dt
            if self.frozen_timer <= 0:
                self.frozen = False
        if self.base_protected:
            self.base_protect_timer -= dt
            if self.base_protect_timer <= 0:
                self._remove_base_protection()
        if self.helmet_active:
            self.helmet_timer -= dt
            if self.helmet_timer <= 0:
                self.helmet_active = False

        self.player.update(dt)
        if self.player.alive and not self.player.spawning:
            keys = pygame.key.get_pressed()
            last_dir = self.player.direction
            moving = False
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.player.direction = DIR_UP
                moving = True
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.player.direction = DIR_DOWN
                moving = True
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.player.direction = DIR_LEFT
                moving = True
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.player.direction = DIR_RIGHT
                moving = True
            if self.player.direction != last_dir:
                self.player.snap_to_grid()
            if moving:
                self.player.move(dt, self.game_map, self._all_tanks())

        for enemy in self.enemies[:]:
            if not enemy.alive:
                continue
            if self.frozen and not enemy.spawning:
                continue
            want_shoot = enemy.update(dt, self.game_map, self._all_tanks(),
                                      self.player)
            if want_shoot and not enemy.spawning and not self.frozen:
                e_bullets = [b for b in self.bullets
                             if b.owner == 'enemy' and b.alive]
                if len(e_bullets) < MAX_ENEMY_BULLETS:
                    bullet = enemy.shoot()
                    bullet.owner = 'enemy'
                    self.bullets.append(bullet)
                    cfg.snd_shoot.play()

        if (self.enemies_spawned < self.enemies_total and
                len(self.enemies) < MAX_ENEMIES_ON_FIELD):
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_enemy()
                self.spawn_timer = SPAWN_INTERVAL

        for bullet in self.bullets[:]:
            if not bullet.alive:
                continue
            result = bullet.update(dt, self.game_map)
            if not bullet.alive:
                if result == 'base':
                    self._on_base_hit()
                    continue
                if result == 'brick':
                    cfg.snd_brick.play()
                    self._spawn_particles(bullet.x, bullet.y, COLOR_BRICK, 5)
                elif result == 'steel':
                    cfg.snd_steel.play()
                continue

            if bullet.owner == 'player':
                target_tanks = self.enemies
            else:
                target_tanks = [self.player]

            for tank in target_tanks:
                if not tank.alive or tank.spawning:
                    continue
                if bullet.rect().colliderect(tank.rect()):
                    if isinstance(tank, PlayerTank):
                        if self.helmet_active or tank.invincible:
                            bullet.alive = False
                            continue
                        self._on_player_hit()
                    else:
                        tank.hp -= 1
                        if tank.hp <= 0:
                            tank.alive = False
                            self.score += tank.score
                            self.explosions.append(
                                Explosion(tank.x, tank.y, True))
                            cfg.snd_explosion.play()
                            self._spawn_particles(tank.x, tank.y,
                                                  tank.color, 15)
                            if random.random() < 0.4:
                                self._spawn_powerup(tank.x, tank.y)
                        else:
                            self.explosions.append(
                                Explosion(bullet.x, bullet.y))
                            cfg.snd_steel.play()
                    bullet.alive = False
                    break

            if bullet.alive and bullet.owner == 'player':
                for other in self.bullets:
                    if other is bullet or other.owner == 'player':
                        continue
                    if not other.alive:
                        continue
                    if bullet.rect().colliderect(other.rect()):
                        bullet.alive = False
                        other.alive = False
                        break

        self.bullets = [b for b in self.bullets if b.alive]
        for enemy in self.enemies[:]:
            if not enemy.alive:
                self.enemies.remove(enemy)

        for pu in self.power_ups[:]:
            pu.update(dt)
            if not pu.alive:
                self.power_ups.remove(pu)
                continue
            if self.player.alive and pu.rect().colliderect(self.player.rect()):
                self._apply_powerup(pu)
                self.power_ups.remove(pu)

        for exp in self.explosions[:]:
            exp.update(dt)
            if not exp.alive:
                self.explosions.remove(exp)

        for p in self.particles[:]:
            p.update(dt)
            if not p.alive:
                self.particles.remove(p)

        if (self.enemies_spawned >= self.enemies_total and
                len(self.enemies) == 0):
            self.stage_clear = True
            self.stage_clear_timer = 3.0
            self.score += 1000

    def _all_tanks(self):
        tanks = [self.player]
        tanks.extend(self.enemies)
        return tanks

    def _on_player_hit(self):
        self.player.alive = False
        self.explosions.append(Explosion(self.player.x, self.player.y, True))
        cfg.snd_explosion.play()
        self._spawn_particles(self.player.x, self.player.y, COLOR_PLAYER, 20)
        self.player.lives -= 1
        if self.player.lives <= 0:
            self.game_over = True
            cfg.snd_gameover.play()
        else:
            self.player.reset_position(11 * TILE, 25 * TILE)

    def _on_base_hit(self):
        self.base_alive = False
        self.game_over = True
        bx, by = int(12.5 * TILE), 25 * TILE
        self.explosions.append(Explosion(bx, by, True))
        self.explosions.append(Explosion(bx - TILE, by - TILE, True))
        self.explosions.append(Explosion(bx + TILE, by - TILE, True))
        cfg.snd_gameover.play()
        cfg.snd_base_hit.play()
        self._spawn_particles(bx, by, COLOR_BASE, 30)

    def _spawn_powerup(self, x, y):
        for pu in self.power_ups:
            if pu.alive and abs(pu.x - x) < TILE and abs(pu.y - y) < TILE:
                return
        types = PowerUp.TYPES
        weights = [0.15, 0.25, 0.15, 0.15, 0.15, 0.15]
        pu_type = random.choices(types, weights=weights, k=1)[0]
        self.power_ups.append(PowerUp(x, y, pu_type))

    def _apply_powerup(self, pu):
        cfg.snd_powerup.play()
        if pu.type == 'tank':
            self.player.lives = min(self.player.lives + 1, 5)
        elif pu.type == 'star':
            self.player.upgrade()
        elif pu.type == 'bomb':
            for enemy in self.enemies[:]:
                if enemy.alive:
                    enemy.alive = False
                    self.score += enemy.score
                    self.explosions.append(Explosion(enemy.x, enemy.y, True))
                    self._spawn_particles(enemy.x, enemy.y, enemy.color, 10)
            self.enemies.clear()
            cfg.snd_explosion.play()
        elif pu.type == 'clock':
            self.frozen = True
            self.frozen_timer = FREEZE_TIME
        elif pu.type == 'shovel':
            self._add_base_protection()
        elif pu.type == 'helmet':
            self.helmet_active = True
            self.helmet_timer = 10.0

    def _add_base_protection(self):
        self.base_protected = True
        self.base_protect_timer = BASE_PROTECT_TIME
        self._shovel_tiles = []
        for r in range(MAP_H - 3, MAP_H):
            for c in range(10, 16):
                if self.game_map[r][c] in (EMPTY, BRICK):
                    self._shovel_tiles.append((r, c, self.game_map[r][c]))
                    self.game_map[r][c] = STEEL
        self.game_map[MAP_H - 1][12] = BASE
        self.game_map[MAP_H - 1][13] = BASE
        self.game_map[MAP_H - 2][12] = BASE
        self.game_map[MAP_H - 2][13] = BASE

    def _remove_base_protection(self):
        self.base_protected = False
        for r, c, old_tile in self._shovel_tiles:
            if self.game_map[r][c] == STEEL:
                self.game_map[r][c] = old_tile
        self._shovel_tiles = []
        self.game_map[MAP_H - 1][12] = BASE
        self.game_map[MAP_H - 1][13] = BASE
        self.game_map[MAP_H - 2][12] = BASE
        self.game_map[MAP_H - 2][13] = BASE

    def _spawn_particles(self, x, y, color, count):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))
