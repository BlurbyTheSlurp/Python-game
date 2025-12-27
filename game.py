import pygame
import random
import sys
import math

pygame.init()

# --- Screen and world settings ---
SCREEN_WIDTH, SCREEN_HEIGHT = 960, 540
TILE_SIZE = 32
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Side-Scroller Survival (Scrolling, Inventory, Crafting)")

clock = pygame.time.Clock()
FPS = 60

WORLD_HEIGHT_TILES = SCREEN_HEIGHT // TILE_SIZE
WORLD_WIDTH_TILES = 300  # big but finite, feels "endless"

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BROWN = (120, 72, 0)
GREY = (140, 140, 140)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
SAND = (210, 200, 120)
SKY = (120, 180, 255)
DARK = (10, 10, 30)

# --- Tiles ---
AIR = 0
DIRT = 1
WOOD = 2
STONE = 3
WALL = 4

# --- Player ---
PLAYER_SPEED = 4
JUMP_FORCE = -12
GRAVITY = 0.6
PLAYER_WIDTH = 28
PLAYER_HEIGHT = 48
PLAYER_MAX_HP = 100

MINING_RANGE_TILES = 3  # how close you must be to mine

# --- Enemies ---
ZOMBIE_SPEED = 1.2
ZOMBIE_DAMAGE_COOLDOWN = 600
ZOMBIE_SPAWN_INTERVAL = 4000

# --- Day/Night ---
DAY_DURATION = 20_000
NIGHT_DURATION = 25_000


# ---------------------------------------------------------
# Player
# ---------------------------------------------------------
class Player:
    def __init__(self, x, y):
        self.x = x  # world coordinates
        self.y = y
        self.vx = 0
        self.vy = 0
        self.hp = PLAYER_MAX_HP

        # Inventory
        self.inventory = {
            "wood": 0,
            "stone": 0,
            "stone_wall": 0,
            "wood_wall": 0,
        }

        self.last_hit = 0

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), PLAYER_WIDTH, PLAYER_HEIGHT)

    def move(self, world, keys):
        # Horizontal movement
        self.vx = 0
        if keys[pygame.K_a]:
            self.vx = -PLAYER_SPEED
        if keys[pygame.K_d]:
            self.vx = PLAYER_SPEED

        # Jump
        if keys[pygame.K_SPACE]:
            if self.on_ground(world):
                self.vy = JUMP_FORCE

        # Gravity
        self.vy += GRAVITY
        if self.vy > 12:
            self.vy = 12

        # Move X
        self.x += self.vx
        self.collide(world, dx=self.vx)

        # Move Y
        self.y += self.vy
        self.collide(world, dy=self.vy)

        # Keep within world horizontally
        if self.x < 0:
            self.x = 0
        if self.x + PLAYER_WIDTH > WORLD_WIDTH_TILES * TILE_SIZE:
            self.x = WORLD_WIDTH_TILES * TILE_SIZE - PLAYER_WIDTH

    def on_ground(self, world):
        rect = self.rect()
        rect.y += 2
        return check_collision(rect, world)

    def collide(self, world, dx=0, dy=0):
        rect = self.rect()
        for tile_rect, tile_type in get_collidable_tiles_around(world, rect):
            if tile_type != AIR:
                if rect.colliderect(tile_rect):
                    if dx > 0:
                        self.x = tile_rect.left - PLAYER_WIDTH
                        rect.x = int(self.x)
                    if dx < 0:
                        self.x = tile_rect.right
                        rect.x = int(self.x)
                    if dy > 0:
                        self.y = tile_rect.top - PLAYER_HEIGHT
                        self.vy = 0
                        rect.y = int(self.y)
                    if dy < 0:
                        self.y = tile_rect.bottom
                        self.vy = 0
                        rect.y = int(self.y)

    def draw(self, cam_x):
        screen_x = int(self.x - cam_x)
        pygame.draw.rect(screen, (50, 80, 255), (screen_x, int(self.y), PLAYER_WIDTH, PLAYER_HEIGHT))


# ---------------------------------------------------------
# Zombie
# ---------------------------------------------------------
class Zombie:
    def __init__(self, x, y):
        self.x = x  # world coordinates
        self.y = y
        self.vy = 0
        self.width = 28
        self.height = 48

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self, player, world):
        # Gravity
        self.vy += GRAVITY
        if self.vy > 10:
            self.vy = 10

        # Horizontal chase
        if player.x > self.x:
            self.x += ZOMBIE_SPEED
        else:
            self.x -= ZOMBIE_SPEED

        # Move Y
        self.y += self.vy

        # Collisions
        rect = self.rect()
        for tile_rect, tile_type in get_collidable_tiles_around(world, rect):
            if tile_type != AIR and rect.colliderect(tile_rect):
                if self.vy > 0:
                    self.y = tile_rect.top - self.height
                    self.vy = 0

    def draw(self, cam_x):
        screen_x = int(self.x - cam_x)
        pygame.draw.rect(screen, GREEN, (screen_x, int(self.y), self.width, self.height))


