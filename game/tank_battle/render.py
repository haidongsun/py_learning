"""Drawing functions for Tank Battle."""

import pygame

from .config import (
    TILE, MAP_W, MAP_H, PLAYFIELD_W, PLAYFIELD_H, SIDEBAR_W, SCREEN_W, SCREEN_H,
    EMPTY, BRICK, STEEL, BASE, WATER, TREE, ICE,
    COLOR_BG, COLOR_PLAYFIELD_BG, COLOR_BRICK, COLOR_BRICK_MORTAR,
    COLOR_STEEL, COLOR_STEEL_DARK, COLOR_BASE,
    COLOR_WATER, COLOR_WATER_LIGHT,
    COLOR_TREE, COLOR_TREE_DARK,
    COLOR_ICE, COLOR_ICE_LINE,
    COLOR_SIDEBAR, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_PLAYER, COLOR_PLAYER_DARK,
    COLOR_ENEMY_BASIC, COLOR_ENEMY_FAST, COLOR_ENEMY_POWER, COLOR_ENEMY_ARMOR,
    COLOR_ENEMY_SCOUT, COLOR_ENEMY_HEAVY, COLOR_ENEMY_SNIPER, COLOR_ENEMY_BOSS,
    COLOR_BULLET, COLOR_BULLET_POWER,
    get_font,
)


