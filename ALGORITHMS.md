# Algorithms Used in ColabCatan Project

## 1. Dijkstra's Algorithm
**Location:** `search/pathfinding.py` - `_dijkstra_shortest_path()`

**Purpose:** Find shortest path from starting vertices to target vertices for road building decisions.

**Implementation Details:**
- Uses binary heap (heapq) as priority queue
- Edge weights are 1 (unweighted graph, but tracks path length)
- Explores edges owned by player (cost 0) vs. unowned edges (cost 1)

**Time Complexity:**
- **Average Case:** O(E log V) where E = edges, V = vertices
- **Worst Case:** O(E log V)
- **Space Complexity:** O(V) for visited set and priority queue

**Notes:** Standard Dijkstra with binary heap. In Catan board, V ≈ 54 vertices, E ≈ 72 edges, so this is efficient.

---

## 2. Breadth-First Search (BFS)
**Location:** `search/pathfinding.py` - `get_player_connected_vertices()`

**Purpose:** Find all vertices connected to player's road network (for determining where player can build).

**Implementation Details:**
- Uses `deque` for queue
- Starts from vertices with settlements/cities
- Traverses only edges owned by player

**Time Complexity:**
- **Average Case:** O(V + E) where V = vertices, E = edges
- **Worst Case:** O(V + E)
- **Space Complexity:** O(V) for visited set and queue

**Notes:** Standard BFS. In practice, only explores player's subgraph, so often much faster.

---

## 3. Priority Queue / Heap Sort
**Location:** 
- `engine/cpu_player.py` - `choose_action()` (max-heap via min-heap with negated scores)
- `search/pathfinding.py` - `_dijkstra_shortest_path()` (min-heap for Dijkstra)

**Purpose:** 
- CPU player: Select best-scoring action from candidate actions
- Pathfinding: Maintain priority queue for Dijkstra

**Implementation Details:**
- Uses Python's `heapq` module (binary heap)
- CPU player negates scores to simulate max-heap behavior

**Time Complexity:**
- **Average Case:** O(n log n) for building heap, O(log n) per insert/extract
- **Worst Case:** O(n log n) for building heap, O(log n) per insert/extract
- **Space Complexity:** O(n)

**Notes:** 
- CPU player: O(A log A) where A = number of candidate actions
- Pathfinding: O(E log V) for Dijkstra operations

---

## 4. Sorting Algorithms
**Location:**
- `model/game.py` - `determine_turn_order()` (sorting players by dice roll)
- `services/building_service.py` - `cpu_build_settlement()` (sorting vertices by score)

**Purpose:**
- Determine turn order after dice rolls
- Rank settlement locations by strategic value

**Implementation Details:**
- Uses Python's built-in `list.sort()` (Timsort algorithm)

**Time Complexity:**
- **Average Case:** O(n log n) - Timsort is adaptive and efficient
- **Worst Case:** O(n log n) - Timsort worst case
- **Space Complexity:** O(n) for temporary storage

**Notes:** 
- Turn order: O(P log P) where P = number of players (typically 3-4)
- Settlement scoring: O(B log B) where B = buildable vertices

---

## 5. Counter / Multiset Operations
**Location:** `engine/turn_engine.py` - `PlayerView`, `distribute_resources()`

**Purpose:** Track and manipulate player resources efficiently.

**Implementation Details:**
- Uses Python's `collections.Counter` (hash-based multiset)
- Operations: add, remove, count, sum

**Time Complexity:**
- **Average Case:** O(1) for add/remove/lookup, O(k) for iteration where k = unique resources
- **Worst Case:** O(k) where k = number of unique resource types (typically 5)
- **Space Complexity:** O(k)

**Notes:** Counter operations are effectively O(1) for small resource sets (5 types).

---

## 6. DefaultDict Operations
**Location:** 
- `engine/turn_engine.py` - `distribute_resources()`
- `model/board.py` - `num_to_hexes` mapping

**Purpose:** Efficient dictionary operations with automatic default values.

**Implementation Details:**
- Uses Python's `collections.defaultdict`
- Avoids key existence checks

**Time Complexity:**
- **Average Case:** O(1) for insert/lookup
- **Worst Case:** O(1) amortized, O(n) worst case if hash collisions occur
- **Space Complexity:** O(n) where n = number of entries

---

## 7. Random Selection / Sampling
**Location:**
- `engine/turn_engine.py` - `remove_random_cards()`, `default_choose_victim()`, `default_choose_steal_resource()`
- `engine/dice.py` - `roll()`
- `model/game.py` - `_roll_dice()`, `determine_turn_order()` (tie resolution)

**Purpose:**
- Random card discarding
- Random victim selection for robber
- Dice rolling
- Tie-breaking in turn order

**Implementation Details:**
- Uses Python's `random.choice()`, `random.randint()`
- Creates weighted pools for random selection

**Time Complexity:**
- **Average Case:** O(1) for single random choice, O(n) for building weighted pool
- **Worst Case:** O(1) for single random choice, O(n) for building weighted pool
- **Space Complexity:** O(n) for weighted pool creation

**Notes:** 
- `remove_random_cards()`: O(n) where n = number of cards to remove (creates pool each time)
- Dice rolling: O(1)

---

