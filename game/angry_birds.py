import pygame
import math
import random

pygame.init()

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
GROUND_HEIGHT = 100

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 50, 50)
GREEN = (50, 180, 50)
BLUE = (50, 100, 200)
YELLOW = (255, 220, 50)
BROWN = (139, 90, 43)
DARK_BROWN = (101, 67, 33)
LIGHT_BLUE = (135, 206, 235)
DARK_GREEN = (34, 139, 34)
ORANGE = (255, 165, 0)
PINK = (255, 182, 193)
GRAY = (128, 128, 128)

GRAVITY = 0.5
FRICTION = 0.99
BOUNCE = 0.6

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Angry Birds")
clock = pygame.time.Clock()
font_large = pygame.font.SysFont("arial", 36, bold=True)
font_medium = pygame.font.SysFont("arial", 24)
font_small = pygame.font.SysFont("arial", 18)


class Bird:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 15
        self.vx = 0
        self.vy = 0
        self.launched = False
        self.active = True
        self.color = RED
        self.trail = []

    def update(self):
        if self.launched and self.active:
            self.trail.append((int(self.x), int(self.y)))
            if len(self.trail) > 30:
                self.trail.pop(0)
            self.vy += GRAVITY
            self.vx *= FRICTION
            self.vy *= FRICTION
            self.x += self.vx
            self.y += self.vy
            if self.y >= SCREEN_HEIGHT - GROUND_HEIGHT - self.radius:
                self.y = SCREEN_HEIGHT - GROUND_HEIGHT - self.radius
                self.vy *= -BOUNCE
                self.vx *= 0.8
                if abs(self.vy) < 1 and abs(self.vx) < 0.5:
                    self.active = False
            if self.x < self.radius:
                self.x = self.radius
                self.vx *= -BOUNCE
            elif self.x > SCREEN_WIDTH - self.radius:
                self.x = SCREEN_WIDTH - self.radius
                self.vx *= -BOUNCE

    def draw(self, surface):
        for i, pos in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)) * 0.3) if self.trail else 0
            radius = max(2, int(self.radius * (i / len(self.trail)) * 0.5)) if self.trail else 2
            trail_color = (200, 100, 100)
            pygame.draw.circle(surface, trail_color, pos, radius)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, BLACK, (int(self.x), int(self.y)), self.radius, 2)
        pygame.draw.circle(surface, WHITE, (int(self.x) - 5, int(self.y) - 5), 4)
        pygame.draw.circle(surface, BLACK, (int(self.x) - 5, int(self.y) - 5), 2)
        pygame.draw.circle(surface, WHITE, (int(self.x) + 5, int(self.y) - 5), 4)
        pygame.draw.circle(surface, BLACK, (int(self.x) + 5, int(self.y) - 5), 2)
        pygame.draw.arc(surface, ORANGE, 
                       (int(self.x) - 8, int(self.y) + 2, 16, 10), 
                       3.14, 6.28, 2)

    def launch(self, vx, vy):
        self.vx = vx
        self.vy = vy
        self.launched = True
        self.fade_timer = 0

    def update_fade(self):
        if self.launched and not self.active:
            self.fade_timer += 1
            return self.fade_timer > 60
        return False


class Pig:
    def __init__(self, x, y, radius=20):
        self.x = x
        self.y = y
        self.radius = radius
        self.health = 100
        self.alive = True
        self.vx = 0
        self.vy = 0

    def update(self):
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        if self.y >= SCREEN_HEIGHT - GROUND_HEIGHT - self.radius:
            self.y = SCREEN_HEIGHT - GROUND_HEIGHT - self.radius
            self.vy = 0
            self.vx *= 0.8
        if self.x < self.radius:
            self.x = self.radius
        elif self.x > SCREEN_WIDTH - self.radius:
            self.x = SCREEN_WIDTH - self.radius

    def draw(self, surface):
        if not self.alive:
            return
        pygame.draw.circle(surface, GREEN, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x), int(self.y)), self.radius, 2)
        pygame.draw.circle(surface, WHITE, (int(self.x) - 6, int(self.y) - 5), 6)
        pygame.draw.circle(surface, WHITE, (int(self.x) + 6, int(self.y) - 5), 6)
        pygame.draw.circle(surface, BLACK, (int(self.x) - 6, int(self.y) - 5), 3)
        pygame.draw.circle(surface, BLACK, (int(self.x) + 6, int(self.y) - 5), 3)
        pygame.draw.ellipse(surface, DARK_GREEN, 
                           (int(self.x) - 5, int(self.y) + 3, 10, 6))
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x) - 12, int(self.y) - 3), 5)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x) + 12, int(self.y) - 3), 5)

    def hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.alive = False
            return True
        return False


