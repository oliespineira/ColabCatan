"""
Building rules for roads and settlements during the main game.
This module validates whether a player can build roads and settlements according to Catan rules.

RULES FOR ROADS:
- Road must connect to an existing road or settlement/city owned by the player
- Edge must be empty (no existing road)
- Player must have enough resources (1 Lumber + 1 Brick)

RULES FOR SETTLEMENTS:
- Vertex must be empty
- No settlement/city within 2 edges (distance rule)
- Must be connected by a road owned by the player
- Player must have enough resources (1 Lumber + 1 Brick + 1 Grain + 1 Wool)

RULES FOR CITIES:
- Vertex must have a settlement owned by the player
- Player must have enough resources (2 Grain + 3 Ore)
"""

from typing import Tuple, Optional
from ..model.board import BoardGraph, Vertex, Edge
from ..model.game import GameState, Player
from ..model.enums import Resource


class BuildingRules:
    """Validates building rules for roads, settlements, and cities."""
    
    def __init__(self, game_state: GameState):
        self.game = game_state
        self.board = game_state.board
    
    def can_build_road(self, player_id: int, edge_id: int) -> Tuple[bool, str]:
        """
        Check if a player can build a road on the given edge.
        
        Args:
            player_id: ID of the player attempting to build
            edge_id: ID of the edge where road should be built
            
        Returns:
            Tuple of (can_build: bool, reason: str)
        """
        # Check if edge exists
        edge = self.board.edges.get(edge_id)
        if not edge:
            return False, "Invalid edge ID"
        
        # Check if edge is already occupied
        if edge.owner is not None:
            return False, "Edge already has a road"
        
        # Check if player has enough resources
        player = self.game.players[player_id]
        road_cost = {Resource.LUMBER: 1, Resource.BRICK: 1}
        if not player.has_resources(road_cost):
            return False, "Insufficient resources (need 1 Lumber + 1 Brick)"
        
        # Check if player has roads remaining
        if player.roads_remaining <= 0:
            return False, "No roads remaining"
        
        # Check connectivity: road must connect to existing road or settlement/city
        v1_connected = self._is_vertex_connected_to_player(player_id, edge.v1)
        v2_connected = self._is_vertex_connected_to_player(player_id, edge.v2)
        
        if not (v1_connected or v2_connected):
            return False, "Road must connect to your existing road or settlement/city"
        
        return True, "Valid road placement"
    
    def can_build_settlement(self, player_id: int, vertex_id: str) -> Tuple[bool, str]:
        """
        Check if a player can build a settlement on the given vertex.
        
        Args:
            player_id: ID of the player attempting to build
            vertex_id: ID of the vertex where settlement should be built
            
        Returns:
            Tuple of (can_build: bool, reason: str)
        """
        # Check if vertex exists
        vertex = self.board.vertices.get(vertex_id)
        if not vertex:
            return False, "Invalid vertex ID"
        
        # Check if vertex is already occupied
        if vertex.owner is not None:
            return False, "Vertex already occupied"
        
        # Check distance rule: no settlement within 2 edges
        if not self._check_distance_rule(vertex_id):
            return False, "Too close to another settlement (distance rule violation)"
        
        # Check if player has enough resources
        player = self.game.players[player_id]
        settlement_cost = {
            Resource.LUMBER: 1,
            Resource.BRICK: 1,
            Resource.GRAIN: 1,
            Resource.WOOL: 1
        }
        if not player.has_resources(settlement_cost):
            return False, "Insufficient resources (need 1 Lumber + 1 Brick + 1 Grain + 1 Wool)"
        
        # Check if player has settlements remaining
        if player.settlements_remaining <= 0:
            return False, "No settlements remaining"
        
        # Check connectivity: must be connected by a road owned by the player
        if not self._is_vertex_connected_by_road(player_id, vertex_id):
            return False, "Settlement must be connected by your road"
        
        return True, "Valid settlement placement"
    
    def can_upgrade_to_city(self, player_id: int, vertex_id: str) -> Tuple[bool, str]:
        """
        Check if a player can upgrade a settlement to a city.
        
        Args:
            player_id: ID of the player attempting to upgrade
            vertex_id: ID of the vertex with the settlement
            
        Returns:
            Tuple of (can_build: bool, reason: str)
        """
        # Check if vertex exists
        vertex = self.board.vertices.get(vertex_id)
        if not vertex:
            return False, "Invalid vertex ID"
        
        # Check if vertex is owned by the player
        if vertex.owner != player_id:
            return False, "You don't own a settlement at this vertex"
        
        # Check if it's already a city
        if vertex.is_city:
            return False, "Already a city"
        
        # Check if player has enough resources
        player = self.game.players[player_id]
        city_cost = {Resource.GRAIN: 2, Resource.ORE: 3}
        if not player.has_resources(city_cost):
            return False, "Insufficient resources (need 2 Grain + 3 Ore)"
        
        # Check if player has cities remaining
        if player.cities_remaining <= 0:
            return False, "No cities remaining"
        
        return True, "Valid city upgrade"
    
    def _is_vertex_connected_to_player(self, player_id: int, vertex_id: str) -> bool:
        """
        Check if a vertex is connected to the player's network.
        A vertex is connected if:
        - It has a settlement/city owned by the player, OR
        - It's connected by a road owned by the player to such a vertex
        """
        vertex = self.board.vertices.get(vertex_id)
        if not vertex:
            return False
        
        # Check if player owns settlement/city at this vertex
        if vertex.owner == player_id:
            return True
        
        # Check if any adjacent edge is owned by the player
        for edge_id in vertex.edge_ids:
            edge = self.board.edges.get(edge_id)
            if edge and edge.owner == player_id:
                # Check if the other end has a settlement/city
                other_vertex_id = self.board.other_end(edge_id, vertex_id)
                other_vertex = self.board.vertices.get(other_vertex_id)
                if other_vertex and other_vertex.owner == player_id:
                    return True
        
        return False
    
    def _is_vertex_connected_by_road(self, player_id: int, vertex_id: str) -> bool:
        """
        Check if a vertex is connected by at least one road owned by the player.
        """
        vertex = self.board.vertices.get(vertex_id)
        if not vertex:
            return False
        
        # Check if any adjacent edge is owned by the player
        for edge_id in vertex.edge_ids:
            edge = self.board.edges.get(edge_id)
            if edge and edge.owner == player_id:
                return True
        
        return False
    
    def _check_distance_rule(self, vertex_id: str) -> bool:
        """
        Check the distance rule: no settlement/city within 2 edges.
        This means no adjacent vertex can have a settlement/city.
        """
        vertex = self.board.vertices.get(vertex_id)
        if not vertex:
            return False
        
        # Check all adjacent vertices (1 edge away)
        for neighbor_id in self.board.neighbors(vertex_id):
            neighbor = self.board.vertices.get(neighbor_id)
            if neighbor and neighbor.owner is not None:
                return False
        
        return True