## 8. Graph Traversal (Adjacency Checks)
**Location:**
- `rules/building_rules.py` - `_is_vertex_connected_to_player()`, `_check_distance_rule()`
- `model/board.py` - `neighbors()`, `edges_of()`
- `services/building_service.py` - `_find_buildable_vertices()`

**Purpose:**
- Check vertex connectivity
- Validate distance rule (no settlements within 2 edges)
- Find adjacent vertices/edges

**Implementation Details:**
- Iterates through vertex edge lists
- Checks neighbor vertices

**Time Complexity:**
- **Average Case:** O(deg(v)) where deg(v) = vertex degree (typically 2-3 in Catan)
- **Worst Case:** O(deg(v)) - bounded by maximum vertex degree
- **Space Complexity:** O(1) for single checks, O(V) for full traversal

**Notes:** Vertex degrees in Catan are small (2-3), so these are effectively O(1) in practice.

---

## 9. Resource Location Mapping / Multidimensional Array
**Location:** `services/building_service.py` - `_build_resource_map()`, `get_vertices_with_resource()`

**Purpose:** Fast lookup of vertices adjacent to hexes with specific resources.

**Implementation Details:**
- Pre-computed map: `resource -> hex_id -> list of vertex_ids`
- Built once during initialization
- Used for O(1) lookups

**Time Complexity:**
- **Build Time (Average):** O(H × V) where H = hexes (19), V = vertices (54)
- **Build Time (Worst):** O(H × V)
- **Lookup Time:** O(T) where T = number of target vertices (typically small)
- **Space Complexity:** O(H × V) in worst case, but typically much less

**Notes:** Preprocessing step, so lookup is fast during gameplay.

---

## 10. Recursive Tie Resolution
**Location:** `model/game.py` - `determine_turn_order()`

**Purpose:** Resolve ties in dice rolls for turn order determination.

**Implementation Details:**
- Iterative approach (while loop) that re-rolls for tied players
- Continues until single winner emerges

**Time Complexity:**
- **Average Case:** O(P) where P = players, but with re-rolls: O(P × R) where R = expected re-rolls
- **Worst Case:** O(P × R) where R could theoretically be large if ties persist
- **Space Complexity:** O(P)

**Notes:** Expected number of re-rolls is small (geometric distribution), so effectively O(P) in practice.

---

## 11. Linear Search / Filtering
**Location:**
- `services/building_service.py` - `_find_buildable_vertices()`, `find_best_settlement_for_resource()`
- `engine/turn_engine.py` - `distribute_resources()` (filtering tiles)
- `engine/cpu_player.py` - `generate_candidate_actions()`

**Purpose:**
- Filter buildable locations
- Find valid actions
- Process game entities

**Time Complexity:**
- **Average Case:** O(n) where n = number of items to check
- **Worst Case:** O(n)
- **Space Complexity:** O(n) for result lists

**Notes:** Various linear scans through vertices, edges, tiles, etc.

---

## 12. Heuristic Scoring Algorithm
**Location:** `engine/cpu_player.py` - `score_action()`, `_trade_progress_towards_builds()`

**Purpose:** Evaluate and rank possible CPU actions using weighted heuristics.

**Implementation Details:**
- Multi-factor scoring system
- Phase-dependent weights
- Resource analysis
- Trade evaluation

**Time Complexity:**
- **Average Case:** O(1) per action scoring (constant factors)
- **Worst Case:** O(O) where O = number of opponents (for trade safety checks)
- **Space Complexity:** O(1)

**Notes:** 
- `score_action()`: O(1) for most actions, O(O) for bank trades
- `_trade_progress_towards_builds()`: O(1) - checks 4 build types

---

## Summary Table

| Algorithm | Location | Average Time | Worst Time | Space |
|-----------|----------|--------------|------------|-------|
| Dijkstra's Algorithm | `pathfinding.py` | O(E log V) | O(E log V) | O(V) |
| Breadth-First Search | `pathfinding.py` | O(V + E) | O(V + E) | O(V) |
| Priority Queue/Heap | `cpu_player.py`, `pathfinding.py` | O(n log n) | O(n log n) | O(n) |
| Sorting (Timsort) | `game.py`, `building_service.py` | O(n log n) | O(n log n) | O(n) |
| Counter Operations | `turn_engine.py` | O(1) | O(k) | O(k) |
| DefaultDict | `turn_engine.py`, `board.py` | O(1) | O(1) amortized | O(n) |
| Random Selection | `turn_engine.py`, `dice.py` | O(1) | O(n) | O(n) |
| Graph Traversal | `building_rules.py`, `board.py` | O(deg(v)) | O(deg(v)) | O(1) |
| Resource Mapping | `building_service.py` | O(H × V) build, O(T) lookup | O(H × V) | O(H × V) |
| Tie Resolution | `game.py` | O(P × R) | O(P × R) | O(P) |
| Linear Search | Various | O(n) | O(n) | O(n) |
| Heuristic Scoring | `cpu_player.py` | O(1) | O(O) | O(1) |

**Legend:**
- V = number of vertices (~54 in Catan)
- E = number of edges (~72 in Catan)
- H = number of hexes (19 in Catan)
- P = number of players (3-4)
- O = number of opponents
- n = variable size (depends on context)
- k = number of resource types (5)
- T = number of target vertices
- R = expected re-rolls (typically small)
- deg(v) = vertex degree (typically 2-3)


