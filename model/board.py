"""
This is the Settlers of Catan board implementation. Essential for everyone in the group to know what is happening here.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .enums import Resource, PortKind


#This is a python dict that maps the node name with the adjacent node names. In other words, it represents the vertex adjacency list for the board.
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

#these are the different hexagons, each one has a 6 corners (nodes in the graph)
HEX_LAYOUT={
    0: ("D", "A", "E", "J", "H", "I"),   
    1: ("E", "B", "F", "L", "K", "J"),  
    2: ("F", "C", "G", "N", "M", "L"),   
    3: ("O", "H", "I", "T", "S", "R"),  
    4: ("I", "J", "K", "V", "U", "T"),  
    5: ("K", "L", "M", "X", "W", "V"),     
    6: ("M", "N", "P", "Z", "Y", "X"), 
    7: ("Q", "R", "S", "D2", "C2", "B2"),    
    8: ("S", "T", "U", "F2", "E2", "D2"),    
    9: ("U", "V", "W", "H2", "G2", "F2"),   
    10: ("W", "X", "Y", "J2", "I2", "H2"),  
    11: ("Y", "Z", "A2", "L2", "K2", "J2"),
    12: ("C2", "D2", "E2", "N2", "M2", "V2"),
    13: ("E2", "F2", "G2", "P2", "O2", "N2"),
    14: ("G2", "H2", "I2", "R2", "Q2", "P2"),
    15: ("I2", "J2", "K2", "T2", "S2", "R2"),
    16: ("M2", "N2", "O2", "X2", "W2", "U2"),
    17: ("O2", "P2", "Q2", "Z2", "Y2", "X2"),
    18: ("Q2", "R2", "S2", "B3", "A3", "Z2"),


}

#This lists the types of terrains possible in the game. Each type of terrain produce their corresponfing resource
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
    The number attribute relates to the dice number token (there is none for the desert)
    """
    id: int
    resource: Optional[Resource] # none for desert
    number: Optional[int]#chit number, none for desert
# how to use: HexTile(id=0, resource=Resource.HILL, number=8)

@dataclass
class Vertex:
    """This is the corner where up to 3 hexes meet"""
    id: str
    edge_ids: list[int] = field(default_factory=list) #list of edge IDs connected to the specific vertex
    hex_ids: list[int] = field(default_factory=list) #list of hexes touching vertex, up to 3
    owner: Optional[int] = None  #player who has a settlement or city there
    is_city: bool = False# false meaning settlement and true meaning City

@dataclass
class Edge:
    """
    Edge connecting two vertices (for roads).
    """
    id: int
    v1: str #first vertex endpoint
    v2: str#second vertex endpoint
    owner: Optional[int] = None  # player id who owns the road
@dataclass
class BoardGraph:
    """
    The complete board - holds all hexes, vertices, edges, and ports.
    Also includes helpful indexes for fast lookups.
    """
    vertices: Dict[str, Vertex]= field(default_factory= dict)
    edges: Dict[int, Edge] = field(default_factory=dict)           # edge_id -> Edge
    hexes: Dict[int, HexTile] = field(default_factory=dict)        # hex_id -> HexTile
    num_to_hexes: Dict[int, Set[int]] = field(default_factory=lambda: defaultdict(set))
    vertex_to_hexes: Dict[str, List[int]] = field(default_factory=dict)


    def __post_init__(self):
        # Build num_to_hexes from hexes
        for hid, h in self.hexes.items():
            if h.number is not None:
                self.num_to_hexes[h.number].add(hid)

        # Build vertex_to_hexes from vertices. 
        for vid, v in self.vertices.items():
            self.vertex_to_hexes[vid] = list(v.hex_ids)

        # Ensure edge back-references exist on vertices
        for eid, e in self.edges.items():
            if e.v1 in self.vertices and eid not in self.vertices[e.v1].edge_ids:
                self.vertices[e.v1].edge_ids.append(eid)
            if e.v2 in self.vertices and eid not in self.vertices[e.v2].edge_ids:
                self.vertices[e.v2].edge_ids.append(eid)

    # SOME HELPER METHODS

    def edges_of(self, v: str) -> List[int]:
        """Returns list of edge IDs connected to vertex v."""
        return list(self.vertices[v].edge_ids)

    def other_end(self, e: int, v: str) -> str:
        """Given edge e and one vertex v, return the other vertex."""
        edge = self.edges[e]
        if v == edge.v1:
            return edge.v2
        if v == edge.v2:
            return edge.v1
        raise ValueError(f"Vertex {v} is not an endpoint of edge {e}")

    def neighbors(self, v: str) -> List[str]:
        """Returns list of neighbor vertex IDs (vertices connected by edges)."""
        return [self.other_end(eid, v) for eid in self.edges_of(v)]
    

def build_catan_board(resource_assignment: List[Resource], 
                       chit_assignment: List[int]) -> BoardGraph:
    """
    Builds the complete Catan board from the graph structure.
    """
    board = BoardGraph()
    
    # Create all vertices
    for vertex_id in catan_graph.keys():
        board.vertices[vertex_id] = Vertex(id=vertex_id)
    
    # Create edges from adjacency list
    edge_id = 0
    seen_edges = set()
    for v1, neighbors in catan_graph.items():
        for v2 in neighbors:
            edge_key = tuple(sorted([v1, v2]))
            if edge_key not in seen_edges:
                board.edges[edge_id] = Edge(id=edge_id, v1=v1, v2=v2)
                edge_id += 1
                seen_edges.add(edge_key)
    
    # Create hexes and link to vertices
    for hex_id, vertices in HEX_LAYOUT.items():
        board.hexes[hex_id] = HexTile(
            id=hex_id,
            resource=resource_assignment[hex_id],
            number=chit_assignment[hex_id]
        )
        # Link vertices to this hex
        for v_id in vertices:
            board.vertices[v_id].hex_ids.append(hex_id)
    
    return board

def create_standard_board() -> BoardGraph:
    """Creates a standard Catan board with shuffled resources and chits."""
    import random
    
    resources = RESOURCE_POOL.copy()
    random.shuffle(resources)
    
    chits = CHITS.copy()
    random.shuffle(chits)
    
    # Find desert and assign None chit
    resource_assignment = [Resource.from_string(r) for r in resources]
    chit_assignment = []
    chit_idx = 0
    
    for i in range(19):
        if resources[i] == "desert":
            chit_assignment.append(None)
        else:
            chit_assignment.append(chits[chit_idx])
            chit_idx += 1
    
    return build_catan_board(resource_assignment, chit_assignment)