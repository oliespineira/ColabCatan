"""
Building service for roads and settlements.

Algorithms referenced:
- Rule validation delegates to local adjacency scans (`O(deg(v))`).
- CPU road planning uses Dijkstra (`O(E log V)`) via the `Pathfinding` helper.
- Settlement scoring leverages heuristic evaluation plus cached resource maps
  for near-constant lookups.

Method time complexities:
- `build_road`: `O(1)` beyond delegated rule checks.
- `build_settlement`: `O(1)` beyond delegated rule checks.
- `upgrade_to_city`: `O(1)`.
- `cpu_build_road`: `O(E log V + H * V)` through pathfinding.
- `cpu_build_settlement`: `O(B log B)` for scoring `B` buildable vertices.
- `_find_buildable_vertices`: `O(B * deg)` bounded by connected frontier size.
- `_score_settlement_location`: `O(k)` where `k` is adjacent hex count (≤3).
- `_build_resource_map`: `O(H * V)` preprocessing.
- `get_vertices_with_resource`: `O(T)` where `T` is count cached for resource.
- `find_best_settlement_for_resource`: `O(B log B)` sorting buildable targets.
"""

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from ..model.board import BoardGraph
from ..model.enums import Resource
from ..rules.building_rules import BuildingRules
from ..search.pathfinding import Pathfinding

if TYPE_CHECKING:
    from ..model.game import GameState, Player