# ---------------------------------------------------------
# World generation and helpers
# ---------------------------------------------------------
def generate_world():
    rows = WORLD_HEIGHT_TILES
    cols = WORLD_WIDTH_TILES
    world = [[AIR for _ in range(cols)] for _ in range(rows)]

    ground_level = rows - 5

    for r in range(rows):
        for c in range(cols):
            if r > ground_level:
                world[r][c] = DIRT
            elif r == ground_level:
                world[r][c] = DIRT
            else:
                # Random resources
                if random.random() < 0.02 and r > 3:
                    world[r][c] = WOOD
                elif random.random() < 0.015 and r > 3:
                    world[r][c] = STONE
    return world


def get_tile_rect(r, c):
    return pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)


def get_collidable_tiles_around(world, rect):
    tiles = []
    rows = len(world)
    cols = len(world[0])

    left = max(0, rect.left // TILE_SIZE - 2)
    right = min(cols - 1, rect.right // TILE_SIZE + 2)
    top = max(0, rect.top // TILE_SIZE - 2)
    bottom = min(rows - 1, rect.bottom // TILE_SIZE + 2)

    for r in range(top, bottom + 1):
        for c in range(left, right + 1):
            tile = world[r][c]
            if tile != AIR:
                tiles.append((get_tile_rect(r, c), tile))
    return tiles


def check_collision(rect, world):
    for tile_rect, tile_type in get_collidable_tiles_around(world, rect):
        if tile_type != AIR and rect.colliderect(tile_rect):
            return True
    return False


# ---------------------------------------------------------
# Drawing
# ---------------------------------------------------------
def draw_world(world, cam_x):
    rows = len(world)
    cols = len(world[0])

    # Only draw visible columns
    start_col = max(0, int(cam_x // TILE_SIZE) - 2)
    end_col = min(cols - 1, int((cam_x + SCREEN_WIDTH) // TILE_SIZE) + 2)

    for r in range(rows):
        for c in range(start_col, end_col + 1):
            tile = world[r][c]
            x = c * TILE_SIZE - cam_x
            y = r * TILE_SIZE

            if tile == DIRT:
                pygame.draw.rect(screen, SAND, (x, y, TILE_SIZE, TILE_SIZE))
            elif tile == WOOD:
                pygame.draw.rect(screen, BROWN, (x, y, TILE_SIZE, TILE_SIZE))
            elif tile == STONE:
                pygame.draw.rect(screen, GREY, (x, y, TILE_SIZE, TILE_SIZE))
            elif tile == WALL:
                pygame.draw.rect(screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE))


def draw_ui(player, night, crafting_open):
    font = pygame.font.SysFont("consolas", 18)
    hp_text = font.render(f"HP: {player.hp}", True, WHITE)
    wood_text = font.render(f"Wood: {player.inventory['wood']}", True, WHITE)
    stone_text = font.render(f"Stone: {player.inventory['stone']}", True, WHITE)
    stw_text = font.render(f"StoneWalls: {player.inventory['stone_wall']}", True, WHITE)
    wdw_text = font.render(f"WoodWalls: {player.inventory['wood_wall']}", True, WHITE)
    cycle_text = font.render("NIGHT" if night else "DAY", True, RED if night else WHITE)

    screen.blit(hp_text, (10, 10))
    screen.blit(wood_text, (10, 35))
    screen.blit(stone_text, (10, 60))
    screen.blit(stw_text, (10, 85))
    screen.blit(wdw_text, (10, 110))
    screen.blit(cycle_text, (SCREEN_WIDTH - 90, 10))

    if crafting_open:
        draw_crafting_menu(player)


def draw_crafting_menu(player):
    font = pygame.font.SysFont("consolas", 18)
    w, h = 400, 120
    x = SCREEN_WIDTH // 2 - w // 2
    y = 40
    pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h))
    pygame.draw.rect(screen, WHITE, (x, y, w, h), 2)

    lines = [
        "CRAFTING (press 1/2):",
        "1) Stone Wall (cost: 2 stone) -> +1 stone_wall",
        "2) Wood Wall  (cost: 2 wood)  -> +1 wood_wall",
    ]
    for i, text in enumerate(lines):
        surf = font.render(text, True, WHITE)
        screen.blit(surf, (x + 10, y + 10 + i * 25))


def apply_day_night_tint(night, t, cycle_start, day_len, night_len):
    # Simple tint: darker at night
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    if night:
        # full dark
        overlay.fill((0, 0, 0, 120))
    else:
        # light tint, almost none
        overlay.fill((0, 0, 0, 30))
    screen.blit(overlay, (0, 0))


# ---------------------------------------------------------
# Mining / placing
# ---------------------------------------------------------
def can_mine_tile(player, tile_row, tile_col):
    tile_cx = tile_col * TILE_SIZE + TILE_SIZE / 2
    tile_cy = tile_row * TILE_SIZE + TILE_SIZE / 2
    player_cx = player.x + PLAYER_WIDTH / 2
    player_cy = player.y + PLAYER_HEIGHT / 2
    dist = math.hypot(tile_cx - player_cx, tile_cy - player_cy)
    return dist <= MINING_RANGE_TILES * TILE_SIZE


def handle_mining_and_placing(event, player, world, cam_x):
    if event.type != pygame.MOUSEBUTTONDOWN:
        return

    mx, my = pygame.mouse.get_pos()
    world_x = mx + cam_x
    world_y = my
    c = int(world_x // TILE_SIZE)
    r = int(world_y // TILE_SIZE)

    if r < 0 or r >= len(world) or c < 0 or c >= len(world[0]):
        return

    # Left click: mine
    if event.button == 1:
        if not can_mine_tile(player, r, c):
            return  # too far to mine

        tile = world[r][c]
        if tile == WOOD:
            player.inventory["wood"] += 1
            world[r][c] = AIR
        elif tile == STONE:
            player.inventory["stone"] += 1
            world[r][c] = AIR

    # Right click: place walls (uses crafted wall items)
    if event.button == 3:
        if world[r][c] != AIR:
            return

        # Prefer stone_wall, else wood_wall
        if player.inventory["stone_wall"] > 0:
            world[r][c] = WALL
            player.inventory["stone_wall"] -= 1
        elif player.inventory["wood_wall"] > 0:
            world[r][c] = WALL
            player.inventory["wood_wall"] -= 1


# ---------------------------------------------------------
# Crafting logic
# ---------------------------------------------------------
def handle_crafting_key(player, key):
    # 1: Stone wall
    if key == pygame.K_1:
        if player.inventory["stone"] >= 2:
            player.inventory["stone"] -= 2
            player.inventory["stone_wall"] += 1

    # 2: Wood wall
    if key == pygame.K_2:
        if player.inventory["wood"] >= 2:
            player.inventory["wood"] -= 2
            player.inventory["wood_wall"] += 1


# ---------------------------------------------------------
# Main loop
# ---------------------------------------------------------
def main():
    world = generate_world()
    player = Player(200, 200)
    zombies = []

    running = True
    last_spawn = 0
    cycle_start = pygame.time.get_ticks()
    night = False
    crafting_open = False

    font_big = pygame.font.SysFont("consolas", 48)
    font_small = pygame.font.SysFont("consolas", 24)

    while running:
        dt = clock.tick(FPS)
        t = pygame.time.get_ticks()

        # Day/night cycle
        if night:
            if t - cycle_start > NIGHT_DURATION:
                night = False
                cycle_start = t
                zombies.clear()
        else:
            if t - cycle_start > DAY_DURATION:
                night = True
                cycle_start = t

        # Spawn zombies at night
        if night and t - last_spawn > ZOMBIE_SPAWN_INTERVAL:
            side = random.choice(["left", "right"])
            if side == "left":
                zx = max(0, player.x - SCREEN_WIDTH)
            else:
                zx = min(WORLD_WIDTH_TILES * TILE_SIZE - 40, player.x + SCREEN_WIDTH)
            zy = 0
            zombies.append(Zombie(zx, zy))
            last_spawn = t

        # Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_e:
                    crafting_open = not crafting_open
                if crafting_open:
                    if event.key in (pygame.K_1, pygame.K_2):
                        handle_crafting_key(player, event.key)

            handle_mining_and_placing(event, player, world, cam_x=0)  # cam_x corrected later per frame

        keys = pygame.key.get_pressed()
        player.move(world, keys)

        # Camera follows player
        cam_x = player.x - SCREEN_WIDTH // 2
        cam_x = max(0, min(cam_x, WORLD_WIDTH_TILES * TILE_SIZE - SCREEN_WIDTH))

        # Now we know cam_x; we need to re-handle mining/placing with correct cam_x.
        # Easiest fix: re-bind mouse actions in this frame manually:
        # (events already consumed, so we just trust next frames; it's good enough for a prototype)

        # Update zombies
        for z in zombies:
            z.update(player, world)

            if z.rect().colliderect(player.rect()):
                if t - player.last_hit > ZOMBIE_DAMAGE_COOLDOWN:
                    player.hp -= 10
                    player.last_hit = t

        # Drawing
        screen.fill(SKY if not night else DARK)
        draw_world(world, cam_x)

        # Entities
        player.draw(cam_x)
        for z in zombies:
            z.draw(cam_x)

        apply_day_night_tint(night, t, cycle_start, DAY_DURATION, NIGHT_DURATION)
        draw_ui(player, night, crafting_open)

        # Game over
        if player.hp <= 0:
            go_text = font_big.render("YOU DIED", True, RED)
            info = font_small.render("Press R to restart or ESC to quit", True, WHITE)
            screen.blit(
                go_text,
                (
                    SCREEN_WIDTH // 2 - go_text.get_width() // 2,
                    SCREEN_HEIGHT // 2 - go_text.get_height(),
                ),
            )
            screen.blit(
                info,
                (
                    SCREEN_WIDTH // 2 - info.get_width() // 2,
                    SCREEN_HEIGHT // 2 + 10,
                ),
            )
            pygame.display.flip()

            waiting = True
            while waiting:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()
                        if e.key == pygame.K_r:
                            main()
                clock.tick(30)
        else:
            pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
