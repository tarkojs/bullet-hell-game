import math
import time
import random
import pygame

# Enemy-specific configurations
ENEMY_SIZE = 80
ENEMY_HEALTH = 1
ENEMY_COLOR = (255, 0, 0)  # Red
HEALTH_COLOR = (0, 255, 0)  # Green for health bar

BLACK = (0, 0, 0)
RED = (255, 0, 0)

# Drops
DROP_COLOR = (255, 105, 180)  # Pink for drop
DROP_SIZE = 20  # Medium-size circle
ENEMY_IMAGE = None


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
        self.babies = []
        self.damage_boost = False
    
    ENEMY_IMAGE = None

    @classmethod
    def load_sprite(cls):
        if cls.ENEMY_IMAGE is None:
            cls.ENEMY_IMAGE = pygame.image.load("boar.png").convert_alpha()
            cls.ENEMY_IMAGE = pygame.transform.scale(cls.ENEMY_IMAGE, (ENEMY_SIZE, ENEMY_SIZE))
        return cls.ENEMY_IMAGE
    

    def aim_at_player(self, player):
        dx = player.x + player.size/2 - (self.x + self.size/2)
        dy = player.y + player.size/2 - (self.y + self.size/2)
        return math.atan2(dy, dx)

    def shoot(self, player):
        current_time = time.time()
        if current_time - self.last_shot >= 1:
            angle = self.aim_at_player(player)
            self.last_shot = current_time
            damage = 3 if self.damage_boost else 1  # 3 HP if boosted, 1 otherwise
            return [
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle, damage, 'black'),
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle + 0.2, damage, 'black'),
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle - 0.2, damage, 'black')
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

        # Move babies with mother, check if all babies are dead
        alive_babies = [b for b in self.babies if b.health > 0]
        self.babies = alive_babies
        self.damage_boost = len(self.babies) == 0  # Boost if no babies left

        for baby in self.babies:
            baby.move(world_width, world_height)

    def draw(self, camera):
        if Enemy.ENEMY_IMAGE is None:
            Enemy.load_sprite()  # Load sprite if not loaded
        pos = camera.apply((self.x, self.y))
        screen = pygame.display.get_surface()
        screen.blit(Enemy.ENEMY_IMAGE, (pos[0], pos[1]))
        health_width = (self.size * self.health) // ENEMY_HEALTH
        pygame.draw.rect(screen, HEALTH_COLOR, (pos[0], pos[1] - 10, health_width, 5))

        for baby in self.babies:
            baby.draw(camera)

    def spawn_drop(self):
        if random.random() < 0.9:  # 10% chance
            return Drop(self.x + self.size/2, self.y + self.size/2)
        return None

    @classmethod
    def spawn_enemies(cls, num_enemies, world_width, world_height):
        enemies = []
        for _ in range(num_enemies):
            x = random.randint(50, world_width - 50)
            y = random.randint(50, world_height - 50)
            enemy = cls(x, y)
            if random.random() < 0.1:  # 10% chance for babies
                enemy.babies.extend([BabyBoar(enemy) for _ in range(2)])  # 2 babies per mother
            enemies.append(enemy)
        return enemies

class EnemyBullet:
    def __init__(self, x, y, angle, damage=1, color='red', origin_x=None, origin_y=None):
        self.x = x
        self.y = y
        self.speed = 4
        self.radius = 5
        self.angle = angle
        self.damage = damage  # Store damage
        self.color = BLACK if color == 'black' else RED
        self.origin_x = origin_x if origin_x is not None else x  # Default to spawn position
        self.origin_y = origin_y if origin_y is not None else y

    def move(self, reflected=False):
        if not reflected:
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed
        else:
            # Reflect back to origin at 30% faster speed
            dx = self.origin_x - self.x
            dy = self.origin_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.angle = math.atan2(dy, dx)
                self.speed = 4 * 1.3  # 30% faster
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

class BabyBoar:
    def __init__(self, mother, radius=100):
        self.mother = mother  # Reference to parent Enemy
        self.radius = radius  # Circle radius around mother
        self.angle = random.uniform(0, 2 * math.pi)  # Initial angle
        self.size = 40  # Smaller size for baby
        self.health = 1

        # After imports:
    BABY_BOAR_IMAGE = None  # Placeholder for lazy loading

    @classmethod
    def load_baby_sprite(cls):
        if cls.BABY_BOAR_IMAGE is None:
            cls.BABY_BOAR_IMAGE = pygame.image.load("baby_boar.png").convert_alpha()
            cls.BABY_BOAR_IMAGE = pygame.transform.scale(cls.BABY_BOAR_IMAGE, (40, 40))  # Smaller size
        return cls.BABY_BOAR_IMAGE

    def move(self, world_width, world_height):
        # Circle mother while following her
        self.angle += 0.02  # Adjust speed of circling (0.05 radians per frame)
        # Position relative to mother, offset by circle radius
        self.x = self.mother.x + self.radius * math.cos(self.angle)
        self.y = self.mother.y + self.radius * math.sin(self.angle)
        # Clamp to world bounds
        self.x = max(0, min(self.x, world_width - self.size))
        self.y = max(0, min(self.y, world_height - self.size))

    def draw(self, camera):
        if BabyBoar.BABY_BOAR_IMAGE is None:
            BabyBoar.load_baby_sprite()
        pos = camera.apply((self.x, self.y))
        screen = pygame.display.get_surface()
        screen.blit(BabyBoar.BABY_BOAR_IMAGE, (pos[0], pos[1]))

    def take_damage(self):
        self.health -= 1
        return self.health <= 0  # Return True if dead