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
YELLOW = (255, 255, 0)

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
        self.is_mother = False
        self.is_enraged = False
        self.initial_babies = 0
    
    ENEMY_IMAGE = None

    @classmethod
    def load_sprite(cls):
        if cls.ENEMY_IMAGE is None:
            cls.ENEMY_IMAGE = pygame.image.load('sprites/enemies/boar.png').convert_alpha()
            cls.ENEMY_IMAGE = pygame.transform.scale(cls.ENEMY_IMAGE, (ENEMY_SIZE, ENEMY_SIZE))
        return cls.ENEMY_IMAGE
    

    def aim_at_player(self, player):
        dx = player.x + player.size/2 - (self.x + self.size/2)
        dy = player.y + player.size/2 - (self.y + self.size/2)
        return math.atan2(dy, dx)

    def shoot(self, player):
        current_time = time.time()
        shot_delay = 0.2 if self.is_enraged else 1  # 1.5x faster when enraged
        if current_time - self.last_shot >= shot_delay:
            angle = self.aim_at_player(player)
            self.last_shot = current_time
            damage = 3 if self.damage_boost else 1
            color = BLACK if self.damage_boost else RED
            return [
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle, damage, color),
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle + 0.2, damage, color),
                EnemyBullet(self.x + self.size/2, self.y + self.size/2, angle - 0.2, damage, color)
            ]
        return []

    def move(self, projectiles, world_width, world_height, player=None):
        if self.is_enraged:
            current_time = time.time()
            if not hasattr(self, 'charge_timer') or self.charge_timer is None:
                self.charge_timer = current_time
                self.charging = True
                self.rest_start = None

            if self.charging:
                # Charge toward player at double bullet speed (8)
                dx = player.x + player.size/2 - (self.x + self.size/2)
                dy = player.y + player.size/2 - (self.y + self.size/2)
                angle = math.atan2(dy, dx)
                self.x += math.cos(angle) * 8
                self.y += math.sin(angle) * 8
                # Stop charging if close to player or after 1 second
                dist = math.hypot(dx, dy)
                if dist < 10 or current_time - self.charge_timer > 1:
                    self.charging = False
                    self.rest_start = current_time
            else:
                # Rest for 2 seconds with random movement
                if current_time - self.rest_start < 2:
                    self.random_walk_timer -= 1
                    if self.random_walk_timer <= 0:
                        self.random_angle = random.uniform(0, 2 * math.pi)
                        self.random_walk_timer = random.randint(60, 120)
                    dx = math.cos(self.random_angle) * self.base_speed
                    dy = math.sin(self.random_angle) * self.base_speed
                    self.x += dx
                    self.y += dy
                else:
                    # Reset for next charge
                    self.charging = True
                    self.charge_timer = current_time

            # Clamp to world bounds
            self.x = max(0, min(self.x, world_width - self.size))
            self.y = max(0, min(self.y, world_height - self.size))
        else:
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

            self.x += dx
            self.y += dy

            # Clamp to world bounds
            self.x = max(0, min(self.x, world_width - self.size))
            self.y = max(0, min(self.y, world_height - self.size))

        # Update babies
        alive_babies = [b for b in self.babies if b.health > 0]
        self.babies = alive_babies
        if self.is_mother:
            if len(self.babies) == 0 and self.initial_babies > 0 and not self.is_enraged:
                self.is_enraged = True
                self.damage_boost = True
                self.health = 30
            elif len(self.babies) == 1 and self.initial_babies > 1:
                self.babies[0].flee = True
                self.health = max(self.health, 10 if self.babies else 3)

        for baby in self.babies:
            baby.move(world_width, world_height, player=player)


    def draw(self, camera):
        if Enemy.ENEMY_IMAGE is None:
            Enemy.load_sprite()
        pos = camera.apply((self.x, self.y))
        screen = pygame.display.get_surface()
        if not hasattr(self, 'last_x'):
            self.last_x = self.x  # Initialize last_x
        dx = self.x - self.last_x
        # Flip sprite if moving left (dx < 0), keep default if moving right (dx >= 0)
        sprite = pygame.transform.flip(Enemy.ENEMY_IMAGE, dx < 0, False) if dx != 0 else Enemy.ENEMY_IMAGE
        # Tint red if enraged
        if self.is_enraged:
            tinted_image = Enemy.ENEMY_IMAGE.copy()
            tinted_image.fill((255, 0, 0, 128), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(tinted_image, (pos[0], pos[1]))
        else:
            screen.blit(sprite, (pos[0], pos[1]))
        health_width = (self.size * self.health) // (30 if self.is_enraged else 10 if self.is_mother else ENEMY_HEALTH)
        pygame.draw.rect(screen, HEALTH_COLOR, (pos[0], pos[1] - 10, health_width, 5))
        for baby in self.babies:
            baby.draw(camera)
        self.last_x = self.x

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
            if random.random() < 0.9:  # 10% chance for babies
                num_babies = random.randint(1, 3)  # 1-3 babies
                enemy.babies.extend([BabyBoar(enemy) for _ in range(num_babies)])
                enemy.is_mother = True
                enemy.initial_babies = num_babies
                enemy.health = 10  # Set mother HP
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

class ChildBullet:
    def __init__(self, x, y, angle, source):
        self.x = x
        self.y = y
        self.speed = 4  # 30% of EnemyBullet speed (4 * 0.3 = 1.2)
        self.angle = angle
        self.width = 20  # Long stick shape
        self.height = 5
        self.damage = 1
        self.source = source

    def move(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self, camera):
        pos = camera.apply((self.x - self.width/2, self.y - self.height/2))  # Center the stick
        screen = pygame.display.get_surface()
        bullet_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(bullet_surface, YELLOW, (0, 0, self.width, self.height))
        rotated_bullet = pygame.transform.rotate(bullet_surface, -math.degrees(self.angle))
        screen.blit(rotated_bullet, (pos[0], pos[1]))

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
        self.health = 5
        self.flee = False
        self.last_shot = time.time()

        # After imports:
    BABY_BOAR_IMAGE = None  # Placeholder for lazy loading

    @classmethod
    def load_baby_sprite(cls):
        if cls.BABY_BOAR_IMAGE is None:
            cls.BABY_BOAR_IMAGE = pygame.image.load('sprites/enemies/baby_boar.png').convert_alpha()
            cls.BABY_BOAR_IMAGE = pygame.transform.scale(cls.BABY_BOAR_IMAGE, (40, 40))  # Smaller size
        return cls.BABY_BOAR_IMAGE

    def move(self, world_width, world_height, player=None):
        if self.flee and player:
            # Run away from player
            dx = self.x - (player.x + player.size/2)
            dy = self.y - (player.y + player.size/2)
            angle = math.atan2(dy, dx)
            self.x += math.cos(angle) * 3  # Move at speed 3
            self.y += math.sin(angle) * 3
        else:
            self.angle += 0.02
            self.x = self.mother.x + self.radius * math.cos(self.angle)
            self.y = self.mother.y + self.radius * math.sin(self.angle)
        self.x = max(0, min(self.x, world_width - self.size))
        self.y = max(0, min(self.y, world_height - self.size))

    def draw(self, camera):
        if BabyBoar.BABY_BOAR_IMAGE is None:
            BabyBoar.load_baby_sprite()
        pos = camera.apply((self.x, self.y))
        screen = pygame.display.get_surface()
        if not hasattr(self, 'last_x'):
            self.last_x = self.x  # Initialize last_x
        dx = self.x - self.last_x
        # Flip sprite if moving left (dx < 0), keep default if moving right (dx >= 0)
        sprite = pygame.transform.flip(BabyBoar.BABY_BOAR_IMAGE, dx < 0, False) if dx != 0 else BabyBoar.BABY_BOAR_IMAGE
        screen.blit(sprite, (pos[0], pos[1]))
        self.last_x = self.x  # Update last_x for next frame

    def take_damage(self):
        self.health -= 1
        return self.health <= 0  # Return True if dead
    
    def shoot(self, player):
        if self.flee:
            return []
        current_time = time.time()
        if current_time - self.last_shot >= 1:
            self.last_shot = current_time
            angle = math.atan2(player.y + player.size/2 - (self.y + self.size/2), player.x + player.size/2 - (self.x + self.size/2))
            offset_x = self.x + self.size/2 + 10 * math.cos(angle)
            offset_y = self.y + self.size/2 + 10 * math.sin(angle)
            return [ChildBullet(offset_x, offset_y, angle, source=self)]
        return []   