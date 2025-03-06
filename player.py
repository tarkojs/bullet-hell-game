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
        self.health = 50  # Player can take 5 hits
        self.weapon_level = 1  # Start at level 1
        self.shield_active = False  # Track shield state
        self.shield_radius = 30  # Distance from player
        self.shield_width = 20  # Shield width
        self.shield_height = 40  # Shield height (taller for shield shape)

    def move(self, keys):
        speed_boost = 1 + (self.weapon_level - 1) * 0.3
        speed = self.base_speed * (speed_boost if keys[pygame.K_SPACE] else 1.0)
        self.toggle_shield(keys)  # Update shield state
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
    
    def get_shield_rect(self, mouse_pos, camera):
        if not self.shield_active:
            return None, 0, 0
        world_mx = mouse_pos[0] + camera.x
        world_my = mouse_pos[1] + camera.y
        dx = world_mx - self.x
        dy = world_my - self.y
        angle = math.atan2(dy, dx)
        # Shield position relative to player, rotated to face cursor
        shield_x = self.x + self.shield_radius * math.cos(angle + math.pi)  # Behind player
        shield_y = self.y + self.shield_radius * math.sin(angle + math.pi)
        # Rotate shield to face cursor, maintaining shield shape
        angle_deg = math.degrees(angle + math.pi)  # Flip to face away from player
        shield_rect = pygame.Rect(shield_x - self.shield_width/2, shield_y - self.shield_height/2, self.shield_width, self.shield_height)
        return shield_rect, angle_deg, angle
    
    def draw_shield(self, mouse_pos, camera):
        shield_rect, angle_deg, angle = self.get_shield_rect(mouse_pos, camera)
        if shield_rect:
            screen = pygame.display.get_surface()
            shield_surface = pygame.Surface((self.shield_width, self.shield_height), pygame.SRCALPHA)
            pygame.draw.rect(shield_surface, (100, 100, 255, 128), (0, 0, self.shield_width, self.shield_height))
            rotated_shield = pygame.transform.rotate(shield_surface, -angle_deg)
            pos = camera.apply((self.x + self.shield_radius * math.cos(angle + math.pi), self.y + self.shield_radius * math.sin(angle + math.pi)))
            screen.blit(rotated_shield, (pos[0] - rotated_shield.get_width()/2, pos[1] - rotated_shield.get_height()/2))

    def take_damage(self, damage=1):
        self.health -= damage  # Reduce health by damage amount (default 1)
        return self.health <= 0  # Return True if dead
    
    def toggle_shield(self, keys):
        self.shield_active = keys[pygame.K_k]  # Activate shield with 'S' key
        