class Block:
    def __init__(self, x, y, width, height, block_type="wood"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.block_type = block_type
        self.vx = 0
        self.vy = 0
        self.alive = True
        if block_type == "wood":
            self.health = 50
            self.color = BROWN
        elif block_type == "stone":
            self.health = 100
            self.color = GRAY
        elif block_type == "glass":
            self.health = 25
            self.color = (200, 230, 255)

    def update(self):
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        if self.y + self.height >= SCREEN_HEIGHT - GROUND_HEIGHT:
            self.y = SCREEN_HEIGHT - GROUND_HEIGHT - self.height
            self.vy = 0
            self.vx *= 0.8
        if self.x < 0:
            self.x = 0
        elif self.x + self.width > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.width

    def draw(self, surface):
        if not self.alive:
            return
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, self.color, rect)
        pygame.draw.rect(surface, BLACK, rect, 2)
        if self.block_type == "wood":
            for i in range(0, int(self.height), 8):
                pygame.draw.line(surface, DARK_BROWN, 
                               (self.x + 2, self.y + i), 
                               (self.x + self.width - 2, self.y + i), 1)
        elif self.block_type == "glass":
            pygame.draw.line(surface, WHITE, 
                           (self.x + 5, self.y + 5), 
                           (self.x + self.width - 5, self.y + self.height - 5), 2)

    def hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.alive = False
            return True
        return False

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)


class Slingshot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 20
        self.height = 80

    def draw(self, surface, bird=None, dragging=False, drag_pos=None):
        pygame.draw.rect(surface, DARK_BROWN, 
                        (self.x - 10, self.y - 60, 8, 70))
        pygame.draw.rect(surface, DARK_BROWN, 
                        (self.x + 2, self.y - 60, 8, 70))
        pygame.draw.rect(surface, BROWN, 
                        (self.x - 15, self.y - 10, 30, 15))
        back_x = self.x + 6
        front_x = self.x - 6
        anchor_y = self.y - 50
        rest_x = self.x
        rest_y = self.y - 50
        if bird and not bird.launched:
            bx, by = int(bird.x), int(bird.y)
            pygame.draw.line(surface, DARK_BROWN, 
                           (front_x, anchor_y), (bx, by), 4)
            pygame.draw.line(surface, DARK_BROWN, 
                           (back_x, anchor_y), (bx, by), 4)
        elif not bird or bird.launched:
            pygame.draw.line(surface, DARK_BROWN, 
                           (front_x, anchor_y), (rest_x, rest_y), 4)
            pygame.draw.line(surface, DARK_BROWN, 
                           (back_x, anchor_y), (rest_x, rest_y), 4)