# ── Map base layer (ground, walls, water, ice, base) ─────
def draw_map_base(surface, game_map):
    for r in range(MAP_H):
        for c in range(MAP_W):
            tile = game_map[r][c]
            rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
            if tile == EMPTY:
                pygame.draw.rect(surface, COLOR_PLAYFIELD_BG, rect)
            elif tile == BRICK:
                pygame.draw.rect(surface, COLOR_BRICK, rect)
                pygame.draw.rect(surface, COLOR_BRICK_MORTAR, rect, 1)
                hw, hh = TILE // 2, TILE // 2
                for br in range(2):
                    for bc in range(2):
                        sr = pygame.Rect(
                            c * TILE + bc * hw + 1,
                            r * TILE + br * hh + 1,
                            hw - 2, hh - 2)
                        lighter = tuple(min(255, v + 30)
                                        for v in COLOR_BRICK[:3])
                        pygame.draw.rect(surface, lighter, sr)
            elif tile == STEEL:
                pygame.draw.rect(surface, COLOR_STEEL, rect)
                pygame.draw.rect(surface, COLOR_STEEL_DARK, rect, 1)
                shine = pygame.Surface((TILE - 4, TILE - 4))
                shine.fill(COLOR_STEEL_DARK)
                pygame.draw.rect(shine, COLOR_STEEL, (0, 0, TILE - 4, TILE // 2 - 2))
                surface.blit(shine, (c * TILE + 2, r * TILE + 2))
            elif tile == WATER:
                pygame.draw.rect(surface, COLOR_WATER, rect)
                # Wave lines
                for wave_y in range(2, TILE, 5):
                    offset = (c + r) % 3 * 2
                    for wx in range(offset, TILE, 6):
                        pygame.draw.line(surface, COLOR_WATER_LIGHT,
                                         (c * TILE + wx, r * TILE + wave_y),
                                         (c * TILE + wx + 3, r * TILE + wave_y), 1)
            elif tile == ICE:
                pygame.draw.rect(surface, COLOR_ICE, rect)
                # Grid pattern
                for lx in range(0, TILE, 5):
                    pygame.draw.line(surface, COLOR_ICE_LINE,
                                     (c * TILE + lx, r * TILE),
                                     (c * TILE + lx, r * TILE + TILE), 1)
                for ly in range(0, TILE, 5):
                    pygame.draw.line(surface, COLOR_ICE_LINE,
                                     (c * TILE, r * TILE + ly),
                                     (c * TILE + TILE, r * TILE + ly), 1)
            elif tile == BASE:
                pygame.draw.rect(surface, COLOR_PLAYFIELD_BG, rect)
                cx, cy = c * TILE + TILE // 2, r * TILE + TILE // 2
                pole_x = c * TILE + TILE // 2 - 1
                pygame.draw.rect(surface, (200, 180, 20),
                                 (pole_x, r * TILE + TILE // 4, 3, TILE // 2))
                flag_points = [
                    (cx + 2, r * TILE + TILE // 4),
                    (cx + TILE // 2 - 2, cy),
                    (cx + 2, r * TILE + TILE * 3 // 4),
                ]
                pygame.draw.polygon(surface, COLOR_BASE, flag_points)
                pygame.draw.polygon(surface, (150, 130, 10), flag_points, 1)


# ── Tree overlay (drawn AFTER tanks to hide them) ────────
def draw_trees(surface, game_map):
    for r in range(MAP_H):
        for c in range(MAP_W):
            if game_map[r][c] == TREE:
                rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                pygame.draw.rect(surface, COLOR_TREE, rect)
                # Leaf cluster shapes
                cx, cy = c * TILE + TILE // 2, r * TILE + TILE // 2
                r1, r2, r3 = TILE // 3, TILE // 4, TILE // 5
                pygame.draw.circle(surface, COLOR_TREE_DARK, (cx - 3, cy), r1)
                pygame.draw.circle(surface, COLOR_TREE_DARK, (cx + 3, cy - 2), r2)
                pygame.draw.circle(surface, COLOR_TREE, (cx, cy - 3), r2 + 1)
                pygame.draw.circle(surface, COLOR_TREE_DARK, (cx + 2, cy + 3), r3)
                pygame.draw.circle(surface, COLOR_TREE, (cx - 2, cy + 2), r3 + 1)


# ── Stage number ─────────────────────────────────────────
def draw_stage_number(surface, stage):
    font = get_font(22)
    text = font.render(f"STAGE  {stage + 1}", True, (180, 180, 180))
    tw = text.get_width()
    surface.blit(text, (PLAYFIELD_W - tw - 8, 4))


def draw_grid_overlay(surface):
    for r in range(MAP_H + 1):
        y = r * TILE
        pygame.draw.line(surface, (25, 25, 25), (0, y), (PLAYFIELD_W, y))
    for c in range(MAP_W + 1):
        x = c * TILE
        pygame.draw.line(surface, (25, 25, 25), (x, 0), (x, PLAYFIELD_H))


# ── Sidebar HUD (Chinese) ────────────────────────────────
def draw_sidebar(surface, game):
    sx = PLAYFIELD_W + 12
    ft = get_font(24)
    fm = get_font(18)
    fs = get_font(14)

    pygame.draw.rect(surface, COLOR_SIDEBAR,
                     (PLAYFIELD_W, 0, SIDEBAR_W, SCREEN_H))

    title = ft.render("坦克大战", True, (255, 220, 80))
    surface.blit(title, (sx, 12))

    stage_text = fm.render(f"第 {game.level + 1} 关", True, COLOR_TEXT)
    surface.blit(stage_text, (sx, 52))

    score_lbl = fs.render("得分", True, COLOR_TEXT_DIM)
    surface.blit(score_lbl, (sx, 82))
    score_val = fm.render(str(game.score), True, COLOR_TEXT)
    surface.blit(score_val, (sx, 100))

    lives_lbl = fs.render("生命", True, COLOR_TEXT_DIM)
    surface.blit(lives_lbl, (sx, 128))
    for i in range(game.player.lives):
        lx = sx + i * 24
        pygame.draw.rect(surface, COLOR_PLAYER, (lx, 148, 18, 18))
        pygame.draw.rect(surface, COLOR_PLAYER_DARK, (lx, 148, 18, 18), 2)

    y_off = 178
    if game.player.level > 0:
        star_lbl = fs.render("火力", True, COLOR_TEXT_DIM)
        surface.blit(star_lbl, (sx, y_off))
        stars = "*" * game.player.level
        star_text = fm.render(stars, True, (255, 200, 50))
        surface.blit(star_text, (sx + 50, y_off))
        y_off += 24

    enemy_lbl = fs.render("剩余敌人", True, COLOR_TEXT_DIM)
    surface.blit(enemy_lbl, (sx, y_off))
    y_off += 20
    remaining = game.enemies_total - game.enemies_spawned + len(game.enemies)
    for i in range(min(remaining, 10)):
        ex = sx + (i % 5) * 22
        ey = y_off + (i // 5) * 22
        pygame.draw.rect(surface, (180, 180, 190), (ex, ey, 16, 16))
        pygame.draw.rect(surface, (120, 120, 130), (ex, ey, 16, 16), 1)
    if remaining > 10:
        more = fs.render(f"+{remaining - 10}", True, COLOR_TEXT_DIM)
        surface.blit(more, (sx + 5 * 22, y_off + 22))

    y_off += 46

    eff_lbl = fs.render("道具效果", True, COLOR_TEXT_DIM)
    surface.blit(eff_lbl, (sx, y_off))
    y_off += 20
    if game.frozen:
        t = fs.render(f"冻结 {game.frozen_timer:.0f}s", True, (100, 200, 255))
        surface.blit(t, (sx, y_off)); y_off += 18
    if game.base_protected:
        t = fs.render(f"铁壁 {game.base_protect_timer:.0f}s", True, (180, 140, 100))
        surface.blit(t, (sx, y_off)); y_off += 18
    if game.helmet_active:
        t = fs.render(f"头盔 {game.helmet_timer:.0f}s", True, (200, 200, 200))
        surface.blit(t, (sx, y_off)); y_off += 18

    ctrl_y = SCREEN_H - 140
    ctrl = fs.render("操作", True, COLOR_TEXT_DIM)
    surface.blit(ctrl, (sx, ctrl_y))
    lines = ["方向键/WASD 移动",
             "空格 射击",
             "P 暂停  R 重来",
             "Esc 退出"]
    for i, line in enumerate(lines):
        t = fs.render(line, True, COLOR_TEXT_DIM)
        surface.blit(t, (sx, ctrl_y + 18 + i * 18))

    leg_y = ctrl_y + 18 + len(lines) * 18 + 6
    leg_lbl = fs.render("敌人类型", True, COLOR_TEXT_DIM)
    surface.blit(leg_lbl, (sx, leg_y))
    etypes = [
        ("普通   100", COLOR_ENEMY_BASIC),
        ("快速   200", COLOR_ENEMY_FAST),
        ("侦察   150", COLOR_ENEMY_SCOUT),
        ("火力   300", COLOR_ENEMY_POWER),
        ("狙击   250", COLOR_ENEMY_SNIPER),
        ("重装   350", COLOR_ENEMY_HEAVY),
        ("装甲   400", COLOR_ENEMY_ARMOR),
        ("首领   500", COLOR_ENEMY_BOSS),
    ]
    for i, (label, color) in enumerate(etypes):
        pygame.draw.rect(surface, color, (sx, leg_y + 20 + i * 16, 12, 12))
        t = fs.render(label, True, COLOR_TEXT_DIM)
        surface.blit(t, (sx + 18, leg_y + 18 + i * 16))


# ── Overlays (Chinese) ───────────────────────────────────
def draw_overlay(surface, game):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    f_big = get_font(42)
    f_med = get_font(24)

    if game.game_over:
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        if not game.base_alive:
            msg = f_big.render("基地被毁", True, (255, 80, 80))
        else:
            msg = f_big.render("游戏结束", True, (255, 200, 80))
        msg_rect = msg.get_rect(center=(PLAYFIELD_W // 2, PLAYFIELD_H // 2 - 25))
        surface.blit(msg, msg_rect)
        sub = f_med.render("按 R 重新开始", True, COLOR_TEXT_DIM)
        sub_rect = sub.get_rect(center=(PLAYFIELD_W // 2, PLAYFIELD_H // 2 + 22))
        surface.blit(sub, sub_rect)

    elif game.stage_clear:
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        msg = f_big.render("关卡通过!", True, (100, 255, 100))
        msg_rect = msg.get_rect(center=(PLAYFIELD_W // 2, PLAYFIELD_H // 2 - 20))
        surface.blit(msg, msg_rect)
        pts = f_med.render(f"+1000  总分: {game.score}", True, COLOR_TEXT)
        pts_rect = pts.get_rect(center=(PLAYFIELD_W // 2, PLAYFIELD_H // 2 + 25))
        surface.blit(pts, pts_rect)

    elif game.paused:
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        msg = f_big.render("暂停中", True, COLOR_TEXT)
        msg_rect = msg.get_rect(center=(PLAYFIELD_W // 2, PLAYFIELD_H // 2))
        surface.blit(msg, msg_rect)
