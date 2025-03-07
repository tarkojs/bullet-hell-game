import pygame
import math
import time
import random
import asyncio

from player import Player
from enemy import Enemy, EnemyBullet, BabyBoar

pygame.font.init()

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH = 1440
HEIGHT = 800
WORLD_WIDTH = 1600  # Larger world dimensions
WORLD_HEIGHT = 1200
screen = pygame.display.set_mode((WIDTH, HEIGHT))
background_image = pygame.image.load('sprites/background.png').convert()  # Load image
background_image = pygame.transform.scale(background_image, (WORLD_WIDTH, WORLD_HEIGHT))  # Scale to world size
pygame.display.set_caption("Boardom")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
PURPLE = (128, 0, 128)  # Purple color
ORANGE = (255, 165, 0)
ENEMY_AMOUNT = 1

# Camera class
class Camera:
    def __init__(self, target):
        self.x = target.x + target.size/2 - WIDTH/2
        self.y = target.y + target.size/2 - HEIGHT/2

    def update(self, target):
        # Center camera on player
        self.x = target.x + target.size/2 - WIDTH/2
        self.y = target.y + target.size/2 - HEIGHT/2
        # Clamp camera to world bounds
        self.x = max(0, min(self.x, WORLD_WIDTH - WIDTH))
        self.y = max(0, min(self.y, WORLD_HEIGHT - HEIGHT))

    def apply(self, pos):
        # Apply camera offset to object positions
        return (pos[0] - self.x, pos[1] - self.y)

# Projectile class
class Projectile:
    def __init__(self, x, y, angle, color='green', phase=0):
        self.x = x
        self.y = y
        self.base_angle = angle
        self.speed = 7 + (2 if color == 'purple' else 5 if color == 'orange' else 0)
        self.radius = 5  # Used for collision, not drawing
        self.color = color
        self.phase = phase
        self.time = 0

    def move(self):
        if self.color == 'orange':
            self.time += 0.7
            oscillation = math.sin(self.time + self.phase) * (self.speed / 20)
            angle = self.base_angle + oscillation
            self.x += math.cos(angle) * self.speed
            self.y += math.sin(angle) * self.speed
        else:
            self.x += math.cos(self.base_angle) * self.speed
            self.y += math.sin(self.base_angle) * self.speed

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        if self.color == 'green':
            screen.blit(BULLET_MAIN, (pos[0] - 5, pos[1] - 5))  # Center on position
        elif self.color == 'purple':
            screen.blit(BULLET_PURPLE, (pos[0] - 5, pos[1] - 5))
        elif self.color == 'orange':
            screen.blit(BULLET_ORANGE, (pos[0] - 5, pos[1] - 5))

class DamageText:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.lifetime = 60  # Frames (1 second at 60 FPS)
        self.speed = -2  # Move upwards

    def update(self):
        self.y += self.speed  # Move up
        self.lifetime -= 1
        return self.lifetime > 0  # Return True if still alive

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        text_surface = pygame.font.Font(None, 36).render(self.text, True, self.color)
        screen.blit(text_surface, pos)

def load_bullet_sprites():
    global BULLET_MAIN, BULLET_PURPLE, BULLET_ORANGE
    BULLET_MAIN = pygame.image.load('sprites/projectiles/bullet_main.png').convert_alpha()
    BULLET_PURPLE = pygame.image.load('sprites/projectiles/bullet_main.png').convert_alpha()
    BULLET_ORANGE = pygame.image.load('sprites/projectiles/bullet_main.png').convert_alpha()
    BULLET_MAIN = pygame.transform.scale(BULLET_MAIN, (40, 40))
    BULLET_PURPLE = pygame.transform.scale(BULLET_PURPLE, (20, 20))
    BULLET_ORANGE = pygame.transform.scale(BULLET_ORANGE, (20, 20))

