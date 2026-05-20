import asyncio
import pygame
import random
import math

pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 900, 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("KimYoodam Pihagi")

clock = pygame.time.Clock()

enemy_image = pygame.image.load("yudam.png").convert_alpha()
enemy_image = pygame.transform.smoothscale(enemy_image, (36, 48))

FONT_SM = pygame.font.SysFont("arial", 28)
FONT_LG = pygame.font.SysFont("arial", 60)
FONT_XL = pygame.font.SysFont("arial", 90)

BULLET_SPEED = 3
SHOOT_DELAY = 1000

BLUE = (70, 70, 255)
RED = (230, 80, 80)
GOLD = (255, 200, 0)
WHITE = (245, 245, 245)
BLACK = (30, 30, 30)
GREEN = (0, 200, 30)


def random_pos(margin=40):
    return (
        random.randint(margin, WIDTH - margin),
        random.randint(margin, HEIGHT - margin)
    )


def draw_text(surface, text, x, y, color=BLACK, font=None):
    f = font or FONT_SM
    img = f.render(text, True, color)
    surface.blit(img, (x, y))


class GameObject:
    def __init__(self, x, y, radius, color):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.color = color
        self.alive = True

    def draw(self, surface):
        pygame.draw.circle(
            surface,
            self.color,
            (int(self.x), int(self.y)),
            self.radius
        )

    def dist(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    def hits(self, other):
        return self.dist(other) < self.radius + other.radius


class Player(GameObject):
    def __init__(self):
        super().__init__(WIDTH // 2, HEIGHT // 2, 20, BLUE)

        self.hp = 3
        self.score = 0

        self.last_shot = 0
        self.shield_until = 0

    def update(self, now):
        keys = pygame.key.get_pressed()

        speed = 5

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= speed

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += speed

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= speed

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += speed

        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

        if now - self.last_shot > SHOOT_DELAY:
            self.last_shot = now
            return True

        return False

    def draw(self, surface):
        ticks = pygame.time.get_ticks()

        if ticks < self.shield_until:
            if (ticks // 150) % 2 == 0:
                return

        super().draw(surface)

        pygame.draw.circle(
            surface,
            BLACK,
            (int(self.x), int(self.y)),
            self.radius,
            3
        )

        pygame.draw.circle(
            surface,
            BLACK,
            (int(self.x) - 5, int(self.y) - 4),
            2
        )

        pygame.draw.circle(
            surface,
            BLACK,
            (int(self.x) + 5, int(self.y) - 4),
            2
        )


class Enemy(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 18, RED)

        self.personality = random.random()

    def update(self, player, time_ratio):
        min_speed = 1.2 + 1.8 * time_ratio
        max_speed = 1.5 + 2.5 * time_ratio

        speed = min_speed + (
            max_speed - min_speed
        ) * self.personality

        d = self.dist(player)

        if d > 0:
            self.x += (player.x - self.x) / d * speed
            self.y += (player.y - self.y) / d * speed

    def draw(self, surface):
        rect = enemy_image.get_rect(
            center=(int(self.x), int(self.y))
        )

        surface.blit(enemy_image, rect)


class Bullet(GameObject):
    def __init__(self, x, y, target):
        super().__init__(x, y, 8, (130, 130, 130))

        d = math.hypot(
            target.x - x,
            target.y - y
        )

        if d == 0:
            self.vx = 0
            self.vy = 0
        else:
            self.vx = (
                (target.x - x) / d
            ) * BULLET_SPEED

            self.vy = (
                (target.y - y) / d
            ) * BULLET_SPEED

    def update(self):
        self.x += self.vx
        self.y += self.vy

        if (
            self.x < 0 or
            self.x > WIDTH or
            self.y < 0 or
            self.y > HEIGHT
        ):
            self.alive = False


class Coin(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 12, GOLD)

        self.t = 0

    def update(self):
        self.t += 0.12

        self.radius = int(
            12 + math.sin(self.t) * 2
        )

    def draw(self, surface):
        super().draw(surface)

        pygame.draw.circle(
            surface,
            WHITE,
            (int(self.x) - 3, int(self.y) - 3),
            3
        )


class Potion(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 12, GREEN)

        self.t = 0

    def update(self):
        self.t += 0.12

        self.radius = int(
            12 + math.sin(self.t) * 2
        )


class Game:
    def __init__(self):
        self.flash = pygame.Surface((WIDTH, HEIGHT))
        self.flash.fill(RED)

        self.running = True

        self.reset()

    def reset(self):
        self.player = Player()

        self.enemies = []
        self.coins = []
        self.bullets = []
        self.potions = []

        self.over = False

        self.start_time = pygame.time.get_ticks()

        self.elapsed = 0

        self.last_enemy_spawn = 0
        self.last_potion_spawn = 0

        self.flash_alpha = 0

        for _ in range(5):
            self.enemies.append(
                Enemy(*self.safe_pos())
            )

        for _ in range(8):
            self.coins.append(
                Coin(*random_pos())
            )

    def safe_pos(self, min_dist=200):
        while True:
            x, y = random_pos()

            if math.hypot(
                x - self.player.x,
                y - self.player.y
            ) > min_dist:
                return x, y

    def handle_events(self):
        for e in pygame.event.get():

            if e.type == pygame.QUIT:
                self.running = False

            elif e.type == pygame.KEYDOWN:

                if (
                    self.over and
                    e.key == pygame.K_r
                ):
                    self.reset()

    def update(self):
        now = pygame.time.get_ticks()

        if self.over:
            return

        elapsed_time = now - self.start_time

        self.elapsed = elapsed_time

        time_ratio = min(
            1.0,
            elapsed_time / 80000
        )

        if now - self.last_enemy_spawn > 800:
            self.last_enemy_spawn = now

            self.enemies.append(
                Enemy(*self.safe_pos())
            )

        if now - self.last_potion_spawn > 15000:
            self.last_potion_spawn = now

            self.potions.append(
                Potion(*random_pos())
            )

        if self.enemies and self.player.update(now):
            target = min(
                self.enemies,
                key=self.player.dist
            )

            self.bullets.append(
                Bullet(
                    self.player.x,
                    self.player.y,
                    target
                )
            )

        for enemy in self.enemies:
            enemy.update(
                self.player,
                time_ratio
            )

        for bullet in self.bullets:
            bullet.update()

        for coin in self.coins:
            coin.update()

        for potion in self.potions:
            potion.update()

        self.handle_collisions()

    def handle_collisions(self):
        for bullet in self.bullets:
            for enemy in self.enemies:

                if bullet.hits(enemy):
                    bullet.alive = False
                    enemy.alive = False
                    break

        self.bullets = [
            b for b in self.bullets
            if b.alive
        ]

        self.enemies = [
            e for e in self.enemies
            if e.alive
        ]

        for coin in self.coins:

            if (
                coin.alive and
                self.player.hits(coin)
            ):
                coin.alive = False
                self.player.score += 1

        self.coins = [
            c for c in self.coins
            if c.alive
        ]

        if len(self.coins) == 0:

            for _ in range(8):
                self.coins.append(
                    Coin(*random_pos())
                )

        now = pygame.time.get_ticks()

        for enemy in self.enemies:

            if (
                self.player.hits(enemy) and
                now > self.player.shield_until
            ):
                self.player.hp -= 1

                self.player.shield_until = (
                    now + 1000
                )

                self.flash_alpha = 140

                if self.player.hp <= 0:
                    self.over = True

        for potion in self.potions:

            if self.player.hits(potion):
                potion.alive = False
                self.player.hp += 1

        self.potions = [
            p for p in self.potions
            if p.alive
        ]

    def draw(self):
        screen.fill(WHITE)

        for obj in (
            self.coins +
            self.potions +
            self.bullets +
            self.enemies +
            [self.player]
        ):
            obj.draw(screen)

        draw_text(
            screen,
            f"Score: {self.player.score}",
            15,
            15
        )

        draw_text(
            screen,
            f"HP: {self.player.hp}",
            15,
            45
        )

        draw_text(
            screen,
            f"{self.elapsed / 1000:.1f}s",
            800,
            15
        )

        if self.over:
            draw_text(
                screen,
                "GAME OVER",
                220,
                220,
                RED,
                FONT_XL
            )

            draw_text(
                screen,
                f"Final Score: {self.player.score}",
                300,
                330,
                BLACK,
                FONT_LG
            )

            draw_text(
                screen,
                "Press R to Restart",
                340,
                420,
                BLACK,
                FONT_SM
            )

        if self.flash_alpha > 0:
            self.flash.set_alpha(
                self.flash_alpha
            )

            screen.blit(
                self.flash,
                (0, 0)
            )

            self.flash_alpha -= 8

            if self.flash_alpha < 0:
                self.flash_alpha = 0

        pygame.display.flip()


async def main():
    game = Game()

    while game.running:
        await asyncio.sleep(0)

        game.handle_events()
        game.update()
        game.draw()

        clock.tick(60)


if __name__ == "__main__":
    asyncio.run(main())