import random

class Dice:
    "This will be our 2 dices with 6 sides each"
    def __init__(self):
        self.last_roll = (0, 0)

    def roll(self):
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
        self.last_roll = (die1, die2, total)
        return self.last_roll
        
    def __repr__(self):
        if self.last_roll:
            die1, die2, total = self.last_roll
            return f"Dice(Die1: {die1}, Die2: {die2}, Total: {total})"
        return "Dice(Not rolled yet)"