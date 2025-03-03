import math
import time
import random
import pygame

# Enemy-specific configurations
ENEMY_SIZE = 40
ENEMY_HEALTH = 3
ENEMY_COLOR = (255, 0, 0)  # Red
HEALTH_COLOR = (0, 255, 0)  # Green for health bar

# Drops
DROP_COLOR = (255, 105, 180)  # Pink for drop
DROP_SIZE = 20  # Medium-size circle

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = ENEMY_SIZE
        self.health = ENEMY_HEALTH
        self.last_shot = time.time()
        self.base_speed = 1.5
        self.dodge_speed = 2.5
        self.random_walk_timer = 0
        self.random_angle = random.uniform(0, 2 * math.pi)
        self.dodge_cooldown = 0

    def aim_at_player(self, player):
        dx = player.x + player.size/2 - (self.x + self.size/2)
        dy = player.y + player.size/2 - (self.y + self.size/2)
        return math.atan2(dy, dx)

    def shoot(self, player):
        current_time = time.time()
        if current_time - self.last_shot >= 1:
            angle = self.aim_at_player(player)
            self.last_shot = current_time
            return [
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle),
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle + 0.2),
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle - 0.2)
            ]
        return []

    def move(self, projectiles, world_width, world_height):
        self.random_walk_timer -= 1
        if self.random_walk_timer <= 0:
            self.random_angle = random.uniform(0, 2 * math.pi)
            self.random_walk_timer = random.randint(60, 120)

        dodge_dx = dodge_dy = 0
        if self.dodge_cooldown <= 0:
            for p in projectiles:
                dist = math.hypot(p.x - (self.x + self.size/2), p.y - (self.y + self.size/2))
                if dist < 100:
                    angle_to_proj = math.atan2(self.y + self.size/2 - p.y, self.x + self.size/2 - p.x)
                    dodge_dx += math.cos(angle_to_proj + math.pi/2) * self.dodge_speed
                    dodge_dy += math.sin(angle_to_proj + math.pi/2) * self.dodge_speed
                    self.dodge_cooldown = 30
                    break

        self.dodge_cooldown -= 1

        dx = math.cos(self.random_angle) * self.base_speed + dodge_dx
        dy = math.sin(self.random_angle) * self.base_speed + dodge_dy

        self.x = max(0, min(self.x + dx, world_width - self.size))
        self.y = max(0, min(self.y + dy, world_height - self.size))

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        pygame.draw.rect(pygame.display.get_surface(), ENEMY_COLOR, (pos[0], pos[1], self.size, self.size))
        health_width = (self.size * self.health) // ENEMY_HEALTH
        pygame.draw.rect(pygame.display.get_surface(), HEALTH_COLOR, (pos[0], pos[1] - 10, health_width, 5))

    def spawn_drop(self):
        if random.random() < 0.9:  # 10% chance
            return Drop(self.x + self.size/2, self.y + self.size/2)
        return None

    def spawn_enemies(num_enemies, world_width, world_height):
        enemies = []
        for _ in range(num_enemies):
            # Random spawn within world bounds, avoiding edges
            x = random.randint(50, world_width - 50)
            y = random.randint(50, world_height - 50)
            enemies.append(Enemy(x, y))
        return enemies

class EnemyBullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.speed = 4
        self.radius = 5
        self.angle = angle

    def move(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        pygame.draw.circle(pygame.display.get_surface(), ENEMY_COLOR, (int(pos[0]), int(pos[1])), self.radius)

class Drop:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = DROP_SIZE

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        pygame.draw.circle(pygame.display.get_surface(), DROP_COLOR, (int(pos[0]), int(pos[1])), self.size//2)