class Game:
    def __init__(self):
        self.slingshot = Slingshot(150, SCREEN_HEIGHT - GROUND_HEIGHT)
        self.birds = []
        self.current_bird = None
        self.pigs = []
        self.blocks = []
        self.score = 0
        self.level = 1
        self.dragging = False
        self.drag_start = None
        self.game_over = False
        self.level_complete = False
        self.birds_remaining = 3
        self.max_drag = 120
        self.create_level()

    def create_level(self):
        self.pigs = []
        self.blocks = []
        self.birds = []
        self.birds_remaining = 2 + self.level
        self.spawn_bird()
        base_x = 700 + random.randint(-50, 50)
        base_y = SCREEN_HEIGHT - GROUND_HEIGHT
        if self.level == 1:
            self.blocks.append(Block(base_x, base_y - 40, 20, 80, "wood"))
            self.blocks.append(Block(base_x + 80, base_y - 40, 20, 80, "wood"))
            self.blocks.append(Block(base_x - 10, base_y - 60, 120, 20, "wood"))
            self.pigs.append(Pig(base_x + 50, base_y - 80, 20))
        elif self.level == 2:
            self.blocks.append(Block(base_x, base_y - 40, 20, 80, "wood"))
            self.blocks.append(Block(base_x + 80, base_y - 40, 20, 80, "wood"))
            self.blocks.append(Block(base_x - 10, base_y - 60, 120, 20, "wood"))
            self.blocks.append(Block(base_x + 30, base_y - 100, 20, 40, "wood"))
            self.blocks.append(Block(base_x + 50, base_y - 120, 60, 20, "wood"))
            self.pigs.append(Pig(base_x + 50, base_y - 80, 18))
            self.pigs.append(Pig(base_x + 60, base_y - 140, 15))
        else:
            self.blocks.append(Block(base_x, base_y - 30, 20, 60, "wood"))
            self.blocks.append(Block(base_x + 80, base_y - 30, 20, 60, "wood"))
            self.blocks.append(Block(base_x - 10, base_y - 50, 120, 20, "stone"))
            self.blocks.append(Block(base_x + 30, base_y - 90, 20, 40, "wood"))
            self.blocks.append(Block(base_x + 50, base_y - 110, 60, 20, "wood"))
            self.blocks.append(Block(base_x + 100, base_y - 150, 20, 80, "wood"))
            self.blocks.append(Block(base_x + 90, base_y - 170, 40, 20, "glass"))
            self.pigs.append(Pig(base_x + 50, base_y - 70, 18))
            self.pigs.append(Pig(base_x + 60, base_y - 130, 15))
            self.pigs.append(Pig(base_x + 100, base_y - 190, 15))

    def spawn_bird(self):
        if self.birds_remaining > 0:
            self.current_bird = Bird(self.slingshot.x, self.slingshot.y - 50)
            self.birds.append(self.current_bird)
            self.birds_remaining -= 1
        else:
            self.current_bird = None

    def handle_launch(self, drag_pos):
        if self.current_bird and not self.current_bird.launched:
            dx = self.slingshot.x - drag_pos[0]
            dy = (self.slingshot.y - 50) - drag_pos[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > self.max_drag:
                dx = dx / dist * self.max_drag
                dy = dy / dist * self.max_drag
                dist = self.max_drag
            power = 0.3 * (dist / self.max_drag) + 0.25
            self.current_bird.launch(dx * power, dy * power)

    def check_collisions(self):
        if not self.current_bird or not self.current_bird.launched:
            return
        bird = self.current_bird
        for pig in self.pigs:
            if not pig.alive:
                continue
            dist = math.sqrt((bird.x - pig.x) ** 2 + (bird.y - pig.y) ** 2)
            if dist < bird.radius + pig.radius:
                damage = math.sqrt(bird.vx ** 2 + bird.vy ** 2) * 10
                if pig.hit(damage):
                    self.score += 500
                bird.vx *= 0.5
                bird.vy *= 0.5
        for block in self.blocks:
            if not block.alive:
                continue
            block_rect = block.rect
            closest_x = max(block_rect.left, min(bird.x, block_rect.right))
            closest_y = max(block_rect.top, min(bird.y, block_rect.bottom))
            dist = math.sqrt((bird.x - closest_x) ** 2 + (bird.y - closest_y) ** 2)
            if dist < bird.radius:
                damage = math.sqrt(bird.vx ** 2 + bird.vy ** 2) * 8
                if block.hit(damage):
                    self.score += 100
                if abs(bird.x - closest_x) > abs(bird.y - closest_y):
                    bird.vx *= -BOUNCE
                else:
                    bird.vy *= -BOUNCE
                bird.vx *= 0.7
                bird.vy *= 0.7

    def check_level_status(self):
        pigs_alive = sum(1 for p in self.pigs if p.alive)
        if pigs_alive == 0:
            self.level_complete = True
            return
        if self.current_bird and not self.current_bird.active and self.birds_remaining == 0:
            self.game_over = True

    def next_bird(self):
        if self.birds_remaining > 0:
            self.spawn_bird()
        elif not any(p.alive for p in self.pigs):
            self.level_complete = True
        else:
            self.game_over = True

    def next_level(self):
        self.level += 1
        self.level_complete = False
        self.create_level()

    def restart(self):
        self.level = 1
        self.score = 0
        self.game_over = False
        self.level_complete = False
        self.create_level()

    def update(self):
        for block in self.blocks:
            if block.alive:
                block.update()
        for pig in self.pigs:
            if pig.alive:
                pig.update()
        for bird in self.birds[:]:
            if bird.launched and bird.update_fade():
                self.birds.remove(bird)
        if self.current_bird:
            self.current_bird.update()
            self.check_collisions()
            if self.current_bird.launched and not self.current_bird.active:
                self.check_level_status()
                if not self.level_complete and not self.game_over:
                    self.next_bird()

    def draw_background(self, surface):
        surface.fill(LIGHT_BLUE)
        pygame.draw.rect(surface, DARK_GREEN, 
                        (0, SCREEN_HEIGHT - GROUND_HEIGHT, SCREEN_WIDTH, GROUND_HEIGHT))
        pygame.draw.rect(surface, GREEN, 
                        (0, SCREEN_HEIGHT - GROUND_HEIGHT, SCREEN_WIDTH, 20))
        for i in range(0, SCREEN_WIDTH, 30):
            pygame.draw.line(surface, DARK_GREEN, 
                           (i, SCREEN_HEIGHT - GROUND_HEIGHT + 20), 
                           (i + 15, SCREEN_HEIGHT - GROUND_HEIGHT + 40), 2)

    def draw_ui(self, surface):
        title = font_large.render("ANGRY BIRDS", True, RED)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 10))
        score_text = font_medium.render(f"Score: {self.score}", True, BLACK)
        surface.blit(score_text, (20, 20))
        level_text = font_medium.render(f"Level: {self.level}", True, BLACK)
        surface.blit(level_text, (20, 50))
        birds_text = font_small.render(f"Birds: {self.birds_remaining + (1 if self.current_bird and not self.current_bird.launched else 0)}", True, BLACK)
        surface.blit(birds_text, (20, 80))
        controls = [
            "Controls:",
            "Mouse - Drag and release to launch",
            "R - Restart",
            "N - Next Level (after win)",
            "ESC - Quit"
        ]
        for i, text in enumerate(controls):
            color = BLACK if i == 0 else GRAY
            lbl = font_small.render(text, True, color)
            surface.blit(lbl, (SCREEN_WIDTH - 200, 20 + i * 22))
        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            surface.blit(overlay, (0, 0))
            go_text = font_large.render("GAME OVER", True, RED)
            surface.blit(go_text, (SCREEN_WIDTH // 2 - go_text.get_width() // 2, 
                                  SCREEN_HEIGHT // 2 - 40))
            score_text = font_medium.render(f"Final Score: {self.score}", True, WHITE)
            surface.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 
                                      SCREEN_HEIGHT // 2))
            restart_text = font_medium.render("Press R to restart", True, YELLOW)
            surface.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 
                                        SCREEN_HEIGHT // 2 + 40))
        if self.level_complete:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            surface.blit(overlay, (0, 0))
            win_text = font_large.render("LEVEL COMPLETE!", True, GREEN)
            surface.blit(win_text, (SCREEN_WIDTH // 2 - win_text.get_width() // 2, 
                                   SCREEN_HEIGHT // 2 - 40))
            score_text = font_medium.render(f"Score: {self.score}", True, WHITE)
            surface.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 
                                      SCREEN_HEIGHT // 2))
            next_text = font_medium.render("Press N for next level", True, YELLOW)
            surface.blit(next_text, (SCREEN_WIDTH // 2 - next_text.get_width() // 2, 
                                     SCREEN_HEIGHT // 2 + 40))

    def draw_trajectory(self, surface, drag_pos):
        if self.dragging and self.current_bird and not self.current_bird.launched:
            dx = self.slingshot.x - drag_pos[0]
            dy = (self.slingshot.y - 50) - drag_pos[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > self.max_drag:
                dx = dx / dist * self.max_drag
                dy = dy / dist * self.max_drag
            power = 0.3 * (dist / self.max_drag) + 0.25
            vx = dx * power
            vy = dy * power
            x = float(self.slingshot.x)
            y = float(self.slingshot.y - 50)
            for i in range(50):
                vy += GRAVITY
                x += vx
                y += vy
                if y > SCREEN_HEIGHT - GROUND_HEIGHT:
                    break
                if i % 3 == 0:
                    pygame.draw.circle(surface, (200, 200, 200), (int(x), int(y)), 3)

    def draw(self, surface, dragging=False, drag_pos=(0, 0)):
        self.draw_background(surface)
        self.slingshot.draw(surface, self.current_bird, dragging, drag_pos)
        for block in self.blocks:
            block.draw(surface)
        for pig in self.pigs:
            pig.draw(surface)
        for bird in self.birds:
            if bird.launched and not bird.active:
                continue
            bird.draw(surface)
        self.draw_ui(surface)


def main():
    game = Game()
    dragging = False
    drag_pos = (0, 0)

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
                    game.restart()
                if event.key == pygame.K_n and game.level_complete:
                    game.next_level()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if game.current_bird and not game.current_bird.launched:
                        mx, my = event.pos
                        dist = math.sqrt((mx - game.current_bird.x) ** 2 + 
                                        (my - game.current_bird.y) ** 2)
                        if dist < 50:
                            dragging = True
                            drag_pos = event.pos
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and dragging:
                    game.handle_launch(drag_pos)
                    dragging = False
            if event.type == pygame.MOUSEMOTION:
                if dragging:
                    drag_pos = event.pos

        if not game.game_over and not game.level_complete:
            game.update()
        
        game.draw(screen, dragging, drag_pos)
        if dragging and not game.game_over and not game.level_complete:
            game.draw_trajectory(screen, drag_pos)
            if game.current_bird and not game.current_bird.launched:
                game.current_bird.x = drag_pos[0]
                game.current_bird.y = drag_pos[1]
        
        pygame.display.flip()


if __name__ == "__main__":
    main()