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


@dataclass(frozen=True)
class HexTile:
    """
    A single hexagon tile on the board.
    Each tile produces a specific resource when the dice roll matches its number.
    """
    # TODO: Fill in these fields
    # id: int
    # resource: Resource
    # number: Optional[int]  # None for desert, otherwise 2-12


@dataclass
class Vertex:
    """
    A corner where up to 3 hexes meet.
    Players can build settlements (1 VP) or cities (2 VP) here.
    """
    # TODO: Fill in these fields
    # id: int
    # edge_ids: List[int] = field(default_factory=list)
    # hex_ids: List[int] = field(default_factory=list)
    # owner: Optional[int] = None  # player ID
    # is_city: bool = False
    pass


@dataclass
class Edge:
    """
    A line connecting two vertices.
    Players can build roads here.
    """
    # TODO: Fill in these fields
    # id: int
    # v1: int
    # v2: int
    # owner: Optional[int] = None  # player ID
    pass


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

