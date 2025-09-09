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
GOLD = (212, 175, 55)

# Drops
DROP_COLOR = (255, 105, 180)  # Pink for drop
DROP_SIZE = 20  # Medium-size circle
ENEMY_IMAGE = None

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
        pygame.display.get_surface().blit(text_surface, pos)

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
        self.damage_texts = []  # Add damage text list
    
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

    def take_damage(self, damage=1):
        self.health -= damage
        self.damage_texts.append(DamageText(self.x + self.size/2, self.y, f"-{damage}", RED))
        return self.health <= 0

    def update_damage_texts(self):
        self.damage_texts = [text for text in self.damage_texts if text.update()]
        for baby in self.babies:
            baby.update_damage_texts()

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
        
        # Draw damage texts
        for text in self.damage_texts:
            text.draw(camera)
            
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

class FibonacciBullet:
    def __init__(self, origin_x, origin_y, target_x, target_y, theta0, damage=1, color='red'):
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.target_x = target_x
        self.target_y = target_y
        # Orientation toward target
        self.dir_angle = math.atan2(target_y - origin_y, target_x - origin_x)
        # Spiral parameters (tight, readable)
        self.theta0 = theta0
        # Halved traversal speed: reduce angular speed and radial growth
        self.omega = (10.0 / 60.0) * 0.5  # radians per frame
        self.a = -ENEMY_SIZE * 0.3  # start slightly behind enemy along -dir
        self.b = 3.0 * 0.5  # radial growth per radian
        self.spawn_time = time.time()
        self.damage = damage
        self.color = BLACK if color == 'black' else RED
        self.radius = 5
        # Initialize current position
        self.x = origin_x
        self.y = origin_y
        self.angle = self.dir_angle  # for compatibility
        self.speed = 4
        # Lifetime and collapse state
        self.max_lifetime = 0.5
        self.dying = False
        self.die_start = None
        self.die_duration = 0.3
        self.dead = False

    def move(self, reflected=False):
        if reflected:
            # Reflect straight back to origin at 30% faster speed
            dx = self.origin_x - self.x
            dy = self.origin_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.angle = math.atan2(dy, dx)
                step = self.speed * 1.3
                self.x += math.cos(self.angle) * step
                self.y += math.sin(self.angle) * step
            return
        # Check lifetime expiration and start collapse
        now = time.time()
        age = now - self.spawn_time
        if not self.dying and age >= self.max_lifetime:
            self.dying = True
            self.die_start = now
        # During collapse, keep position and shrink in draw; stop path update
        if self.dying:
            # Mark dead after animation completes
            if now - self.die_start >= self.die_duration:
                self.dead = True
            return
        # Spiral parametric motion toward target axis
        t = age
        theta = self.theta0 + self.omega * t * 60.0  # scale by frames assuming 60fps
        r = self.a + self.b * theta
        # Cap minimum radius to avoid getting stuck behind
        r = max(r, -ENEMY_SIZE * 0.4)
        # Cap maximum radius to keep bullets close to enemy
        r = min(r, ENEMY_SIZE * 3.2)  # Quadrupled from 0.8
        # Local spiral coordinates rotated by dir_angle
        cosd = math.cos(self.dir_angle)
        sind = math.sin(self.dir_angle)
        x_local = r * math.cos(theta)
        y_local = r * math.sin(theta)
        self.x = self.origin_x + x_local * cosd - y_local * sind
        self.y = self.origin_y + x_local * sind + y_local * cosd

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        # Collapse animation scale
        scale = 1.0
        if self.dying and self.die_start is not None:
            t = min(1.0, (time.time() - self.die_start) / self.die_duration)
            scale = max(0.0, 1.0 - t)
        draw_r = max(0, int(self.radius * scale))
        if draw_r > 0:
            pygame.draw.circle(pygame.display.get_surface(), GOLD, (int(pos[0]), int(pos[1])), draw_r)

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

