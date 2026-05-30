import pygame
import random

pygame.init()

CELL_SIZE = 30
COLS = 10
ROWS = 20
SIDEBAR_WIDTH = 200
SCREEN_WIDTH = COLS * CELL_SIZE + SIDEBAR_WIDTH
SCREEN_HEIGHT = ROWS * CELL_SIZE

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (50, 50, 50)

COLORS = {
    'I': (0, 255, 255),
    'O': (255, 255, 0),
    'T': (128, 0, 128),
    'S': (0, 255, 0),
    'Z': (255, 0, 0),
    'J': (0, 0, 255),
    'L': (255, 165, 0),
}

SHAPES = {
    'I': [
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        [(0, 0), (0, 1), (0, 2), (0, 3)],
    ],
    'O': [
        [(0, 0), (1, 0), (0, 1), (1, 1)],
    ],
    'T': [
        [(0, 0), (1, 0), (2, 0), (1, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (0, 1)],
    ],
    'S': [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'Z': [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ],
    'J': [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(0, 0), (1, 0), (0, 1), (0, 2)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    'L': [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (0, 1)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}


class Piece:
    def __init__(self, shape_type):
        self.type = shape_type
        self.rotation = 0
        self.x = COLS // 2 - 2
        self.y = 0
        self.color = COLORS[shape_type]

    def cells(self):
        return SHAPES[self.type][self.rotation]

    def positions(self):
        return [(self.x + cx, self.y + cy) for cx, cy in self.cells()]

    def rotate(self):
        self.rotation = (self.rotation + 1) % len(SHAPES[self.type])


class Tetris:
    def __init__(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False
        self.paused = False
        self.current = None
        self.next = None
        self.fall_time = 0
        self.fall_speed = 500
        self.lock_delay = 500
        self.lock_time = 0
        self.locking = False
        self.soft_drop = False
        self.new_piece()

    def new_piece(self):
        if self.next is None:
            self.next = Piece(random.choice(list(SHAPES.keys())))
        self.current = self.next
        self.next = Piece(random.choice(list(SHAPES.keys())))
        self.locking = False
        self.lock_time = 0
        self.soft_drop = False
        if not self.valid_positions(self.current.positions()):
            self.game_over = True

    def valid_positions(self, positions):
        for x, y in positions:
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def move(self, dx, dy):
        old = self.current.positions()
        self.current.x += dx
        self.current.y += dy
        new = self.current.positions()
        if not self.valid_positions(new):
            self.current.x -= dx
            self.current.y -= dy
            if dy > 0:
                self.locking = True
            return False
        self.locking = False
        return True

    def rotate_piece(self):
        old_rot = self.current.rotation
        self.current.rotate()
        if not self.valid_positions(self.current.positions()):
            kicks = [(1, 0), (-1, 0), (0, -1), (2, 0), (-2, 0)]
            for kx, ky in kicks:
                self.current.x += kx
                self.current.y += ky
                if self.valid_positions(self.current.positions()):
                    return True
                self.current.x -= kx
                self.current.y -= ky
            self.current.rotation = old_rot
            return False
        return True

    def hard_drop(self):
        drop_distance = 0
        while self.move(0, 1):
            drop_distance += 1
        self.score += drop_distance * 2
        self.lock_piece()

    def lock_piece(self):
        for x, y in self.current.positions():
            if y >= 0:
                self.board[y][x] = self.current.color
        self.clear_lines()
        self.new_piece()

    def clear_lines(self):
        cleared = 0
        for y in range(ROWS):
            if all(self.board[y][x] is not None for x in range(COLS)):
                cleared += 1
                for row in range(y, 0, -1):
                    self.board[row] = self.board[row - 1][:]
                self.board[0] = [None] * COLS
        if cleared > 0:
            self.lines += cleared
            scores = {1: 100, 2: 300, 3: 500, 4: 800}
            self.score += scores.get(cleared, 0) * self.level
            self.level = self.lines // 10 + 1
            self.fall_speed = max(50, 500 - (self.level - 1) * 40)

    def ghost_positions(self):
        ghost = Piece(self.current.type)
        ghost.rotation = self.current.rotation
        ghost.x = self.current.x
        ghost.y = self.current.y
        while True:
            ghost.y += 1
            positions = ghost.positions()
            if not self.valid_positions(positions):
                ghost.y -= 1
                return ghost.positions()

    def update(self, dt):
        if self.game_over or self.paused:
            return
        self.fall_time += dt
        if self.locking:
            self.lock_time += dt
            if self.lock_time >= self.lock_delay:
                self.lock_piece()
                self.fall_time = 0
            return
        speed = 50 if self.soft_drop else self.fall_speed
        if self.fall_time >= speed:
            self.fall_time = 0
            if self.move(0, 1) and self.soft_drop:
                self.score += 1


screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Tetris")
clock = pygame.time.Clock()
font_large = pygame.font.SysFont("arial", 36, bold=True)
font_medium = pygame.font.SysFont("arial", 24)
font_small = pygame.font.SysFont("arial", 18)


def draw_cell(surface, x, y, color, size=CELL_SIZE):
    rect = pygame.Rect(x * size, y * size, size, size)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, WHITE, rect, 1)
    inner = pygame.Rect(x * size + 3, y * size + 3, size - 6, size - 6)
    lighter = tuple(min(255, c + 40) for c in color)
    pygame.draw.rect(surface, lighter, inner)


def draw_board(game):
    grid_left = 0
    pygame.draw.rect(screen, DARK_GRAY, (grid_left, 0, COLS * CELL_SIZE, ROWS * CELL_SIZE))
    for y in range(ROWS):
        for x in range(COLS):
            if game.board[y][x] is not None:
                draw_cell(screen, x, y, game.board[y][x])
            else:
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, DARK_GRAY, rect)
                pygame.draw.rect(screen, GRAY, rect, 1)

    if game.current and not game.game_over:
        ghost = game.ghost_positions()
        for gx, gy in ghost:
            if gy >= 0:
                rect = pygame.Rect(gx * CELL_SIZE, gy * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                ghost_color = tuple(c // 4 for c in game.current.color)
                pygame.draw.rect(screen, ghost_color, rect)
                pygame.draw.rect(screen, GRAY, rect, 1)
        for px, py in game.current.positions():
            if py >= 0:
                draw_cell(screen, px, py, game.current.color)


def draw_sidebar(game):
    sidebar_x = COLS * CELL_SIZE + 10
    pygame.draw.rect(screen, BLACK, (COLS * CELL_SIZE, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))

    title = font_large.render("TETRIS", True, WHITE)
    screen.blit(title, (sidebar_x + 20, 20))

    labels = [("SCORE", str(game.score), 80),
              ("LEVEL", str(game.level), 140),
              ("LINES", str(game.lines), 200)]
    for label, value, y in labels:
        lbl = font_medium.render(label, True, GRAY)
        screen.blit(lbl, (sidebar_x, y))
        val = font_medium.render(value, True, WHITE)
        screen.blit(val, (sidebar_x + 100, y))

    next_label = font_medium.render("NEXT", True, GRAY)
    screen.blit(next_label, (sidebar_x, 280))

    preview_size = 20
    preview_x_offset = sidebar_x + 20
    preview_y_offset = 310
    if game.next:
        cells = game.next.cells()
        min_cx = min(cx for cx, cy in cells)
        max_cx = max(cx for cx, cy in cells)
        min_cy = min(cy for cx, cy in cells)
        max_cy = max(cy for cx, cy in cells)
        pw = (max_cx - min_cx + 1) * preview_size
        ph = (max_cy - min_cy + 1) * preview_size
        offset_x = preview_x_offset + (100 - pw) // 2 - min_cx * preview_size
        offset_y = preview_y_offset
        for cx, cy in cells:
            rect = pygame.Rect(offset_x + cx * preview_size, offset_y + cy * preview_size, preview_size, preview_size)
            pygame.draw.rect(screen, game.next.color, rect)
            pygame.draw.rect(screen, WHITE, rect, 1)

    controls_y = 420
    controls = [
        "Controls:",
        "← →  Move",
        "↑    Rotate",
        "↓    Soft Drop",
        "Space Hard Drop",
        "P    Pause",
        "R    Restart",
        "ESC  Quit",
    ]
    for i, text in enumerate(controls):
        color = WHITE if i == 0 else GRAY
        lbl = font_small.render(text, True, color)
        screen.blit(lbl, (sidebar_x, controls_y + i * 22))

    if game.game_over:
        overlay = pygame.Surface((COLS * CELL_SIZE, ROWS * CELL_SIZE))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        go_text = font_large.render("GAME OVER", True, WHITE)
        rect = go_text.get_rect(center=(COLS * CELL_SIZE // 2, ROWS * CELL_SIZE // 2 - 20))
        screen.blit(go_text, rect)
        restart = font_medium.render("Press R to restart", True, GRAY)
        rect2 = restart.get_rect(center=(COLS * CELL_SIZE // 2, ROWS * CELL_SIZE // 2 + 20))
        screen.blit(restart, rect2)

    if game.paused and not game.game_over:
        overlay = pygame.Surface((COLS * CELL_SIZE, ROWS * CELL_SIZE))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        p_text = font_large.render("PAUSED", True, WHITE)
        rect = p_text.get_rect(center=(COLS * CELL_SIZE // 2, ROWS * CELL_SIZE // 2))
        screen.blit(p_text, rect)


def main():
    game = Tetris()

    while True:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_r:
                    game = Tetris()
                    continue
                if event.key == pygame.K_p:
                    game.paused = not game.paused
                    continue
                if game.game_over or game.paused:
                    continue
                if event.key == pygame.K_LEFT:
                    game.move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    game.move(1, 0)
                elif event.key == pygame.K_DOWN:
                    game.soft_drop = True
                elif event.key == pygame.K_UP:
                    game.rotate_piece()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()

        game.update(dt)
        screen.fill(BLACK)
        draw_board(game)
        draw_sidebar(game)
        pygame.display.flip()


if __name__ == "__main__":
    main()