async def game_loop():
    load_bullet_sprites()  # Load assets before the loop
    player = Player(WORLD_WIDTH//2, WORLD_HEIGHT - 100, WORLD_WIDTH, WORLD_HEIGHT)
    enemies = Enemy.spawn_enemies(ENEMY_AMOUNT, WORLD_WIDTH, WORLD_HEIGHT)
    camera = Camera(player)
    projectiles = []
    enemy_bullets = []
    child_bullets = []
    drops = []  # Track active drops
    message = None  # For "Stellanator unlocked"
    message_timer = 3  # Display duration
    damage_texts = []
    clock = pygame.time.Clock()
    game_won = False
    game_lost = False
    spam_timer = 0
    exp = 0  # Experience points
    bullets_shot = 0  # Track bullets fired

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and not (game_won or game_lost):
                mx, my = pygame.mouse.get_pos()
                # Convert screen coordinates to world coordinates
                world_mx = mx + camera.x
                world_my = my + camera.y
                dx = world_mx - (player.x + player.size/2)
                dy = world_my - (player.y + player.size/2)
                angle = math.atan2(dy, dx)
                projectiles.append(Projectile(player.x + player.size/2, player.y + player.size/2, angle))
                bullets_shot += 1  # Increment bullet count
            if event.type == pygame.KEYDOWN and (game_won or game_lost) and event.key == pygame.K_SPACE:
                running = False

        if not (game_won or game_lost):
            keys = pygame.key.get_pressed()
            player.move(keys)
            camera.update(player)

            mx, my = pygame.mouse.get_pos()
            spam_timer -= 1
            if keys[pygame.K_SPACE] and spam_timer <= 0:
                bullet_data = player.shoot_spam((mx, my), camera)
                for data in bullet_data:
                    if len(data) == 5:  # Orange with phase
                        x, y, angle, color, phase = data
                        # Speed scales with weapon_level
                        proj = Projectile(x, y, angle, color, phase)
                        proj.speed += (player.weapon_level - 3) * 2  # +2 speed per level past 3
                        projectiles.append(proj)
                    elif len(data) == 4:  # Purple
                        x, y, angle, color = data
                        projectiles.append(Projectile(x, y, angle, color))
                    else:  # Green
                        x, y, angle = data
                        projectiles.append(Projectile(x, y, angle))
                    bullets_shot += 1
                spam_timer = 5

            for enemy in enemies[:]:
                enemy.move(projectiles, WORLD_WIDTH, WORLD_HEIGHT, player)
                enemy_bullets.extend(enemy.shoot(player))

            for enemy in enemies[:]:
                for baby in enemy.babies:
                    child_bullets.extend(baby.shoot(player))

            projectiles = [p for p in projectiles if 0 <= p.x <= WORLD_WIDTH and 0 <= p.y <= WORLD_HEIGHT]
            to_remove = []  # Collect projectiles to remove
            for p in projectiles[:]:
                p.move()
                hit = False  # Track if projectile hit something
                # Check enemy collisions
                for enemy in enemies[:]:
                    enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.size, enemy.size)
                    if enemy_rect.collidepoint(p.x, p.y):
                        enemy.health -= 1
                        hit = True
                        if enemy.health <= 0:
                            enemies.remove(enemy)
                            exp += 100
                            old_health = player.health
                            player.health += 1
                            if player.health > old_health:
                                damage_texts.append(DamageText(player.x + player.size/2, player.y, "+1", GREEN))
                            drop = enemy.spawn_drop()
                            if drop:
                                drops.append(drop)
                        break  # Only hit one enemy per projectile
                # Check baby collisions
                for mother in enemies[:]:
                    for baby in mother.babies[:]:
                        baby_rect = pygame.Rect(baby.x, baby.y, baby.size, baby.size)
                        if baby_rect.collidepoint(p.x, p.y):
                            if baby.take_damage():
                                mother.babies.remove(baby)
                            hit = True
                            break  # Only hit one baby per projectile
                if hit:
                    to_remove.append(p)  # Mark for removal
            for p in set(to_remove):  # Remove duplicates
                projectiles.remove(p)
            game_won = len(enemies) == 0

            enemy_bullets = [b for b in enemy_bullets if 0 <= b.x <= WORLD_WIDTH and 0 <= b.y <= WORLD_HEIGHT]

            player_rect = pygame.Rect(player.x, player.y, player.size, player.size)

            for drop in drops[:]:
                drop_rect = pygame.Rect(drop.x - drop.size/2, drop.y - drop.size/2, drop.size, drop.size)
                if player_rect.colliderect(drop_rect):
                    drops.remove(drop)
                    player.weapon_level += 1  # Upgrade to level 2
                    damage_texts.append(DamageText(player.x + player.size/2, player.y, "+1", GREEN))
                    player.health += 1
                    message = f"Stellanator level {player.weapon_level} unlocked"
                    message_timer = 120  # Show for 2 seconds at 60 FPS

            for b in enemy_bullets[:]:
                b.move()
                player_rect = pygame.Rect(player.x, player.y, player.size, player.size)
                shield_rect, _, _ = player.get_shield_rect((mx, my), camera)  # Unpack all three values
                if shield_rect and shield_rect.collidepoint(b.x, b.y):
                    # Set origin before reflecting
                    if b.origin_x is None or b.origin_y is None:
                        b.origin_x, b.origin_y = b.x, b.y
                    b.move(reflected=True)
                elif player_rect.collidepoint(b.x, b.y):
                    if player.take_damage(b.damage):
                        game_lost = True
                    else:
                        damage_texts.append(DamageText(player.x + player.size/2, player.y, f"-{b.damage}", RED))
                    enemy_bullets.remove(b)

            # After enemy_bullets handling:
            child_bullets = [b for b in child_bullets if 0 <= b.x <= WORLD_WIDTH and 0 <= b.y <= WORLD_HEIGHT]
            for b in child_bullets[:]:
                b.move()
                # Skip collision with source baby and its mother
                if hasattr(b, 'source'):
                    baby_rect = pygame.Rect(b.source.x, b.source.y, b.source.size, b.source.size)
                    mother_rect = pygame.Rect(b.source.mother.x, b.source.mother.y, b.source.mother.size, b.source.mother.size)
                    if baby_rect.collidepoint(b.x, b.y) or mother_rect.collidepoint(b.x, b.y):
                        continue  # Skip this bullet for now to avoid self-collision
                shield_rect, _, _ = player.get_shield_rect((mx, my), camera)
                if shield_rect and shield_rect.collidepoint(b.x, b.y):
                    dx = b.x - (player.x + player.size/2)
                    dy = b.y - (player.y + player.size/2)
                    b.angle = math.atan2(dy, dx)
                    b.speed *= 1.3
                elif player_rect.collidepoint(b.x, b.y):
                    if player.take_damage(b.damage):
                        game_lost = True
                    else:
                        damage_texts.append(DamageText(player.x + player.size/2, player.y, f"-{b.damage}", RED))
                    child_bullets.remove(b)

        # Draw everything
        bg_x = -camera.x % WORLD_WIDTH  # Tile horizontally
        bg_y = -camera.y % WORLD_HEIGHT  # Tile vertically
        screen.blit(background_image, (bg_x, bg_y))
        # Tile additional sections if camera exceeds image bounds
        if bg_x > 0:
            screen.blit(background_image, (bg_x - WORLD_WIDTH, bg_y))
        if bg_y > 0:
            screen.blit(background_image, (bg_x, bg_y - WORLD_HEIGHT))
        if bg_x > 0 and bg_y > 0:
            screen.blit(background_image, (bg_x - WORLD_WIDTH, bg_y - WORLD_HEIGHT))

        player.draw(camera)
        player.draw_shield((mx, my), camera)
        for enemy in enemies:
            enemy.draw(camera)
        for p in projectiles:
            p.draw(camera)
        for b in enemy_bullets:
            b.draw(camera)
        for b in child_bullets:
            b.draw(camera)
        for drop in drops:
            drop.draw(camera)
        for text in damage_texts[:]:
            if not text.update():  # Remove if lifetime expired
                damage_texts.remove(text)
            else:
                text.draw(camera)

        mx, my = pygame.mouse.get_pos()

        if message and message_timer > 0:
            font = pygame.font.Font(None, 36)
            text = font.render(message, True, BLACK)
            text_rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
            screen.blit(text, text_rect)
            message_timer -= 1

        font = pygame.font.Font(None, 48)  # Larger font for "HP"
        # HP bar (upper-right corner, reducing width, red at 1 HP)
        hp_box_width = 200
        hp_box_height = 50
        hp_box_x = WIDTH - hp_box_width - 10  # 10 pixels from right edge
        hp_box_y = 10  # 10 pixels from top
        max_health = 5  # Player can take 5 hits
        health_ratio = player.health / max_health
        bar_color = RED if player.health == 1 else GREEN  # Red at 1 HP, green otherwise
        bar_width = int(hp_box_width * health_ratio)  # Reduce width based on health
        # Draw dark gray outline first (sleek and thin, 2 pixels)
        outline_color = (50, 50, 50)  # Dark gray
        outline_width = 2
        pygame.draw.rect(screen, outline_color, (hp_box_x - outline_width, hp_box_y - outline_width, hp_box_width + 2 * outline_width, hp_box_height + 2 * outline_width), outline_width)
        # Draw health bar inside outline
        pygame.draw.rect(screen, bar_color, (hp_box_x, hp_box_y, bar_width, hp_box_height))
        # "HP" on left side of bar, larger text
        hp_label = font.render("HP", True, BLACK)
        screen.blit(hp_label, (hp_box_x + 10, hp_box_y + (hp_box_height - hp_label.get_height()) // 2))  # Center vertically
        # Keep EXP and Bullets in top-left
        exp_font = pygame.font.Font(None, 36)  # Smaller font for other stats
        exp_text = exp_font.render(f"EXP: {exp}", True, BLACK)
        bullets_text = exp_font.render(f"Bullets: {bullets_shot}", True, BLACK)
        screen.blit(exp_text, (10, 10))  # EXP at top-left
        screen.blit(bullets_text, (10, 40))  # Bullets below EXP

        if game_won:
            font = pygame.font.Font(None, 74)
            text = font.render("You Win! Press SPACE to restart", True, BLACK)
            text_rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
            screen.blit(text, text_rect)
        elif game_lost:
            font = pygame.font.Font(None, 74)
            text = font.render("You Lose! Press SPACE to restart", True, BLACK)
            text_rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
            screen.blit(text, text_rect)

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)  # Yield control to browser

    return False

# Entry point
if __name__ == "__main__":
    asyncio.run(game_loop())