class CoilEnemy:
    def __init__(self, cx, cy):
        self.x = cx
        self.y = cy
        self.size = int(ENEMY_SIZE * 0.5)
        self.health = 9999
        self.last_pulse = time.time()
        self.pulse_interval = 3.0
        self.pulse_duration_rise = 0.4
        self.pulse_duration_fall = 2.0
        self.pulse_start = None
        self.base_angle = random.uniform(0, 2 * math.pi)  # rotate patterns per pulse
        self.damage_texts = []
        self.babies = []  # API compatibility with main loop

    def take_damage(self, damage=1):
        # Stationary hazard; ignore damage
        return False

    def update_damage_texts(self):
        self.damage_texts = [text for text in self.damage_texts if text.update()]

    def move(self, projectiles, world_width, world_height, player=None):
        # Stationary
        now = time.time()
        if self.pulse_start is None and now - self.last_pulse >= self.pulse_interval:
            self.pulse_start = now
            # Change base angle each pulse
            self.base_angle = random.uniform(0, 2 * math.pi)
        elif self.pulse_start is not None:
            total = self.pulse_duration_rise + self.pulse_duration_fall
            if now - self.pulse_start >= total:
                self.pulse_start = None
                self.last_pulse = now

    def shoot(self, player=None):
        # Visual lasers; we can return empty since main handles EnemyBullet only
        return []

    def draw(self, camera):
        screen = pygame.display.get_surface()
        pos = camera.apply((self.x - self.size/2, self.y - self.size/2))
        # Draw a grey hexagon (6-corner triangle per request interpreted as hexagon)
        hex_radius = self.size/2
        points = []
        for i in range(6):
            ang = self.base_angle + i * (2 * math.pi / 6)
            px = pos[0] + hex_radius + hex_radius * math.cos(ang)
            py = pos[1] + hex_radius + hex_radius * math.sin(ang)
            points.append((px, py))
        pygame.draw.polygon(screen, (120, 120, 120), points)

        # Draw pulsing lasers when active
        if self.pulse_start is not None:
            now = time.time()
            t = now - self.pulse_start
            alpha = 0.0
            if t <= self.pulse_duration_rise:
                alpha = min(1.0, t / self.pulse_duration_rise)
            elif t <= self.pulse_duration_rise + self.pulse_duration_fall:
                t2 = t - self.pulse_duration_rise
                alpha = max(0.0, 1.0 - t2 / self.pulse_duration_fall)
            color = (173, 216, 230, int(alpha * 255))  # light blue with alpha
            laser_len = 500
            for i in range(6):
                ang = self.base_angle + i * (2 * math.pi / 6)
                ex = self.x + math.cos(ang) * laser_len
                ey = self.y + math.sin(ang) * laser_len
                p1 = camera.apply((self.x, self.y))
                p2 = camera.apply((ex, ey))
                sw, sh = screen.get_size()
                surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                pygame.draw.line(surf, color, p1, p2, 6)
                screen.blit(surf, (0, 0))

    def spawn_drop(self):
        return None  # Coil enemies don't drop anything

class BabyBoar:
    def __init__(self, mother, radius=100):
        self.mother = mother  # Reference to parent Enemy
        self.radius = radius  # Circle radius around mother
        self.angle = random.uniform(0, 2 * math.pi)  # Initial angle
        self.size = 40  # Smaller size for baby
        self.health = 5
        self.flee = False
        self.last_shot = time.time()
        self.damage_texts = []  # Add damage text list

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
        
        # Draw damage texts
        for text in self.damage_texts:
            text.draw(camera)
            
        self.last_x = self.x  # Update last_x for next frame

    def take_damage(self):
        self.health -= 1
        self.damage_texts.append(DamageText(self.x + self.size/2, self.y, "-1", YELLOW))
        return self.health <= 0  # Return True if dead

    def update_damage_texts(self):
        self.damage_texts = [text for text in self.damage_texts if text.update()]

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

