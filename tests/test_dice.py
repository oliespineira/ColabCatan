import unittest
from engine.dice import Dice

class TestDice(unittest.TestCase):
    def test_roll_range(self):
        dice = Dice()
        for _ in range(100):
            d1, d2, total = dice.roll()
            self.assertTrue(1 <= d1 <= 6)
            self.assertTrue(1 <= d2 <= 6)
            self.assertTrue(2 <= total <= 12)

if __name__ == '__main__':
    unittest.main()