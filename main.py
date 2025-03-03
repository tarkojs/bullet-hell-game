import pygame
import math
import time
import random

from player import Player
from enemy import Enemy, EnemyBullet

pygame.font.init()

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH = 1440
HEIGHT = 800
WORLD_WIDTH = 1600  # Larger world dimensions
WORLD_HEIGHT = 1200
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bullet Hell Game with Camera")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
PURPLE = (128, 0, 128)  # Purple color
ORANGE = (255, 165, 0)
ENEMY_AMOUNT = 50

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

# Projectile class (for player bullets)
class Projectile:
    def __init__(self, x, y, angle, color='green', phase=0):
        self.x = x
        self.y = y
        self.base_angle = angle
        self.speed = 7 + (2 if color == 'purple' else 5 if color == 'orange' else 0)  # Base + increment
        self.radius = 5
        self.color = ORANGE if color == 'orange' else (PURPLE if color == 'purple' else GREEN)
        self.phase = phase
        self.time = 0

    def move(self):
        if self.color == 'orange':  # Sinusoidal for level 3+
            self.time += 0.1
            oscillation = math.sin(self.time + self.phase) * (self.speed / 20)  # Scale amplitude with speed
            angle = self.base_angle + oscillation
            self.x += math.cos(angle) * self.speed
            self.y += math.sin(angle) * self.speed
        else:  # Straight for level 1-2
            self.x += math.cos(self.base_angle) * self.speed
            self.y += math.sin(self.base_angle) * self.speed

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        pygame.draw.circle(screen, self.color, (int(pos[0]), int(pos[1])), self.radius)


# Enemy class

# Game function
def game_loop():
    player = Player(WORLD_WIDTH//2, WORLD_HEIGHT - 100, WORLD_WIDTH, WORLD_HEIGHT)
    enemies = Enemy.spawn_enemies(ENEMY_AMOUNT, WORLD_WIDTH, WORLD_HEIGHT)
    camera = Camera(player)
    projectiles = []
    enemy_bullets = []
    drops = []  # Track active drops
    message = None  # For "Stellanator unlocked"
    message_timer = 3  # Display duration
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
                return False
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
                return True

        if not (game_won or game_lost):
            keys = pygame.key.get_pressed()
            player.move(keys)
            camera.update(player)

            mx, my = pygame.mouse.get_pos()
            spam_timer -= 1
            # In main.py, update this part in game_loop():
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
            
            for enemy in enemies[:]:  # Use copy to allow removal
                enemy.move(projectiles, WORLD_WIDTH, WORLD_HEIGHT)  # Pass world bounds
                enemy_bullets.extend(enemy.shoot(player))
            
            projectiles = [p for p in projectiles if 0 <= p.x <= WORLD_WIDTH and 0 <= p.y <= WORLD_HEIGHT]
            to_remove = []  # Collect projectiles to remove
            for p in projectiles[:]:
                p.move()
                hit = False  # Track if projectile hit something
                for enemy in enemies[:]:
                    enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.size, enemy.size)
                    if enemy_rect.collidepoint(p.x, p.y):
                        enemy.health -= 1
                        hit = True
                        if enemy.health <= 0:
                            enemies.remove(enemy)
                            exp += 100
                            player.health += 1  # Health gain on kill
                            drop = enemy.spawn_drop()
                            if drop:
                                drops.append(drop)
                        break  # Only hit one enemy per projectile
                if hit:
                    to_remove.append(p)
            for p in set(to_remove):  # Remove duplicates
                projectiles.remove(p)
            game_won = len(enemies) == -100  # Fix win condition

            enemy_bullets = [b for b in enemy_bullets if 0 <= b.x <= WORLD_WIDTH and 0 <= b.y <= WORLD_HEIGHT]

            player_rect = pygame.Rect(player.x, player.y, player.size, player.size)

            for drop in drops[:]:
                drop_rect = pygame.Rect(drop.x - drop.size/2, drop.y - drop.size/2, drop.size, drop.size)
                if player_rect.colliderect(drop_rect):
                    drops.remove(drop)
                    player.weapon_level += 1  # Upgrade to level 2
                    message = f"Stellanator level {player.weapon_level} unlocked"
                    message_timer = 120  # Show for 2 seconds at 60 FPS
            
            for b in enemy_bullets:
                b.move()
                player_rect = pygame.Rect(player.x, player.y, player.size, player.size)
                if player_rect.collidepoint(b.x, b.y):
                    if player.take_damage():
                        game_lost = True
                    enemy_bullets.remove(b)

        # Draw everything
        screen.fill(WHITE)
        player.draw(camera)
        for enemy in enemies:
            enemy.draw(camera)
        for p in projectiles:
            p.draw(camera)
        for b in enemy_bullets:
            b.draw(camera)
        for drop in drops:
            drop.draw(camera)

        if message and message_timer > 0:
            font = pygame.font.Font(None, 36)
            text = font.render(message, True, BLACK)
            text_rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
            screen.blit(text, text_rect)
            message_timer -= 1

        font = pygame.font.Font(None, 36)
        hp_text = font.render(f"HP: {player.health}", True, BLACK)
        exp_text = font.render(f"EXP: {exp}", True, BLACK)
        bullets_text = font.render(f"Bullets: {bullets_shot}", True, BLACK)
        screen.blit(hp_text, (10, 10))  # HP at top-left
        screen.blit(exp_text, (10, 40))  # EXP below HP
        screen.blit(bullets_text, (10, 70))  # Bullets below EXP

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

    return False

# Main game loop
running = True
while running:
    running = game_loop()

pygame.quit()