"""
Pathfinding algorithms for CPU players.

Algorithms referenced:
- Dijkstra's algorithm with a binary heap priority queue (`O(E log V)`)
- Breadth-first search for connectivity queries (`O(V + E)`)

Method time complexities:
- `shortest_path_to_resource`: `O(H * V + E log V)` combines resource scanning
  with Dijkstra.
- `shortest_path_to_vertex`: `O(E log V)` pure Dijkstra run.
- `_dijkstra_shortest_path`: `O(E log V)` explores each edge at most once.
- `_find_vertices_with_resource`: `O(H * V)` since it scans every vertex per
  resource hex (small constant in practice).
- `get_player_connected_vertices`: `O(V + E)` BFS on owned roads.
- `find_best_road_placement`: `O(E log V + H * V)` delegates to resource lookup
  plus shortest path logic.
- `_find_any_valid_road`: `O(E)` bounded by traversing adjacent edges from the
  player's frontier.
"""

from typing import Dict, List, Tuple, Optional, Set
from collections import deque
import heapq
from ..model.board import BoardGraph, Vertex, Edge
from ..model.enums import Resource


class Pathfinding:
    """Pathfinding algorithms for road building decisions."""
    
    def __init__(self, board: BoardGraph):
        self.board = board
    
    def shortest_path_to_resource(
        self, 
        start_vertices: List[str], 
        target_resource: Resource,
        player_id: int
    ) -> Optional[Tuple[List[int], int]]:
        """
        Find the shortest path from any starting vertex to the nearest vertex
        adjacent to a hex that produces the target resource.
        
        Uses Dijkstra's algorithm with edge weights of 1.
        
        Time Complexity: O(H * V + E log V)
        - Resource scanning: O(H * V)
        - Dijkstra: O(E log V)
        
        Args:
            start_vertices: List of vertex IDs where the player can start building
            target_resource: The resource type to find
            player_id: ID of the player (to check existing roads)
            
        Returns:
            Tuple of (path_edges: List[int], distance: int) or None if no path exists
            path_edges is the list of edge IDs to build
        """
        # Find all target vertices (adjacent to hexes with target resource)
        target_vertices = self._find_vertices_with_resource(target_resource)
        
        if not target_vertices:
            return None
        
        # Use Dijkstra's algorithm to find shortest path
        return self._dijkstra_shortest_path(start_vertices, target_vertices, player_id)
    
    def shortest_path_to_vertex(
        self,
        start_vertices: List[str],
        target_vertex: str,
        player_id: int
    ) -> Optional[Tuple[List[int], int]]:
        """
        Find the shortest path from any starting vertex to a target vertex.
        
        Time Complexity: O(E log V) - pure Dijkstra run
        
        Args:
            start_vertices: List of vertex IDs where the player can start building
            target_vertex: The target vertex ID
            player_id: ID of the player (to check existing roads)
            
        Returns:
            Tuple of (path_edges: List[int], distance: int) or None if no path exists
        """
        return self._dijkstra_shortest_path(start_vertices, [target_vertex], player_id)
    
    def _dijkstra_shortest_path(
        self,
        start_vertices: List[str],
        target_vertices: List[str],
        player_id: int
    ) -> Optional[Tuple[List[int], int]]:
        """
        Dijkstra's algorithm to find shortest path from any start to any target.
        
        Time Complexity: O(E log V) average and worst case
        - Uses binary heap (heapq) as priority queue
        - Each edge explored at most once: O(E)
        - Heap operations: O(log V) per edge
        - Space: O(V) for visited set and priority queue
        
        Returns:
            Tuple of (path_edges: List[int], distance: int) or None
        """
        # Priority queue: (distance, current_vertex, path_edges)
        pq = []
        visited = set()
        target_set = set(target_vertices)
        
        # Initialize with all start vertices
        for start_vertex in start_vertices:
            heapq.heappush(pq, (0, start_vertex, []))
        
        while pq:
            distance, current_vertex, path_edges = heapq.heappop(pq)
            
            if current_vertex in visited:
                continue
            
            visited.add(current_vertex)
            
            # Check if we reached a target
            if current_vertex in target_set:
                return (path_edges, distance)
            
            # Explore neighbors
            for edge_id in self.board.vertices[current_vertex].edge_ids:
                edge = self.board.edges[edge_id]
                other_vertex = self.board.other_end(edge_id, current_vertex)
                
                if other_vertex in visited:
                    continue
                
                # If edge is already owned by player, no cost
                # Otherwise, we need to build it (cost = 1)
                if edge.owner == player_id:
                    new_distance = distance
                    new_path = path_edges.copy()
                else:
                    # Check if edge is available (not owned by anyone)
                    if edge.owner is not None:
                        continue  # Can't build through opponent's road
                    new_distance = distance + 1
                    new_path = path_edges + [edge_id]
                
                heapq.heappush(pq, (new_distance, other_vertex, new_path))
        
        return None  # No path found
    
    def _find_vertices_with_resource(self, resource: Resource) -> List[str]:
        """
        Find all vertices that are adjacent to at least one hex producing the given resource.
        
        Time Complexity: O(H * V) average and worst case
        - H = number of hexes (19 in Catan)
        - V = number of vertices (54 in Catan)
        - Scans all vertices for each resource hex
        
        Returns:
            List of vertex IDs
        """
        target_vertices = []
        
        # Find all hexes with the target resource
        resource_hexes = [
            hex_id for hex_id, hex_tile in self.board.hexes.items()
            if hex_tile.resource == resource
        ]
        
        # Find all vertices adjacent to these hexes
        for hex_id in resource_hexes:
            # Get vertices from HEX_LAYOUT (we need to import it or reconstruct)
            # For now, check all vertices
            for vertex_id, vertex in self.board.vertices.items():
                if hex_id in vertex.hex_ids:
                    if vertex_id not in target_vertices:
                        target_vertices.append(vertex_id)
        
        return target_vertices
    
    def get_player_connected_vertices(self, player_id: int) -> List[str]:
        """
        Get all vertices that are connected to the player's road network.
        This includes vertices with settlements/cities and vertices reachable by roads.
        
        Algorithm: Breadth-First Search (BFS)
        Time Complexity: O(V + E) average and worst case
        - V = vertices, E = edges
        - Uses deque for queue operations
        - Space: O(V) for visited set and queue
        
        Returns:
            List of vertex IDs
        """
        connected = set()
        queue = deque()
        
        # Start with vertices that have settlements/cities
        for vertex_id, vertex in self.board.vertices.items():
            if vertex.owner == player_id:
                connected.add(vertex_id)
                queue.append(vertex_id)
        
        # BFS to find all reachable vertices via roads
        while queue:
            current_vertex = queue.popleft()
            
            for edge_id in self.board.vertices[current_vertex].edge_ids:
                edge = self.board.edges[edge_id]
                
                # Only traverse edges owned by the player
                if edge.owner != player_id:
                    continue
                
                other_vertex = self.board.other_end(edge_id, current_vertex)
                if other_vertex not in connected:
                    connected.add(other_vertex)
                    queue.append(other_vertex)
        
        return list(connected)
    
    def find_best_road_placement(
        self,
        player_id: int,
        target_resource: Optional[Resource] = None,
        target_vertex: Optional[str] = None
    ) -> Optional[int]:
        """
        Find the best edge to build a road on for the CPU player.
        
        Args:
            player_id: ID of the CPU player
            target_resource: Optional resource to target
            target_vertex: Optional specific vertex to target
            
        Returns:
            Edge ID to build on, or None if no good placement found
        """
        # Get all vertices the player can build from
        start_vertices = self.get_player_connected_vertices(player_id)
        
        if not start_vertices:
            return None
        
        # Find shortest path
        if target_resource:
            result = self.shortest_path_to_resource(start_vertices, target_resource, player_id)
        elif target_vertex:
            result = self.shortest_path_to_vertex(start_vertices, target_vertex, player_id)
        else:
            # No specific target, find any valid road placement
            return self._find_any_valid_road(player_id, start_vertices)
        
        if result:
            path_edges, _ = result
            # Return the first edge in the path (the one to build next)
            if path_edges:
                return path_edges[0]
        
        return None
    
    def _find_any_valid_road(self, player_id: int, start_vertices: List[str]) -> Optional[int]:
        """
        Find any valid edge to build a road on, starting from connected vertices.
        """
        for vertex_id in start_vertices:
            for edge_id in self.board.vertices[vertex_id].edge_ids:
                edge = self.board.edges[edge_id]
                # Check if edge is available and connects to unvisited area
                if edge.owner is None:
                    other_vertex = self.board.other_end(edge_id, vertex_id)
                    # Prefer edges that lead to unoccupied vertices
                    other_vertex_obj = self.board.vertices[other_vertex]
                    if other_vertex_obj.owner is None:
                        return edge_id
        
        return None