class BabyFibonacciEnemy:
    def __init__(self, cx, cy):
        self.size = int(ENEMY_SIZE * 0.33)
        self.x = cx - self.size/2
        self.y = cy - self.size/2
        self.health = max(1, int(ENEMY_HEALTH * 5 * 0.33))
        self.base_speed = 1.5 * 3
        self.dodge_speed = 2.5 * 3
        self.random_walk_timer = 0
        self.random_angle = random.uniform(0, 2 * math.pi)
        self.dodge_cooldown = 0
        self.damage_texts = []
        self.babies = []  # API compatibility with main loop
        self.last_shot = time.time()
        self.spiral_index = 0
        # Timed random teleport parameters
        self.last_teleport = time.time()
        self.teleport_interval = 0.33
        self.render_scale = 1.0
        self.teleport_phase = None
        self.teleport_phase_start = 0.0
        self.teleport_count = 0  # Track number of teleports

    def take_damage(self, damage=1):
        self.health -= damage
        self.damage_texts.append(DamageText(self.x + self.size/2, self.y, f"-{damage}", RED))
        return self.health <= 0

    def update_damage_texts(self):
        self.damage_texts = [text for text in self.damage_texts if text.update()]

    def _teleport_random(self, world_width, world_height):
        self.teleport_count += 1
        if self.teleport_count == 1:
            # First teleport: move to a common location to create overlap
            # Use a fixed location that all babies will teleport to
            self.x = world_width // 2 - self.size // 2
            self.y = world_height // 2 - self.size // 2
        else:
            # Subsequent teleports: random direction
            angle = random.uniform(0, 2 * math.pi)
            self.x += math.cos(angle) * 50
            self.y += math.sin(angle) * 50
        self.x = max(0, min(self.x, world_width - self.size))
        self.y = max(0, min(self.y, world_height - self.size))

    def move(self, projectiles, world_width, world_height, player=None):
        now = time.time()
        if self.teleport_phase is None and now - self.last_teleport >= self.teleport_interval:
            self.teleport_phase = 'out'
            self.teleport_phase_start = now
        if self.teleport_phase == 'out':
            t = min(1.0, (now - self.teleport_phase_start) / 0.2)
            self.render_scale = max(0.0, 1.0 - t)
            if t >= 1.0:
                self._teleport_random(world_width, world_height)
                self.teleport_phase = 'in'
                self.teleport_phase_start = now
        elif self.teleport_phase == 'in':
            t = min(1.0, (now - self.teleport_phase_start) / 0.2)
            self.render_scale = min(1.0, t)
            if t >= 1.0:
                self.teleport_phase = None
                self.last_teleport = now
        # Simple random walk otherwise
        self.random_walk_timer -= 1
        if self.random_walk_timer <= 0:
            self.random_angle = random.uniform(0, 2 * math.pi)
            self.random_walk_timer = random.randint(30, 90)
        self.x += math.cos(self.random_angle) * self.base_speed
        self.y += math.sin(self.random_angle) * self.base_speed
        self.x = max(0, min(self.x, world_width - self.size))
        self.y = max(0, min(self.y, world_height - self.size))

    def shoot(self, player):
        now = time.time()
        fire_interval = 1.0 / 9.0
        if now - self.last_shot >= fire_interval:
            self.last_shot = now
            golden_angle = math.radians(137.50776405003785)
            theta = self.spiral_index * golden_angle
            self.spiral_index += 1
            cx = self.x + self.size/2
            cy = self.y + self.size/2
            pcx = player.x + player.size/2
            pcy = player.y + player.size/2
            back_offset = self.size * 0.25
            dir_angle = math.atan2(pcy - cy, pcx - cx)
            sx = cx - back_offset * math.cos(dir_angle)
            sy = cy - back_offset * math.sin(dir_angle)
            return [FibonacciBullet(sx, sy, pcx, pcy, theta, damage=1, color='red')]
        return []

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        screen = pygame.display.get_surface()
        # Draw dark-green circle scaled by render_scale
        color = (0, 100, 0)
        scaled_size = max(1, int(self.size * self.render_scale))
        temp = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
        pygame.draw.circle(temp, color, (scaled_size//2, scaled_size//2), scaled_size//2)
        screen.blit(temp, (pos[0] + (self.size - scaled_size)/2, pos[1] + (self.size - scaled_size)/2))
        # Health bar
        max_health = max(1, int(ENEMY_HEALTH * 5 * 0.33))
        health_width = int((self.size * self.health) / max(1, max_health))
        pygame.draw.rect(screen, HEALTH_COLOR, (pos[0], pos[1] - 10, health_width, 5))
        for text in self.damage_texts:
            text.draw(camera)

    def spawn_drop(self):
        return None  # Baby Fibonacci enemies don't drop anything

class FibonacciEnemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = ENEMY_SIZE
        self.health = ENEMY_HEALTH * 5
        self.base_speed = 1.5 * 3
        self.dodge_speed = 2.5 * 3
        self.random_walk_timer = 0
        self.random_angle = random.uniform(0, 2 * math.pi)
        self.dodge_cooldown = 0
        self.damage_texts = []
        self.babies = []  # For API compatibility with main loop
        self.last_shot = time.time()
        self.spiral_index = 0  # For Fibonacci spiral/golden-angle progression
        self.last_teleport = time.time()
        self.teleport_cooldown = 0.0
        self.teleport_phase = None  # None | 'out' | 'in'
        self.teleport_phase_start = 0.0
        self.render_scale = 1.0

    def take_damage(self, damage=1):
        self.health -= damage
        self.damage_texts.append(DamageText(self.x + self.size/2, self.y, f"-{damage}", RED))
        if self.health <= 0:
            # Prepare babies to spawn on death
            self.children_to_spawn = [
                BabyFibonacciEnemy(self.x + self.size/2, self.y + self.size/2) for _ in range(3)
            ]
            return True
        return False

    def update_damage_texts(self):
        self.damage_texts = [text for text in self.damage_texts if text.update()]

    def _maybe_start_teleport(self):
        now = time.time()
        if now - self.last_teleport >= self.teleport_cooldown and self.teleport_phase is None:
            self.teleport_phase = 'out'
            self.teleport_phase_start = now

    def _update_teleport_anim_and_maybe_move(self, player, world_width, world_height):
        if self.teleport_phase is None:
            self.render_scale = 1.0
            # Trigger teleport immediately if far from player (>300px)
            if player is not None:
                dx = (player.x + player.size/2) - (self.x + self.size/2)
                dy = (player.y + player.size/2) - (self.y + self.size/2)
                if math.hypot(dx, dy) > 600:
                    self.teleport_phase = 'out'
                    self.teleport_phase_start = time.time()
            return
        now = time.time()
        duration = 0.3
        if self.teleport_phase == 'out':
            t = min(1.0, (now - self.teleport_phase_start) / duration)
            self.render_scale = max(0.0, 1.0 - t)
            if t >= 1.0:
                # Move near player (<= 10px)
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(0, 10)
                self.x = max(0, min(player.x + player.size/2 + math.cos(angle) * dist - self.size/2, world_width - self.size))
                self.y = max(0, min(player.y + player.size/2 + math.sin(angle) * dist - self.size/2, world_height - self.size))
                self.teleport_phase = 'in'
                self.teleport_phase_start = now
        elif self.teleport_phase == 'in':
            t = min(1.0, (now - self.teleport_phase_start) / duration)
            self.render_scale = min(1.0, t)
            if t >= 1.0:
                self.teleport_phase = None
                self.last_teleport = now
                # Reset movement timers so it doesn't get stuck after teleport
                self.random_walk_timer = 0
                self.dodge_cooldown = 0
                self.just_teleported = True
                # Ensure shooting continues after teleport
                self.last_shot = now - 0.1  # Allow immediate shooting after teleport

    def move(self, projectiles, world_width, world_height, player=None):
        # Teleport logic and animation (distance-based in _update_... only)
        self._update_teleport_anim_and_maybe_move(player, world_width, world_height)
        if self.teleport_phase is not None:
            # During teleport animation, skip movement/dodge but allow shooting
            return

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

        self.x = max(0, min(self.x, world_width - self.size))
        self.y = max(0, min(self.y, world_height - self.size))

    def shoot(self, player):
        # Fire 36 bullets per second. Bullets follow a visible spiral trajectory
        # that starts slightly behind the enemy and curls toward the player's axis.
        now = time.time()
        fire_interval = 1.0 / 36.0
        # Always try to shoot regardless of teleport state
        if now - self.last_shot >= fire_interval:
            self.last_shot = now
            golden_angle = math.radians(137.50776405003785)
            theta = self.spiral_index * golden_angle
            self.spiral_index += 1
            enemy_cx = self.x + self.size/2
            enemy_cy = self.y + self.size/2
            player_cx = player.x + player.size/2
            player_cy = player.y + player.size/2
            # Spawn slightly behind the enemy along the ray to the player
            back_offset = ENEMY_SIZE * 0.25
            dir_angle = math.atan2(player_cy - enemy_cy, player_cx - enemy_cx)
            spawn_x = enemy_cx - back_offset * math.cos(dir_angle)
            spawn_y = enemy_cy - back_offset * math.sin(dir_angle)
            return [FibonacciBullet(spawn_x, spawn_y, player_cx, player_cy, theta, damage=1, color='red')]
        return []

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        screen = pygame.display.get_surface()
        # Draw dark-green circle with teleport scale applied
        color = (0, 100, 0)
        scaled_size = max(1, int(self.size * self.render_scale))
        # Render via temporary surface to keep circle centered while scaling
        temp = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
        pygame.draw.circle(temp, color, (scaled_size//2, scaled_size//2), scaled_size//2)
        screen.blit(temp, (pos[0] + (self.size - scaled_size)/2, pos[1] + (self.size - scaled_size)/2))
        # Health bar
        max_health = ENEMY_HEALTH * 5
        health_width = int((self.size * self.health) / max(1, max_health))
        pygame.draw.rect(screen, HEALTH_COLOR, (pos[0], pos[1] - 10, health_width, 5))
        # Damage texts
        for text in self.damage_texts:
            text.draw(camera)

    def spawn_drop(self):
        if random.random() < 0.9:
            return Drop(self.x + self.size/2, self.y + self.size/2)
        return None