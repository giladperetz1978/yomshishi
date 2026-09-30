import pyxel
import json
from js import window


HEIGHT = 135
WIDTH = max(240, min(720, round(HEIGHT * window.document.getElementById("stage").clientWidth / max(1, window.document.getElementById("stage").clientHeight))))
WORLD_WIDTH = 2660
FLOOR_Y = 112
PLAYER_WIDTH = 10
PLAYER_HEIGHT = 18

FLOORS = [
    (0, 112, 550),
    (600, 112, 460),
    (1110, 112, 520),
    (1680, 112, 500),
    (2220, 112, 440),
]
PLATFORMS = [
    (125, 85, 58),
    (315, 74, 60),
    (690, 88, 64),
    (900, 72, 70),
    (1250, 80, 80),
    (1530, 70, 68),
    (1830, 84, 68),
    (2110, 74, 72),
    (2430, 81, 60),
]


class CourtRun:
    def __init__(self):
        pyxel.init(WIDTH, HEIGHT, title="COURT RUN", fps=30)
        pyxel.colors[1] = 0x153B3A
        pyxel.colors[3] = 0x278E77
        pyxel.colors[4] = 0xB77455
        pyxel.colors[5] = 0x528EAD
        pyxel.colors[8] = 0xF04F64
        pyxel.colors[9] = 0xFF993F
        pyxel.colors[11] = 0x8DEEB3
        pyxel.colors[12] = 0xB3E5EE
        pyxel.sounds[0].set("c3e3g3", "p", "3", "s", 5)
        pyxel.sounds[1].set("c3g3c4e4", "t", "3", "s", 4)
        pyxel.sounds[2].set("c2a1f1", "n", "3", "f", 5)
        pyxel.sounds[3].set("g3c4e4g4", "p", "3", "s", 6)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self):
        self.x = 34.0
        self.y = FLOOR_Y - PLAYER_HEIGHT
        self.vy = 0.0
        self.camera_x = 0
        self.score = 0
        self.lives = 3
        self.power = "NONE"
        self.growth = 0
        self.fire = 0
        self.invulnerable = 0
        self.phase = "play"
        self.player_name = "איתי שלומי"
        self.facing = 1
        self.speed = 0.0
        self.jumps = 0
        self.coyote = 0
        self.jump_buffer = 0
        self.dash = 0
        self.dash_cooldown = 0
        self.shot_cooldown = 0
        self.checkpoint = 34
        self.combo = 0
        self.combo_timer = 0
        self.elapsed = 0
        self.finish_timer = 0
        self.particles = []
        self.popups = []
        self.previous_buttons = set()
        self.tokens = [[float(token_x), 94.0, True] for token_x in range(210, 2550, 85) if self.floor_below(token_x) == FLOOR_Y]
        self.fireballs = []
        self.pickups = [
            [165.0, 68.0, "life", True],
            [350.0, 57.0, "growth", True],
            [730.0, 70.0, "fire", True],
            [960.0, 54.0, "life", True],
            [1285.0, 62.0, "growth", True],
            [1560.0, 52.0, "fire", True],
            [1860.0, 66.0, "life", True],
            [2145.0, 56.0, "growth", True],
            [2460.0, 62.0, "fire", True],
        ]
        self.enemies = [
            [285.0, 96.0, 250.0, 340.0, 1, 8],
            [780.0, 96.0, 740.0, 850.0, -1, 13],
            [1175.0, 96.0, 1130.0, 1260.0, 1, 9],
            [1450.0, 96.0, 1390.0, 1510.0, -1, 14],
            [1930.0, 96.0, 1880.0, 2010.0, 1, 8],
            [2290.0, 96.0, 2250.0, 2370.0, -1, 13],
        ]
        self.cones = [440.0, 630.0, 1010.0, 1350.0, 1630.0, 1770.0, 2050.0, 2370.0, 2575.0]

    def update(self):
        controls = window.courtControls
        if controls.restart or pyxel.btnp(pyxel.KEY_R):
            controls.restart = False
            self.reset()
        self.publish()
        if controls.paused:
            return
        if self.phase != "play":
            if self.phase == "dunk":
                self.finish_timer += 1
                self.y = 66 - pyxel.sin(min(180, self.finish_timer * 5)) * 15
                self.burst(WORLD_WIDTH - 30, 65, 10, 2)
                self.update_effects()
                if self.finish_timer >= 60:
                    self.phase = "won"
                    self.score += self.lives * 300 + max(0, 3000 - self.elapsed)
                    pyxel.play(0, 3)
            return

        self.elapsed += 1
        buttons = {name for name in ("left", "right", "jump", "shoot", "dash") if getattr(controls, name)}
        pressed = buttons - self.previous_buttons
        self.previous_buttons = buttons
        direction = int("right" in buttons or pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D)) - int("left" in buttons or pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A))
        if direction:
            self.facing = direction
        self.speed += (direction * 2.7 - self.speed) * 0.35
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if ("dash" in pressed or pyxel.btnp(pyxel.KEY_C)) and self.dash_cooldown == 0:
            self.dash = 9
            self.dash_cooldown = 75
            pyxel.play(1, 0)
        if self.dash > 0:
            self.dash -= 1
            self.speed = self.facing * 5.5
            self.burst(self.x + 5, self.y + 12, 11, 2)
        self.x = max(0, min(WORLD_WIDTH - 20, self.x + self.speed))
        on_ground = self.is_grounded()
        self.coyote = 4 if on_ground else max(0, self.coyote - 1)
        if on_ground:
            self.jumps = 0
        jump_pressed = (
            "jump" in pressed or pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_UP)
            or pyxel.btnp(pyxel.KEY_Z)
            or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A)
        )
        self.jump_buffer = 4 if jump_pressed else max(0, self.jump_buffer - 1)
        if self.jump_buffer and (self.coyote or self.jumps < 2):
            self.vy = -5.8 if self.jumps == 0 else -5.3
            self.jumps += 1
            self.jump_buffer = 0
            self.coyote = 0
            self.burst(self.x + 5, self.y + PLAYER_HEIGHT, 7, 8)
            pyxel.play(0, 0)

        previous_bottom = self.y + PLAYER_HEIGHT
        self.vy = min(self.vy + 0.42, 7)
        next_y = self.y + self.vy
        landed = False
        if self.vy >= 0:
            for platform_x, platform_y, platform_width in FLOORS + PLATFORMS:
                overlaps_x = self.x + PLAYER_WIDTH > platform_x and self.x < platform_x + platform_width
                crosses_top = previous_bottom <= platform_y and next_y + PLAYER_HEIGHT >= platform_y
                if overlaps_x and crosses_top:
                    next_y = platform_y - PLAYER_HEIGHT
                    self.vy = 0
                    landed = True
                    break
        self.y = next_y

        if self.y > HEIGHT + 10:
            self.take_hit(fallen=True)
            return

        if self.y + PLAYER_HEIGHT == FLOOR_Y:
            for floor_x, _floor_y, _floor_width in FLOORS:
                checkpoint = floor_x + 12
                if checkpoint > self.checkpoint and checkpoint <= self.x:
                    self.checkpoint = checkpoint
                    self.popups.append([checkpoint, 80, "CHECKPOINT", 60])
                    pyxel.play(0, 1)

        if self.invulnerable > 0:
            self.invulnerable -= 1
        if self.growth > 0:
            self.growth -= 1
            if self.growth == 0:
                self.power = "NONE"
        if self.fire > 0:
            self.fire -= 1
            if self.fire == 0:
                self.power = "NONE"

        self.update_enemies(previous_bottom, landed)
        if self.phase != "play":
            return
        for cone in self.cones[:]:
            if abs(self.x + 5 - cone) < 10 and self.y + PLAYER_HEIGHT > FLOOR_Y - 14:
                if self.growth > 0 or self.dash > 0:
                    self.cones.remove(cone)
                    self.award(50, cone, FLOOR_Y - 12)
                    self.burst(cone, FLOOR_Y - 8, 9, 12)
                else:
                    self.take_hit()
        if self.phase != "play":
            return
        self.update_pickups()
        self.update_fireballs()
        self.update_effects()
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0
        for token in self.tokens:
            if token[2] and abs(self.x + 5 - token[0]) < 10 and abs(self.y + 10 - token[1]) < 14:
                token[2] = False
                self.award(25, token[0], token[1])
                self.burst(token[0], token[1], 10, 5)
                pyxel.play(1, 1)

        self.shot_cooldown = max(0, self.shot_cooldown - 1)
        if "shoot" in buttons or pyxel.btn(pyxel.KEY_X) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_X):
            if self.fire > 0 and self.shot_cooldown == 0:
                self.fireballs.append([self.x + 5, self.y + 8, self.facing * 5])
                self.shot_cooldown = 10
                pyxel.play(1, 0)

        target_camera = max(0, min(self.x - WIDTH * 0.3, WORLD_WIDTH - WIDTH))
        self.camera_x += (target_camera - self.camera_x) * 0.15
        if self.x >= WORLD_WIDTH - 48:
            self.phase = "dunk"
            self.finish_timer = 0
            pyxel.play(0, 3)

    def publish(self):
        window.courtState = json.dumps({
            "name": self.player_name, "score": self.score, "lives": self.lives,
            "level": min(3, 1 + int(self.x / 900)), "phase": self.phase,
            "progress": min(100, round(self.x / (WORLD_WIDTH - 48) * 100)),
            "growth": self.growth, "fire": self.fire, "dash_cooldown": self.dash_cooldown,
        })

    def award(self, points, position_x, position_y):
        self.combo = min(5, self.combo + 1)
        self.combo_timer = 75
        earned = points * self.combo
        self.score += earned
        self.popups.append([position_x, position_y - 10, f"+{earned}", 30])

    def burst(self, position_x, position_y, color, count):
        for _particle in range(count):
            self.particles.append([position_x, position_y, pyxel.rndf(-2, 2), pyxel.rndf(-2.5, -0.5), color, 20])

    def update_effects(self):
        for particle in self.particles:
            particle[0] += particle[2]
            particle[1] += particle[3]
            particle[3] += 0.13
            particle[5] -= 1
        self.particles = [particle for particle in self.particles if particle[5] > 0]
        for popup in self.popups:
            popup[1] -= 0.35
            popup[3] -= 1
        self.popups = [popup for popup in self.popups if popup[3] > 0]

    def is_grounded(self):
        if self.vy < 0:
            return False
        bottom = self.y + PLAYER_HEIGHT
        for platform_x, platform_y, platform_width in FLOORS + PLATFORMS:
            if self.x + PLAYER_WIDTH > platform_x and self.x < platform_x + platform_width:
                if abs(bottom - platform_y) <= 1:
                    return True
        return False

    def update_enemies(self, previous_bottom, landed):
        for enemy in self.enemies[:]:
            enemy_x, enemy_y, left_edge, right_edge, direction, shirt = enemy
            enemy_x += direction * (0.65 + left_edge / WORLD_WIDTH * 0.65)
            if enemy_x <= left_edge or enemy_x >= right_edge:
                direction *= -1
            enemy[0] = enemy_x
            enemy[4] = direction
            enemy[1] = self.floor_below(enemy_x + 4) - 16

            close_x = abs(self.x + 5 - (enemy_x + 6)) < 13
            close_y = self.y + PLAYER_HEIGHT > enemy[1] + 2 and self.y < enemy[1] + 16
            if close_x and close_y:
                if self.dash > 0 or self.growth > 0 or ((self.vy > 0 or landed) and previous_bottom <= enemy[1] + 5):
                    self.enemies.remove(enemy)
                    self.vy = -4.5
                    self.jumps = 0
                    self.award(250, enemy_x, enemy[1])
                    self.burst(enemy_x + 5, enemy[1] + 8, shirt, 14)
                    pyxel.play(1, 1)
                elif self.invulnerable == 0:
                    self.take_hit()
                    return

    def update_pickups(self):
        for pickup in self.pickups:
            if not pickup[3]:
                continue
            x, y, kind, _alive = pickup
            bob_y = y + pyxel.sin(pyxel.frame_count * 4 + int(x)) * 2
            if abs(self.x + 5 - x) < 12 and abs(self.y + PLAYER_HEIGHT / 2 - bob_y) < 14:
                pickup[3] = False
                self.award(100, x, y)
                self.burst(x, y, 10, 15)
                pyxel.play(0, 3)
                if kind == "life":
                    self.lives = min(5, self.lives + 1)
                elif kind == "growth":
                    self.growth = 360
                    self.fire = 0
                    self.power = "BIG"
                else:
                    self.fire = 450
                    self.growth = 0
                    self.power = "FIRE"

    def update_fireballs(self):
        for ball in self.fireballs[:]:
            ball[0] += ball[2]
            if ball[0] < self.camera_x - 10 or ball[0] > self.camera_x + WIDTH + 10:
                self.fireballs.remove(ball)
                continue
            for enemy in self.enemies[:]:
                if abs(ball[0] - enemy[0] - 6) < 12 and abs(ball[1] - enemy[1] - 8) < 12:
                    self.enemies.remove(enemy)
                    self.fireballs.remove(ball)
                    self.award(250, enemy[0], enemy[1])
                    self.burst(enemy[0], enemy[1], 8, 12)
                    break
            for cone in self.cones[:]:
                if abs(ball[0] - cone) < 8 and FLOOR_Y - 20 < ball[1] < FLOOR_Y and ball in self.fireballs:
                    self.cones.remove(cone)
                    self.fireballs.remove(ball)
                    self.award(50, cone, FLOOR_Y - 15)
                    self.burst(cone, FLOOR_Y - 8, 9, 10)
                    break

    def floor_below(self, x):
        for floor_x, floor_y, floor_width in FLOORS:
            if floor_x <= x <= floor_x + floor_width:
                return floor_y
        return FLOOR_Y + 25

    def take_hit(self, fallen=False):
        if self.invulnerable > 0 and not fallen:
            return
        self.burst(self.x + 5, self.y + 8, 8, 16)
        pyxel.play(0, 2)
        self.lives -= 1
        self.invulnerable = 75
        self.combo = 0
        self.growth = 0
        self.fire = 0
        self.power = "NONE"
        self.dash = 0
        self.x = self.checkpoint
        self.y = FLOOR_Y - PLAYER_HEIGHT
        self.vy = 0
        self.speed = 0
        self.jumps = 0
        if self.lives <= 0:
            self.phase = "over"

    def draw_ball(self, x, y, color, label):
        pyxel.circ(x, y, 6, 0)
        pyxel.circ(x, y, 5, color)
        pyxel.line(x - 4, y - 2, x + 4, y + 2, 0)
        pyxel.line(x - 2, y - 4, x + 2, y + 4, 0)
        pyxel.text(x - 7, y - 15, label, 7)

    def draw_player(self):
        x = int(self.x)
        y = int(self.y)
        height = 24 if self.growth > 0 else PLAYER_HEIGHT
        top = y - (height - PLAYER_HEIGHT)
        frame = int(self.elapsed // 4 % 2) if abs(self.speed) > 0.3 else 0
        if self.invulnerable > 0 and pyxel.frame_count % 6 < 3:
            return

        pyxel.rect(x + 1, top + height - 5, 3, 5, 1)
        pyxel.rect(x + 7, top + height - 5, 3, 5, 1)
        pyxel.rect(x - (frame if self.is_grounded() else 0), top + height - 2, 5, 2, 7)
        pyxel.rect(x + 6, top + height - 2, 5, 2, 7)
        pyxel.elli(x - 2, self.floor_below(x + 5) - 2, 17, 3, 3)
        pyxel.rect(x + 2, top + 5, 7, height - 10, 11)
        pyxel.line(x + 2, top + 5, x + 8, top + 5, 7)
        pyxel.text(x + 4, top + 7, "7", 1)
        pyxel.rect(x + 3, top + 1, 6, 5, 4)
        pyxel.rect(x + 2, top, 8, 2, 1)
        pyxel.rect(x + (7 if self.facing > 0 else 3), top + 3, 1, 1, 0)
        pyxel.rect(x, top + 7, 2, 8, 4)
        pyxel.rect(x + 9, top + 7, 2, 8, 4)
        ball_x = x + (14 if self.facing > 0 else -4)
        ball_y = top + 10 + abs(pyxel.sin(self.elapsed * 24)) * 6
        if self.phase == "dunk":
            ball_y = top - 3
        pyxel.circ(ball_x, ball_y, 4, 9)
        pyxel.circb(ball_x, ball_y, 4, 1)
        pyxel.line(ball_x - 3, ball_y, ball_x + 3, ball_y, 1)
        pyxel.line(ball_x, ball_y - 3, ball_x, ball_y + 3, 1)

    def draw_rival(self, x, y, shirt):
        x = int(x)
        y = int(y)
        frame = pyxel.frame_count // 8 % 2
        pyxel.rect(x + 2, y + 10, 3, 5, 1)
        pyxel.rect(x + 8, y + 10, 3, 5, 1)
        pyxel.rect(x + 1, y + 14, 5, 2, 7)
        pyxel.rect(x + 7, y + 14, 5, 2, 7)
        pyxel.rect(x + 1, y + 5, 11, 7, shirt)
        pyxel.rect(x + 3, y + 1, 7, 5, 4)
        pyxel.rect(x + 2, y, 9, 2, 1)
        pyxel.rect(x + 8, y + 3, 1, 1, 0)
        pyxel.rect(x - 1, y + 6 + frame, 2, 6, 4)
        pyxel.rect(x + 11, y + 6 - frame, 2, 6, 4)
        pyxel.circ(x + 14, y + 11, 3, 9)

    def draw_cone(self, x, y):
        x = int(x)
        y = int(y)
        pyxel.rect(x - 7, y - 2, 15, 3, 1)
        pyxel.tri(x, y - 17, x + 6, y - 2, x - 6, y - 2, 9)
        pyxel.line(x - 4, y - 7, x + 4, y - 7, 10)
        pyxel.line(x - 6, y - 2, x, y - 17, 1)

    def draw(self):
        pyxel.cls(12)
        camera_x = int(self.camera_x)
        pyxel.circ(WIDTH - 45 - camera_x // 20, 24, 12, 10)

        for index in range(9):
            cloud_x = (index * 93 - camera_x // 4) % (WORLD_WIDTH + 80) - 30
            cloud_y = 17 + index % 3 * 12
            if -35 < cloud_x < WIDTH + 35:
                pyxel.circ(cloud_x, cloud_y, 6, 7)
                pyxel.circ(cloud_x + 7, cloud_y - 2, 8, 7)
                pyxel.circ(cloud_x + 15, cloud_y, 5, 7)

        for index in range(18):
            building_x = index * 155 - camera_x // 3
            if -80 < building_x < WIDTH + 80:
                building_h = 22 + index % 4 * 7
                pyxel.rect(building_x, FLOOR_Y - building_h, 55, building_h, 5 + index % 2)
                for window in range(3):
                    pyxel.rect(building_x + 8 + window * 14, FLOOR_Y - building_h + 7, 5, 5, 10)

        pyxel.rect(0, 98, WIDTH, 14, 3)
        for fence_x in range(-camera_x % 16 - 16, WIDTH, 16):
            pyxel.line(fence_x, 81, fence_x + 28, 109, 6)
            pyxel.line(fence_x, 109, fence_x + 28, 81, 6)
        pyxel.line(0, 81, WIDTH, 81, 1)
        pyxel.camera(camera_x, 0)
        for platform_x, platform_y, platform_width in FLOORS + PLATFORMS:
            if platform_x + platform_width < camera_x - 5 or platform_x > camera_x + WIDTH + 5:
                continue
            if platform_y == FLOOR_Y:
                pyxel.rect(platform_x, platform_y, platform_width, HEIGHT - platform_y, 3)
                pyxel.rect(platform_x, platform_y, platform_width, 2, 7)
                pyxel.rectb(platform_x + 12, platform_y + 7, platform_width - 24, 30, 11)
                pyxel.circb(platform_x + platform_width // 2, platform_y + 25, 17, 7)
                pyxel.line(platform_x + platform_width // 2, platform_y + 3, platform_x + platform_width // 2, HEIGHT, 7)
            else:
                pyxel.rect(platform_x, platform_y, platform_width, 5, 1)
                pyxel.rect(platform_x, platform_y, platform_width, 2, 10)
                pyxel.line(platform_x + 8, platform_y + 5, platform_x + 4, platform_y + 11, 1)
                pyxel.line(platform_x + platform_width - 8, platform_y + 5, platform_x + platform_width - 4, platform_y + 11, 1)

        for marker_x, _marker_y, _marker_width in FLOORS[1:]:
            pyxel.rect(marker_x + 20, 83, 2, 29, 1)
            pyxel.tri(marker_x + 22, 83, marker_x + 34, 87, marker_x + 22, 92, 11 if self.checkpoint >= marker_x + 12 else 10)
        hoop_x = WORLD_WIDTH - 24
        pyxel.rect(hoop_x, 51, 3, 61, 1)
        pyxel.rect(hoop_x - 2, 43, 5, 27, 7)
        pyxel.line(hoop_x - 19, 66, hoop_x, 66, 8)
        for net_x in range(hoop_x - 18, hoop_x, 4):
            pyxel.line(net_x, 67, net_x + 3, 77, 7)
        pyxel.text(hoop_x - 41, 31, "FINISH", 1)

        for token_x, token_y, alive in self.tokens:
            if alive and camera_x - 10 < token_x < camera_x + WIDTH + 10:
                pyxel.circ(token_x, token_y + pyxel.sin(self.elapsed * 5 + token_x) * 2, 3, 10)
                pyxel.line(token_x, token_y - 2, token_x, token_y + 2, 9)

        for cone in self.cones:
            if camera_x - 10 < cone < camera_x + WIDTH + 10:
                self.draw_cone(cone, FLOOR_Y)

        for pickup in self.pickups:
            x, y, kind, alive = pickup
            if not alive or x < camera_x - 15 or x > camera_x + WIDTH + 15:
                continue
            bob_y = y + pyxel.sin(pyxel.frame_count * 4 + int(x)) * 2
            if kind == "life":
                self.draw_ball(x, bob_y, 11, "1UP")
            elif kind == "growth":
                self.draw_ball(x, bob_y, 9, "BIG")
            else:
                self.draw_ball(x, bob_y, 8, "FIRE")

        for enemy in self.enemies:
            if camera_x - 20 < enemy[0] < camera_x + WIDTH + 20:
                self.draw_rival(enemy[0], enemy[1], enemy[5])

        for ball_x, ball_y, _speed in self.fireballs:
            pyxel.circ(ball_x, ball_y, 5, 8)
            pyxel.circ(ball_x, ball_y, 2, 10)
            pyxel.pset(ball_x - 6, ball_y + 2, 9)

        self.draw_player()
        for position_x, position_y, _speed_x, _speed_y, color, lifetime in self.particles:
            pyxel.rect(position_x, position_y, 2 if lifetime > 10 else 1, 2 if lifetime > 10 else 1, color)
        for position_x, position_y, text, _lifetime in self.popups:
            pyxel.text(position_x + 1, position_y + 1, text, 1)
            pyxel.text(position_x, position_y, text, 7)
        pyxel.camera()
        if self.combo > 1 and self.combo_timer:
            pyxel.rect(WIDTH // 2 - 23, 4, 46, 11, 1)
            pyxel.text(WIDTH // 2 - 19, 7, f"COMBO x{self.combo}", 10)


game = CourtRun()