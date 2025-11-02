"""
This file defines the basic types (enums) for our game.

An enum is like a list of labels - instead of using strings like "BRICK" 
which could have typos, we create special constants that Python checks for us.

WHAT YOU NEED TO DO:
1. Resource enum - Already done! ✅
2. Fill in the PortKind enum with:
   - GENERIC_3_FOR_1 (any resource, 3:1 trade rate)
   - SPECIFIC_2_FOR_1 (one specific resource, 2:1 trade rate)

HINT: Use `auto()` to automatically assign numbers to each type.
"""

from enum import Enum, auto


class Resource(Enum):
    """
    Types of resources in the game.
    Each player collects these to build roads, settlements, and cities.
    """
    
    BRICK = auto()
    LUMBER = auto()
    ORE = auto()
    GRAIN = auto()
    WOOL = auto()
    DESERT = auto()

class PortKind(Enum):
    """
    Types of ports (harbors) on the board.
    Players who own settlements next to ports get better trade rates.
    """
    GENERIC_3_FOR_1 = auto()      # Any resource, 3:1 trade rate
    SPECIFIC_2_FOR_1 = auto()      # One specific resource, 2:1 trade rate

