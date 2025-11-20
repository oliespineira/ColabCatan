"""
This file contains the board structure - the physical pieces of the game.

WHAT WE'RE BUILDING:
1. HexTile - A single hexagon tile on the board (like a piece of land)
2. Vertex - A corner where 3 hexes meet (where you can build settlements/cities)
3. Edge - A line connecting two vertices (where you can build roads)
4. Port - A harbor on the coast (for better trading)
5. BoardGraph - The entire board that holds everything together

WHAT YOU NEED TO DO:

1. Fill in the HexTile class:
   - It needs: id (a unique number), resource (Resource type), number (the dice number, or None for desert)

2. Fill in the Vertex class:
   - It needs: id (unique number), edge_ids (list of edges connected to this vertex), 
     hex_ids (list of hexes touching this vertex - up to 3), owner (player ID who owns it, or None),
     is_city (True if it's a city, False if it's just a settlement)

3. Fill in the Edge class:
   - It needs: id (unique number), v1 and v2 (the two vertex IDs it connects),
     owner (player ID who owns the road, or None)

4. Fill in the Port class:
   - It needs: id (unique number), vertex_ids (tuple of 2 vertices that touch this port),
     kind (PortKind enum), resource (the specific resource for 2:1 ports, or None)

5. Fill in the BoardGraph class:
   - It needs: vertices (dictionary: vertex_id -> Vertex), edges (dictionary: edge_id -> Edge),
     hexes (dictionary: hex_id -> HexTile), ports (dictionary: port_id -> Port),
     num_to_hexes (dictionary: dice_number -> set of hex IDs),
     vertex_to_hexes (dictionary: vertex_id -> list of hex IDs)

   Also add these helper methods:
   - edges_of(v) - returns list of edge IDs connected to vertex v
   - other_end(e, v) - given edge e and one vertex v, return the other vertex
   - neighbors(v) - returns list of neighbor vertex IDs
   - pip(number) - static method that returns the pip count for a dice number (2 and 12 = 1 pip, etc.)
   - vertex_pip(v) - returns total pip score for a vertex (sum of pips from adjacent hexes)
   - player_has_port(player_id, port) - checks if player owns a settlement/city at either vertex of the port
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .enums import Resource, PortKind
#This is a python dict that maps the node name with the adjacent node names
catan_graph: dict[str, list[str]] = {
    "A": ["D", "E"],
    "B": ["E", "F"],
    "C": ["F", "G"],
    "D": ["A", "H"],
    "E": ["A", "J", "B"],
    "F": ["C", "B", "L"],
    "G": ["N", "C"],
    "H": ["D", "O", "I"],
    "I": ["H", "T", "J"],
    "J": ["E", "I", "K"],
    "K": ["J", "L", "V"],
    "L": ["F", "K", "M"],
    "M": ["L", "N", "X"],
    "N": ["G", "M", "P"],
    "O": ["H", "R"],
    "P": ["N", "Z"],
    "Q": ["R", "B2"],
    "R": ["Q", "S", "O"],
    "S": ["R", "D2", "T"],
    "T": ["I", "S", "U"],
    "U": ["T", "F2", "V"],
    "V": ["K", "U", "W"],
    "W": ["V", "X", "H2"],
    "X": ["M", "W", "Y"],
    "Y": ["Z", "J2", "X"],
    "Z": ["P", "Y", "A2"],
    "A2": ["Z", "L2"],
    "B2": ["Q", "C2"],
    "C2": ["B2", "V2", "D2"],
    "D2": ["S", "C2", "E2"],
    "E2": ["D2", "N2", "F2"],
    "F2": ["U", "E2", "G2"],
    "G2": ["F2", "P2", "H2"],
    "H2": ["W", "G2", "I2"],
    "I2": ["H2", "R2", "J2"],
    "J2": ["I2", "Y", "K2"],
    "K2": ["J2", "T2", "L2"],
    "L2": ["A2", "K2"],
    "V2": ["C2", "M2"],
    "M2": ["V2", "U2", "N2"],
    "N2": ["M2", "E2", "O2"],
    "O2": ["N2", "X2", "P2"],
    "P2": ["O2", "G2", "Q2"],
    "Q2": ["P2", "Z2", "R2"],
    "R2": ["Q2", "I2", "S2"],
    "S2": ["R2", "B3", "T2"],
    "T2": ["K2", "S2"],
    "U2": ["M2", "W2"],
    "W2": ["U2", "X2"],
    "X2": ["W2", "O2", "Y2"],
    "Y2": ["X2", "Z2"],
    "Z2": ["Y2", "Q2", "A3"],
    "A3": ["Z2", "B3"],
    "B3": ["A3", "S2"],
}

#This lists the types of terrains possible in the game
RESOURCE_POOL = [
    "forest",
    "forest",
    "forest",
    "forest",
    "pasture",
    "pasture",
    "pasture",
    "pasture",
    "field",
    "field",
    "field",
    "field",
    "hill",
    "hill",
    "hill",
    "mountain",
    "mountain",
    "mountain",
    "desert",
]
#This represents the dice number tokes used on the non-desert hexes. Each time the dice rolls the number, the resource is gained.
CHITS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

#Possible colours to use
RESOURCE_COLOURS = {
    "forest": "#4caf50",
    "pasture": "#8bc34a",
    "field": "#ffd54f",
    "hill": "#ff8a65",
    "mountain": "#b0bec5",
    "desert": "#ffe0b2",
}


@dataclass(frozen=True)
class HexTile:
    """
    A single hexagon tile on the board.
    Each tile produces a specific resource when the dice roll matches its number.
    """
    vertices: tuple[str, ...] #the intersections surrounding the hex
    centroid: tuple[float, float] #center coordinate od the hex
    area: float#useful for drawing. maybe one of us needs it for the UI
    resources: str| None = None # here we assign the resource to the specific hex
    radius: float =0.0 #useful for rendering
    orientation: float =0.0 #used for ui
    hex_points: tuple[tuple[float, float], ...] | None #coordinates. Useful for drawing



@dataclass(frozen=True)
class Port:
    """
    A harbor on the coast.
    Players with settlements next to ports get better trade rates.
    """
    # TODO: Fill in these fields
    # id: int
    # vertex_ids: Tuple[int, int]  # the 2 vertices that touch this port
    # kind: PortKind
    # resource: Optional[Resource] = None  # for 2:1 ports, which resource
    pass


@dataclass
class BoardGraph:
    """
    The complete board - holds all hexes, vertices, edges, and ports.
    Also includes helpful indexes for fast lookups.
    """
    # TODO: Fill in these fields
    # vertices: Dict[int, Vertex] = field(default_factory=dict)
    # edges: Dict[int, Edge] = field(default_factory=dict)
    # hexes: Dict[int, HexTile] = field(default_factory=dict)
    # ports: Dict[int, Port] = field(default_factory=dict)
    # num_to_hexes: Dict[int, Set[int]] = field(default_factory=lambda: defaultdict(set))
    # vertex_to_hexes: Dict[int, List[int]] = field(default_factory=dict)
    pass

    # TODO: Add helper methods here
    # def edges_of(self, v: int) -> List[int]:
    #     """Returns list of edge IDs connected to vertex v."""
    #     pass
    #
    # def other_end(self, e: int, v: int) -> int:
    #     """Given edge e and vertex v, return the other vertex."""
    #     pass
    #
    # def neighbors(self, v: int) -> List[int]:
    #     """Returns list of neighbor vertex IDs (vertices connected by edges)."""
    #     pass
    #
    # @staticmethod
    # def pip(number: Optional[int]) -> int:
    #     """Returns pip count for a dice number. 2 and 12 = 1 pip, 3 and 11 = 2 pips, etc."""
    #     pass
    #
    # def vertex_pip(self, v: int) -> int:
    #     """Returns total pip score for vertex (sum of pips from adjacent hexes)."""
    #     pass
    #
    # def player_has_port(self, player_id: int, port: Port) -> bool:
    #     """Checks if player owns a settlement/city at either vertex of the port."""
    #     pass

