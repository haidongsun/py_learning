"""Entry point and main loop for Tank Battle."""

import pygame

from . import config as cfg
from .config import (
    SCREEN_W, SCREEN_H, PLAYFIELD_W, PLAYFIELD_H, FPS,
    COLOR_BG, COLOR_PLAYFIELD_BG,
    COLOR_BULLET, COLOR_BULLET_POWER,
    init_sounds,
)
from .render import (
    draw_map_base, draw_trees, draw_stage_number,
    draw_grid_overlay, draw_sidebar, draw_overlay,
)
from .game import Game


def main():
    pygame.init()
    pygame.mixer.init(frequency=22050, size=-16, channels=8, buffer=512)
    init_sounds()

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Battle City — Tank Battle")
    clock = pygame.time.Clock()

    game = Game()

    while True:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_r:
                    game.reset()
                    continue
                if event.key == pygame.K_p and not game.game_over:
                    game.paused = not game.paused
                    continue
                if event.key == pygame.K_SPACE:
                    if (game.player.alive and not game.player.spawning and
                            game.player.can_shoot()):
                        p_bullets = [b for b in game.bullets
                                     if b.owner == 'player' and b.alive]
                        if len(p_bullets) < game.player.max_bullets():
                            bullet = game.player.shoot()
                            bullet.owner = 'player'
                            game.bullets.append(bullet)
                            cfg.snd_shoot_player.play()

        game.update(dt)

        screen.fill(COLOR_BG)
        playfield_surface = pygame.Surface((PLAYFIELD_W, PLAYFIELD_H))
        playfield_surface.fill(COLOR_PLAYFIELD_BG)
        draw_map_base(playfield_surface, game.game_map)

        for pu in game.power_ups:
            pu.draw(playfield_surface)

        for bullet in game.bullets:
            if bullet.alive:
                color = COLOR_BULLET_POWER if bullet.power else COLOR_BULLET
                pygame.draw.circle(playfield_surface, color,
                                   (int(bullet.x), int(bullet.y)), 3)
                pygame.draw.circle(playfield_surface, (255, 255, 255),
                                   (int(bullet.x), int(bullet.y)), 1)

        for exp in game.explosions:
            exp.draw(playfield_surface)

        for p in game.particles:
            if p.alive:
                s = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*p.color, p.alpha),
                                   (p.size, p.size), p.size)
                playfield_surface.blit(
                    s, (int(p.x - p.size), int(p.y - p.size)))

        for enemy in game.enemies:
            if enemy.alive:
                enemy.draw(playfield_surface)

        if game.player.alive:
            game.player.draw(playfield_surface)

        # Trees drawn AFTER tanks to hide units underneath
        draw_trees(playfield_surface, game.game_map)

        draw_stage_number(playfield_surface, game.level)
        draw_grid_overlay(playfield_surface)
        screen.blit(playfield_surface, (0, 0))
        draw_sidebar(screen, game)
        draw_overlay(screen, game)

        pygame.display.flip()
