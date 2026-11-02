"""
Comprehensive Unit Tests for TITAN 8 Turn Engine (test_engine_unit.py)
"""

import unittest
from engine import (
    TitanEngine,
    STAGE_PLANNING,
    STAGE_PLAYER_MOVED,
    STATE_PLAYING,
    STATE_VICTORY,
    STATE_DEFEAT,
    LEVELS
)

class TestTitanTurnEngine(unittest.TestCase):

    def test_level_1_the_deflection(self):
        """Move Right to (4,5) -> Center Pass. Dasher charges into mountain at (3,6) and dies."""
        eng = TitanEngine(current_level=0)
        self.assertEqual(eng.player_pos, [3, 5])
        self.assertEqual(eng.turn_stage, STAGE_PLANNING)

        # Move Right (3, 5) -> (4, 5)
        moved = eng.take_player_move(1, 0)
        self.assertTrue(moved)
        self.assertEqual(eng.player_pos, [4, 5])
        self.assertEqual(eng.turn_stage, STAGE_PLAYER_MOVED)
        self.assertTrue(eng.has_moved)

        # Second move in same turn must fail!
        moved_again = eng.take_player_move(1, 0)
        self.assertFalse(moved_again)

        # Pass / End Turn
        passed = eng.take_player_pass()
        self.assertTrue(passed)

        # Dasher should have charged up col 3 and smashed into mountain at (3, 6)
        self.assertEqual(len(eng.enemies), 0)
        self.assertEqual(eng.state, STATE_VICTORY)

    def test_level_2_crossfire(self):
        """Player at (4,4). Step away to (4,5) -> Pass. Both Dashers collide at (4,4) and die."""
        eng = TitanEngine(current_level=1)
        self.assertEqual(eng.player_pos, [4, 4])

        # Step away
        eng.take_player_move(0, 1) # to (4, 5)
        self.assertEqual(eng.player_pos, [4, 5])

        # Pass
        eng.take_player_pass()
        # Both Dashers ram each other at (4, 4)
        self.assertEqual(len(eng.enemies), 0)
        self.assertEqual(eng.state, STATE_VICTORY)

    def test_level_3_wall_slam(self):
        """Move to (3,4), then Shove Dasher at (4,4) into the Mountain at (5,4)."""
        eng = TitanEngine(current_level=2)
        self.assertEqual(eng.player_pos, [2, 4])

        # Move to (3, 4)
        eng.take_player_move(1, 0)
        self.assertEqual(eng.player_pos, [3, 4])

        # Shove Right into Dasher at (4, 4)
        shoved = eng.take_player_shove(1, 0)
        self.assertTrue(shoved)

        # Dasher slammed into Mountain at (5,4)
        self.assertEqual(len(eng.enemies), 0)
        self.assertEqual(eng.state, STATE_VICTORY)

    def test_level_4_mortar_trench(self):
        """Navigate fortified trench while dual mortars rain fire; slam battery into bunker wall."""
        eng = TitanEngine(current_level=3)
        self.assertEqual(eng.player_pos, [1, 3])

        # Turn 1: Step Down to (1, 4) -> Center Pass (dodge dual mortar blast at 1, 3)
        eng.take_player_move(0, 1)
        self.assertEqual(eng.player_pos, [1, 4])
        eng.take_player_pass()
        self.assertEqual(eng.player_hp, 2)
        self.assertEqual(len(eng.enemies), 2)

        # Turn 2: Step Right to (2, 4) -> Center Pass (dodge dual mortar blast at 1, 4)
        eng.take_player_move(1, 0)
        self.assertEqual(eng.player_pos, [2, 4])
        eng.take_player_pass()
        self.assertEqual(eng.player_hp, 2)
        self.assertEqual(len(eng.enemies), 2)

        # Turn 3: Step Right to (3, 4) -> Shove Right (1, 0) into Mortar 1 at (4, 4)
        eng.take_player_move(1, 0)
        self.assertEqual(eng.player_pos, [3, 4])
        shoved = eng.take_player_shove(1, 0)
        self.assertTrue(shoved)

        # Both mortars slammed into the bunker mountain wall at (6, 4) and die
        self.assertEqual(len(eng.enemies), 0)
        self.assertEqual(eng.state, STATE_VICTORY)
        self.assertEqual(eng.player_hp, 2)

    def test_level_5_dual_deflection(self):
        """2-Turn puzzle: Dodge 2 Dashers on T1, then shove Striker to intercept returning Dasher on T2."""
        eng = TitanEngine(current_level=4)
        self.assertEqual(eng.player_pos, [3, 3])

        # Turn 1: Step Down to (3, 4) -> Center Pass
        eng.take_player_move(0, 1)
        eng.take_player_pass()
        self.assertEqual(eng.player_hp, 2)
        self.assertEqual(len(eng.enemies), 2)  # Dasher 1 died on mountain (1, 6)

        # Turn 2: Step Left to (2, 4) -> Shove Up into Striker at (2, 3)
        eng.take_player_move(-1, 0)
        shoved = eng.take_player_shove(0, -1)
        self.assertTrue(shoved)
        self.assertEqual(len(eng.enemies), 0)  # Dasher 2 rammed shoved Striker at (2, 2)
        self.assertEqual(eng.state, STATE_VICTORY)
        self.assertEqual(eng.player_hp, 2)

    def test_level_6_the_2hp_sacrifice(self):
        """2-Turn puzzle: Absorb 1 collision dmg on T1, lethal shove on T2 with 1 HP remaining."""
        eng = TitanEngine(current_level=5)
        self.assertEqual(eng.player_pos, [1, 4])

        # Turn 1: Step Right to (2, 4) -> Center Pass (absorb Dasher 1 charge)
        eng.take_player_move(1, 0)
        eng.take_player_pass()
        self.assertEqual(eng.player_hp, 1)  # 1-HP alert state triggered!
        self.assertEqual(len(eng.enemies), 2)  # Dasher 1 died on player

        # Turn 2: Step Up to (2, 3) -> Shove Right into Striker at (3, 3)
        eng.take_player_move(0, -1)
        shoved = eng.take_player_shove(1, 0)
        self.assertTrue(shoved)
        self.assertEqual(len(eng.enemies), 0)  # Striker slammed into Dasher 2
        self.assertEqual(eng.state, STATE_VICTORY)
        self.assertEqual(eng.player_hp, 1)

    def test_level_7_the_triple_pincer(self):
        """3-Turn puzzle: Evade 2 Dasher vectors across two turns, then shove Striker to intercept."""
        eng = TitanEngine(current_level=6)
        self.assertEqual(eng.player_pos, [3, 3])

        # Turn 1: Step Left to (2, 3) -> Center Pass (Dasher 1 dies on mountain 1, 6)
        eng.take_player_move(-1, 0)
        eng.take_player_pass()
        self.assertEqual(eng.player_hp, 2)
        self.assertEqual(len(eng.enemies), 2)

        # Turn 2: Step Up to (2, 2) -> Center Pass (Dasher 2 charges north to 4, 0)
        eng.take_player_move(0, -1)
        eng.take_player_pass()
        self.assertEqual(eng.player_hp, 2)
        self.assertEqual(len(eng.enemies), 2)

        # Turn 3: Step Up to (2, 1) -> Shove Right into Striker at (3, 1)
        eng.take_player_move(0, -1)
        shoved = eng.take_player_shove(1, 0)
        self.assertTrue(shoved)
        self.assertEqual(len(eng.enemies), 0)  # Dasher 2 rams Striker at (4, 1)
        self.assertEqual(eng.state, STATE_VICTORY)
        self.assertEqual(eng.player_hp, 2)

    def test_level_8_the_crucible(self):
        """3-Turn Grand Finale: Wall-slam Striker + bait Dashers on T1, siege Mortar on T2-T3."""
        eng = TitanEngine(current_level=7)
        self.assertEqual(eng.player_pos, [3, 3])

        # Turn 1: Step Up to (3, 2) -> Shove Up into Striker at (3, 1) into mountain at (3, 0)
        eng.take_player_move(0, -1)
        shoved = eng.take_player_shove(0, -1)
        self.assertTrue(shoved)
        self.assertEqual(eng.player_hp, 2)
        self.assertEqual(len(eng.enemies), 1)  # Only Mortar remains at (6, 2)

        # Turn 2: Step Right to (4, 2) -> Center Pass (dodge Mortar blast aimed at 3, 2)
        eng.take_player_move(1, 0)
        eng.take_player_pass()
        self.assertEqual(eng.player_hp, 2)
        self.assertEqual(len(eng.enemies), 1)

        # Turn 3: Step Right to (5, 2) -> Shove Right into Mortar at (6, 2) into mountain at (7, 2)
        eng.take_player_move(1, 0)
        shoved = eng.take_player_shove(1, 0)
        self.assertTrue(shoved)
        self.assertEqual(len(eng.enemies), 0)
        self.assertEqual(eng.state, STATE_VICTORY)
        self.assertEqual(eng.player_hp, 2)

    def test_undo_functionality(self):
        """GPIO 9 Undo restores snapshot taken at turn start."""
        eng = TitanEngine(current_level=0)
        self.assertEqual(eng.player_pos, [3, 5])

        # Player moves
        eng.take_player_move(1, 0)
        self.assertEqual(eng.player_pos, [4, 5])
        self.assertTrue(eng.has_moved)
        self.assertEqual(eng.turn_stage, STAGE_PLAYER_MOVED)

        # Undo!
        reverted = eng.restore_snapshot()
        self.assertTrue(reverted)
        self.assertEqual(eng.player_pos, [3, 5])
        self.assertFalse(eng.has_moved)
        self.assertEqual(eng.turn_stage, STAGE_PLANNING)

        # Can now move in a different direction (e.g. Left)
        moved_left = eng.take_player_move(-1, 0)
        self.assertTrue(moved_left)
        self.assertEqual(eng.player_pos, [2, 5])

    def test_all_8_levels_loaded(self):
        """Verify all 8 levels are valid."""
        self.assertEqual(len(LEVELS), 8)
        for i in range(8):
            eng = TitanEngine(current_level=i)
            self.assertEqual(eng.state, STATE_PLAYING)
            self.assertGreater(len(eng.enemies), 0)
            self.assertEqual(eng.player_hp, 2)

if __name__ == "__main__":
    unittest.main()