class BuildingService:
    """
    Service for building roads, settlements, and cities.
    Handles both player and CPU building logic.
    """
    
    def __init__(self, game_state: 'GameState'):
        self.game = game_state
        self.board = game_state.board
        self.rules = BuildingRules(game_state)
        self.pathfinding = Pathfinding(game_state.board)
        
        # Multidimensional array for quick resource location lookup
        # Structure: resource -> hex_id -> list of vertex_ids
        self._resource_location_map: Dict[Resource, Dict[int, List[str]]] = {}
        self._build_resource_map()
    
    def build_road(self, player_id: int, edge_id: int) -> Tuple[bool, str]:
        """
        Build a road on the specified edge.
        
        Args:
            player_id: ID of the player building the road
            edge_id: ID of the edge to build on
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate placement
        can_build, reason = self.rules.can_build_road(player_id, edge_id)
        if not can_build:
            return False, reason
        
        # Get player and edge
        player = self.game.players[player_id]
        edge = self.board.edges[edge_id]
        
        # Deduct resources
        road_cost = {Resource.LUMBER: 1, Resource.BRICK: 1}
        for resource, amount in road_cost.items():
            player.remove_resource(resource, amount)
        
        # Build the road
        edge.owner = player_id
        player.roads_remaining -= 1
        
        return True, f"Road built successfully on edge {edge_id}"
    
    def build_settlement(self, player_id: int, vertex_id: str) -> Tuple[bool, str]:
        """
        Build a settlement on the specified vertex.
        
        Args:
            player_id: ID of the player building the settlement
            vertex_id: ID of the vertex to build on
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate placement
        can_build, reason = self.rules.can_build_settlement(player_id, vertex_id)
        if not can_build:
            return False, reason
        
        # Get player and vertex
        player = self.game.players[player_id]
        vertex = self.board.vertices[vertex_id]
        
        # Deduct resources
        settlement_cost = {
            Resource.LUMBER: 1,
            Resource.BRICK: 1,
            Resource.GRAIN: 1,
            Resource.WOOL: 1
        }
        for resource, amount in settlement_cost.items():
            player.remove_resource(resource, amount)
        
        # Build the settlement
        vertex.owner = player_id
        vertex.is_city = False
        player.settlements_remaining -= 1
        player.victory_points += 1
        
        return True, f"Settlement built successfully at vertex {vertex_id}"
    
    def upgrade_to_city(self, player_id: int, vertex_id: str) -> Tuple[bool, str]:
        """
        Upgrade a settlement to a city.
        
        Args:
            player_id: ID of the player upgrading
            vertex_id: ID of the vertex with the settlement
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate upgrade
        can_upgrade, reason = self.rules.can_upgrade_to_city(player_id, vertex_id)
        if not can_upgrade:
            return False, reason
        
        # Get player and vertex
        player = self.game.players[player_id]
        vertex = self.board.vertices[vertex_id]
        
        # Deduct resources
        city_cost = {Resource.GRAIN: 2, Resource.ORE: 3}
        for resource, amount in city_cost.items():
            player.remove_resource(resource, amount)
        
        # Upgrade to city
        vertex.is_city = True
        player.settlements_remaining += 1  # Get settlement back
        player.cities_remaining -= 1
        player.victory_points += 1  # City is worth 2 VP, settlement was 1, so +1 more
        
        return True, f"Settlement upgraded to city at vertex {vertex_id}"
    
    # CPU BUILDING METHODS (using shortest path algorithms)
    
    def cpu_build_road(self, player_id: int, target_resource: Optional[Resource] = None) -> Tuple[bool, str]:
        """
        CPU builds a road using shortest path algorithm.
        
        Args:
            player_id: ID of the CPU player
            target_resource: Optional resource to target (if None, builds toward any good location)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Find best road placement using pathfinding
        best_edge = self.pathfinding.find_best_road_placement(player_id, target_resource)
        
        if best_edge is None:
            return False, "No valid road placement found"
        
        return self.build_road(player_id, best_edge)
    
    def cpu_build_settlement(self, player_id: int, preferred_resources: Optional[List[Resource]] = None) -> Tuple[bool, str]:
        """
        CPU builds a settlement at a strategic location.
        Uses multidimensional array to quickly find vertices with desired resources.
        
        Time Complexity: O(B log B) where B = buildable vertices
        - Finding buildable vertices: O(B * deg(v))
        - Scoring: O(B * k) where k = adjacent hexes (≤3)
        - Sorting: O(B log B) using Timsort
        
        Args:
            player_id: ID of the CPU player
            preferred_resources: List of resources to prioritize (if None, finds any valid location)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Get all buildable vertices (connected by road, valid distance rule)
        buildable_vertices = self._find_buildable_vertices(player_id)
        
        if not buildable_vertices:
            return False, "No valid settlement locations found"
        
        # Score vertices based on resources
        scored_vertices = []
        for vertex_id in buildable_vertices:
            score = self._score_settlement_location(vertex_id, preferred_resources)
            scored_vertices.append((score, vertex_id))
        
        # Sort by score (highest first) - O(B log B) using Timsort
        scored_vertices.sort(reverse=True, key=lambda x: x[0])
        
        # Try to build at the best location
        for score, vertex_id in scored_vertices:
            success, message = self.build_settlement(player_id, vertex_id)
            if success:
                return True, f"CPU built settlement at {vertex_id} (score: {score})"
        
        return False, "Could not build settlement at any location"
    
    def _find_buildable_vertices(self, player_id: int) -> List[str]:
        """
        Find all vertices where the player can build a settlement.
        Must be connected by road and satisfy distance rule.
        """
        buildable = []
        
        # Get all vertices connected by roads
        connected_vertices = self.pathfinding.get_player_connected_vertices(player_id)
        
        # Check each connected vertex
        for vertex_id in connected_vertices:
            vertex = self.board.vertices[vertex_id]
            
            # Skip if already occupied
            if vertex.owner is not None:
                continue
            
            # Check distance rule
            if self.rules._check_distance_rule(vertex_id):
                buildable.append(vertex_id)
        
        return buildable
    
    def _score_settlement_location(self, vertex_id: str, preferred_resources: Optional[List[Resource]] = None) -> int:
        """
        Score a settlement location based on adjacent resources.
        Higher score = better location.
        
        Uses the resource location map for fast lookup.
        """
        vertex = self.board.vertices[vertex_id]
        score = 0
        
        # Count resources adjacent to this vertex
        resource_counts: Dict[Resource, int] = {}
        for hex_id in vertex.hex_ids:
            hex_tile = self.board.hexes.get(hex_id)
            if hex_tile and hex_tile.resource and hex_tile.resource != Resource.DESERT:
                resource = hex_tile.resource
                resource_counts[resource] = resource_counts.get(resource, 0) + 1
                
                # Bonus points for preferred resources
                if preferred_resources and resource in preferred_resources:
                    score += 3
                else:
                    score += 1
        
        # Bonus for diversity (having multiple different resources)
        score += len(resource_counts) * 2
        
        return score
    
    def _build_resource_map(self):
        """
        Build a multidimensional array/map for quick resource location lookup.
        Structure: resource -> hex_id -> list of vertex_ids
        
        This allows O(1) lookup of which vertices are adjacent to hexes with a specific resource.
        
        Time Complexity: O(H * V) where H = hexes (19), V = vertices (54)
        - Preprocessing step done once during initialization
        - Space: O(H * V) in worst case, typically much less
        """
        self._resource_location_map = {}
        
        for hex_id, hex_tile in self.board.hexes.items():
            if hex_tile.resource and hex_tile.resource != Resource.DESERT:
                resource = hex_tile.resource
                
                if resource not in self._resource_location_map:
                    self._resource_location_map[resource] = {}
                
                # Find all vertices adjacent to this hex
                for vertex_id, vertex in self.board.vertices.items():
                    if hex_id in vertex.hex_ids:
                        if hex_id not in self._resource_location_map[resource]:
                            self._resource_location_map[resource][hex_id] = []
                        if vertex_id not in self._resource_location_map[resource][hex_id]:
                            self._resource_location_map[resource][hex_id].append(vertex_id)
    
    def get_vertices_with_resource(self, resource: Resource) -> List[str]:
        """
        Quickly get all vertices adjacent to hexes with the given resource.
        Uses the multidimensional array for O(1) lookup.
        
        Time Complexity: O(T) where T = number of target vertices for resource
        - Dictionary lookup: O(1)
        - Iterating cached results: O(T)
        - Space: O(T) for result list
        """
        vertices = []
        if resource in self._resource_location_map:
            for hex_id, vertex_list in self._resource_location_map[resource].items():
                vertices.extend(vertex_list)
        return list(set(vertices))  # Remove duplicates
    
    def find_best_settlement_for_resource(self, player_id: int, resource: Resource) -> Optional[str]:
        """
        Find the best settlement location to access a specific resource.
        Uses the resource location map for efficient lookup.
        """
        # Get all vertices with the target resource
        target_vertices = self.get_vertices_with_resource(resource)
        
        # Filter to only buildable vertices
        buildable = self._find_buildable_vertices(player_id)
        candidate_vertices = [v for v in target_vertices if v in buildable]
        
        if not candidate_vertices:
            return None
        
        # Score and return the best one
        best_vertex = None
        best_score = -1
        
        for vertex_id in candidate_vertices:
            score = self._score_settlement_location(vertex_id, [resource])
            if score > best_score:
                best_score = score
                best_vertex = vertex_id
        
        return best_vertex

