import math
import runpy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class CourtRunTests(unittest.TestCase):
    def setUp(self):
        self.controls = SimpleNamespace(
            left=False, right=False, jump=False, shoot=False, dash=False,
            paused=False, restart=False,
        )
        stage = SimpleNamespace(clientWidth=844, clientHeight=262)
        self.window = SimpleNamespace(
            courtControls=self.controls,
            document=SimpleNamespace(getElementById=lambda _name: stage),
        )
        engine = MagicMock()
        engine.btn.return_value = False
        engine.btnp.return_value = False
        engine.frame_count = 0
        engine.sin.side_effect = lambda angle: math.sin(math.radians(angle))
        engine.rndf.side_effect = lambda low, high: (low + high) / 2
        source = Path(__file__).parents[1] / "public" / "games" / "basketball_run.py"
        with patch.dict(sys.modules, {"pyxel": engine, "js": SimpleNamespace(window=self.window)}):
            self.module = runpy.run_path(str(source))
        self.game = self.module["game"]

    def test_protagonist_is_fixed_after_restart(self):
        self.game.player_name = "other"
        self.controls.restart = True
        self.game.update()
        self.assertEqual(self.game.player_name, "איתי שלומי")
        self.assertFalse(self.controls.restart)

    def test_multitouch_movement_and_double_jump(self):
        self.controls.right = True
        self.controls.jump = True
        self.game.update()
        self.assertGreater(self.game.x, 34)
        self.assertLess(self.game.y, 94)
        self.assertEqual(self.game.jumps, 1)
        self.game.update()
        self.assertEqual(self.game.jumps, 1)
        self.controls.jump = False
        self.game.update()
        self.controls.jump = True
        self.game.update()
        self.assertEqual(self.game.jumps, 2)
        self.controls.jump = False
        self.game.update()
        self.controls.jump = True
        self.game.update()
        self.assertEqual(self.game.jumps, 2)

    def test_cone_costs_one_life_and_returns_to_safe_checkpoint(self):
        self.game.x = 430
        self.game.update()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.x, 34)
        self.assertEqual(self.game.y, 94)

    def test_growth_breaks_cone_without_losing_life(self):
        self.game.x = 430
        self.game.growth = 100
        self.game.update()
        self.assertNotIn(440, self.game.cones)
        self.assertEqual(self.game.lives, 3)
        self.assertGreater(self.game.score, 0)

    def test_fall_respawns_even_during_invulnerability(self):
        self.game.checkpoint = 612
        self.game.x = 1090
        self.game.y = 150
        self.game.invulnerable = 70
        self.game.update()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual((self.game.x, self.game.y), (612, 94))

    def test_checkpoint_activates_only_on_floor(self):
        self.game.x = 670
        self.game.y = 30
        self.game.update()
        self.assertEqual(self.game.checkpoint, 34)
        self.game.y = 94
        self.game.vy = 0
        self.game.update()
        self.assertEqual(self.game.checkpoint, 612)

    def test_respawn_is_clear_of_cone_after_protection_expires(self):
        self.game.x = 670
        self.game.update()
        self.game.take_hit(fallen=True)
        for _frame in range(90):
            self.game.update()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.x, 612)

    def test_dash_defeats_rival_and_has_cooldown(self):
        self.game.x = 274
        self.controls.dash = True
        self.game.update()
        self.assertEqual(len(self.game.enemies), 5)
        self.assertEqual(self.game.lives, 3)
        self.assertGreater(self.game.dash_cooldown, 0)

    def test_fire_follows_touch_direction_and_rate_limit(self):
        self.game.fire = 100
        self.controls.left = True
        self.controls.shoot = True
        self.game.update()
        self.assertEqual(len(self.game.fireballs), 1)
        self.assertLess(self.game.fireballs[0][2], 0)
        self.game.update()
        self.assertEqual(len(self.game.fireballs), 1)

    def test_high_projectile_does_not_break_ground_cone(self):
        self.game.fireballs = [[435, 20, 5]]
        self.game.update_fireballs()
        self.assertIn(440, self.game.cones)
        self.game.fireballs = [[435, 104, 5]]
        self.game.update_fireballs()
        self.assertNotIn(440, self.game.cones)

    def test_three_power_balls(self):
        for index, kind in enumerate(("life", "growth", "fire")):
            pickup = self.game.pickups[index]
            self.game.x = pickup[0] - 5
            self.game.y = pickup[1] - 9
            self.game.update_pickups()
            self.assertFalse(pickup[3])
            if kind == "life":
                self.assertEqual(self.game.lives, 4)
            elif kind == "growth":
                self.assertGreater(self.game.growth, 0)
            else:
                self.assertGreater(self.game.fire, 0)

    def test_pause_freezes_motion_and_timers(self):
        self.controls.right = True
        self.controls.paused = True
        self.game.fire = 100
        self.game.update()
        self.assertEqual(self.game.x, 34)
        self.assertEqual(self.game.fire, 100)
        self.assertEqual(self.game.elapsed, 0)

    def test_final_life_ends_game(self):
        self.game.lives = 1
        self.game.x = 430
        self.game.update()
        self.assertEqual(self.game.phase, "over")
        self.assertEqual(self.game.lives, 0)

    def test_finish_plays_dunk_before_victory(self):
        self.game.x = self.module["WORLD_WIDTH"] - 45
        self.game.update()
        self.assertEqual(self.game.phase, "dunk")
        for _frame in range(60):
            self.game.update()
        self.assertEqual(self.game.phase, "won")
        self.assertGreater(self.game.score, 0)


if __name__ == "__main__":
    unittest.main()