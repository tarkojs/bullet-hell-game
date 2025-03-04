import math
import pygame

# Player-specific configurations
PLAYER_SIZE = 20
PLAYER_SPEED = 5
PLAYER_COLOR = (0, 0, 255)  # Blue
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)

class Player:
    def __init__(self, x, y, world_width, world_height):
        self.x = x
        self.y = y
        self.base_speed = PLAYER_SPEED
        self.size = PLAYER_SIZE
        self.world_width = world_width
        self.world_height = world_height
        self.health = 5  # Player can take 5 hits
        self.weapon_level = 1  # Start at level 1

    def move(self, keys):
        speed_boost = 1 + (self.weapon_level - 1) * 0.3  # +30% per level above 1
        speed = self.base_speed * (speed_boost if keys[pygame.K_SPACE] else 1.0)
        if keys[pygame.K_w] and self.y > 0:
            self.y -= speed
        if keys[pygame.K_s] and self.y < self.world_height - self.size:
            self.y += speed
        if keys[pygame.K_a] and self.x > 0:
            self.x -= speed
        if keys[pygame.K_d] and self.x < self.world_width - self.size:
            self.x += speed

    def draw(self, camera):
        pos = camera.apply((self.x, self.y))
        pygame.draw.rect(pygame.display.get_surface(), PLAYER_COLOR, (pos[0], pos[1], self.size, self.size))
        health_width = (self.size * self.health) // 3
        pygame.draw.rect(pygame.display.get_surface(), GREEN, (pos[0], pos[1] - 10, health_width, 5))

    def get_center(self):
        return (self.x + self.size/2, self.y + self.size/2)

    def shoot_spam(self, mouse_pos, camera):
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            world_mx = mouse_pos[0] + camera.x
            world_my = mouse_pos[1] + camera.y
            center = self.get_center()
            dx = world_mx - center[0]
            dy = world_my - center[1]
            base_angle = math.atan2(dy, dx)
            bullets = []
            if self.weapon_level == 1:
                bullets.append((center[0], center[1], base_angle))
            elif self.weapon_level == 2:
                bullets.extend([
                    (center[0], center[1], base_angle, 'purple'),
                    (center[0], center[1], base_angle + 0.2, 'purple'),
                    (center[0], center[1], base_angle - 0.2, 'purple')
                ])
            else:  # Level 3+
                for i in range(self.weapon_level):
                    phase = i / self.weapon_level  # Spread phases evenly
                    angle_offset = (i - (self.weapon_level - 1) / 2) * 0.2  # Spread angles
                    bullets.append((center[0], center[1], base_angle + angle_offset, 'orange', phase))
            return bullets
        return []

    def take_damage(self):
        self.health -= 1
        return self.health <= 0  # Return True if dead
        