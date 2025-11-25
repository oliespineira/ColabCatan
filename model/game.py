"""
Game setup and main game loop for Simplified Catan.

This module handles:
1. Game state tracking (player order, phases, resources)
2. Initial setup (dice rolling, settlement placement in snake order)
3. Main game loop integration with building service
4. Human and CPU player turn management

COMPLEX TECHNIQUES WE'RE USING HERE:
* PYTHON DICTIONARIES - Storing player resources, board state
* RECURSION - Resolving ties in dice rolls for turn order
* MODULAR DESIGN - Separating setup, rules, and building logic
"""

from dataclasses import dataclass, field
import random
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .board import BoardGraph, create_standard_board, Vertex, Edge
from .enums import Resource
from ..services.building_service import BuildingService
from ..engine.turn_adapter import TurnEngineAdapter


class GamePhase(Enum):
    """
    Enumeration of game phases to track the current stage.
    
    Phases flow: WAITING_FOR_PLAYERS -> DETERMINING_ORDER -> 
    FIRST_SETTLEMENT_ROUND -> SECOND_SETTLEMENT_ROUND -> MAIN_GAME -> GAME_OVER
    """
    WAITING_FOR_PLAYERS = "waiting for players"
    DETERMINING_ORDER = "determining_order"
    FIRST_SETTLEMENT_ROUND = "first_settlement_round"
    SECOND_SETTLEMENT_ROUND = "second_settlement_round"
    MAIN_GAME = "main_game"
    GAME_OVER = "game_over"


@dataclass
class Player:
    """
    Represents a player in the game.
    
    Tracks resources, building pieces remaining, victory points, and whether
    the player is controlled by CPU or human.
    """
    id: int
    name: str
    colour: str  # British spelling
    is_cpu: bool = False  # Flag to distinguish CPU from human players

    # Dictionary mapping resource types to quantities owned
    resources: dict[Resource, int] = field(default_factory=lambda: {
        Resource.LUMBER: 0,
        Resource.WOOL: 0,
        Resource.GRAIN: 0,
        Resource.BRICK: 0,
        Resource.ORE: 0
    })

    victory_points: int = 0
    settlements_remaining: int = 5
    cities_remaining: int = 4
    roads_remaining: int = 15

    has_longest_road: bool = False

    def add_resource(self, resource: Resource, amount: int = 1):
        """
        Add resources to the player's inventory.
        
        Args:
            resource: The type of resource to add
            amount: Quantity to add (default 1)
        """
        self.resources[resource] += amount

    def remove_resource(self, resource: Resource, amount: int = 1) -> bool:
        """
        Remove resources from the player's inventory.
        
        Args:
            resource: The type of resource to remove
            amount: Quantity to remove (default 1)
            
        Returns:
            True if player had enough resources, False otherwise
        """
        if self.resources[resource] >= amount:
            self.resources[resource] -= amount
            return True
        return False
    
    def has_resources(self, cost: dict[Resource, int]) -> bool:
        """
        Check if the player has sufficient resources for a given cost.

        Args:
            cost: Dictionary mapping resource types to required amounts

        Returns:
            True if player has all required resources, False otherwise
        """
        return all(self.resources[res] >= amt for res, amt in cost.items())


@dataclass
class GameState:
    """
    Tracks the complete state of the current game.
    
    This includes the board, all players, current phase, turn order,
    and setup placement history.
    """
    board: BoardGraph
    players: list[Player]
    current_phase: GamePhase = GamePhase.WAITING_FOR_PLAYERS

    # Turn order tracking: list of player IDs in play order
    turn_order: list[int] = field(default_factory=list)
    current_player_idx: int = 0  # Index into turn_order for current player

    # Setup phase tracking: stores (player_id, settlement_vertex, road_edge)
    # for each initial placement
    setup_placements: list[tuple[int, str, str]] = field(default_factory=list)

    # Dice and robber tracking
    last_dice_total: int | None = None
    robber_hex_id: int = 11  # Default robber position

    def get_current_player(self) -> Player:
        """
        Get the player whose turn it currently is.
        
        Returns:
            The Player object for the current turn
        """
        player_id = self.turn_order[self.current_player_idx]
        return self.players[player_id]
    
    def next_turn(self):
        """
        Advance to the next player's turn.
        
        Handles different turn progression logic based on game phase:
        - FIRST_SETTLEMENT_ROUND: Forward order (0, 1, 2, ...)
        - SECOND_SETTLEMENT_ROUND: Reverse order (..., 2, 1, 0) - snake order
        - MAIN_GAME: Normal cycling through players
        """
        if self.current_phase == GamePhase.FIRST_SETTLEMENT_ROUND:
            # Step 1: Move forward in the player list
            self.current_player_idx += 1
            
            # Step 2: If we've reached the end, switch to reverse order
            if self.current_player_idx >= len(self.players):
                self.current_phase = GamePhase.SECOND_SETTLEMENT_ROUND
                # Start from the last player for reverse order
                self.current_player_idx = len(self.players) - 1
                
        elif self.current_phase == GamePhase.SECOND_SETTLEMENT_ROUND:
            # Step 3: Move backward in the player list (snake order)
            self.current_player_idx -= 1
            
            # Step 4: If we've gone past the start, begin main game
            if self.current_player_idx < 0:
                self.current_phase = GamePhase.MAIN_GAME
                self.current_player_idx = 0
        else:
            # Step 5: Normal game - cycle through players using modulo
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)


class GameSetup:
    """
    Handles all pre-game setup logic and main game loop integration.
    
    Manages:
    - Game creation and player initialisation
    - Turn order determination via dice rolling
    - Initial settlement and road placement (snake order)
    - Resource distribution
    - Main game loop with building service integration
    """
    
    def __init__(self):
        """Initialise the game setup with empty game state and building service."""
        self.game: GameState | None = None
        self.building_service: Optional[BuildingService] = None
        self.turn_engine_adapter: Optional[TurnEngineAdapter] = None

    def create_game(
        self,
        player_names: list[str],
        player_colours: list[str],
        cpu_players: Optional[list[bool]] = None
    ) -> GameState:
        """
        Create a new game with the specified players.
        
        Steps:
        1. Validate player count (3-4 players required)
        2. Validate that names and colours lists match in length
        3. Validate CPU player flags if provided
        4. Create Player objects with CPU flags
        5. Generate randomised board
        6. Initialise GameState
        7. Create BuildingService for main game building logic
        
        Args:
            player_names: List of 3-4 player names
            player_colours: List of colours (one per player)
            cpu_players: Optional list of booleans marking which players are CPU-controlled
            
        Returns:
            The created GameState object
        """
        # Step 1: Validate player count
        if not (3 <= len(player_names) <= 4):
            raise ValueError("Catan requires 3-4 players")
        
        # Step 2: Validate names and colours match
        if len(player_names) != len(player_colours):
            raise ValueError("The number of colours doesn't match the number of players")
        
        # Step 3: Validate CPU flags if provided
        if cpu_players and len(cpu_players) != len(player_names):
            raise ValueError("cpu_players list must match player count")

        # Step 4: Create Player objects
        players = []
        for i, (name, colour) in enumerate(zip(player_names, player_colours)):
            # Determine if this player is CPU-controlled
            is_cpu = cpu_players[i] if cpu_players else False
            players.append(Player(
                id=i,
                name=name,
                colour=colour,
                is_cpu=is_cpu
            ))
        
        # Step 5: Create randomised board
        board = create_standard_board()

        # Step 6: Initialise game state
        self.game = GameState(
            board=board,
            players=players,
            current_phase=GamePhase.DETERMINING_ORDER
        )
        
        # Step 7: Create building service for main game integration
        self.building_service = BuildingService(self.game)
        self.turn_engine_adapter = TurnEngineAdapter(self.game)
        return self.game
    
    def determine_turn_order(self) -> list[tuple[str, int]]:
        """
        Determine turn order by having each player roll dice.
        
        Steps:
        1. Each player rolls two dice
        2. Find the highest roll value
        3. Identify all players who tied for highest
        4. If there's a tie, recursively re-roll until one player wins
        5. Sort players by roll (descending)
        6. Set turn order and advance to first settlement round
        
        Returns:
            List of tuples (player_name, final_roll_value) in turn order
        """
        if not self.game:
            raise ValueError("The game has not yet been created")
        if self.game.current_phase != GamePhase.DETERMINING_ORDER:
            raise ValueError("Not in turn order determination phase")

        # Step 1: Collect initial rolls from all players
        rolls = []
        for player in self.game.players:
            roll = self._roll_dice()
            total = sum(roll)
            rolls.append((player, total))

        # Step 2: Find the highest roll value
        max_roll = max(r[1] for r in rolls)

        # Step 3: Identify players who tied for highest
        highest_rollers = [r for r in rolls if r[1] == max_roll]

        # Step 4: Resolve ties using recursion (re-roll until one winner)
        while len(highest_rollers) > 1:
            print(f"Tie between players. They will re-roll: {[p.name for p, _ in highest_rollers]}")
            new_rolls = []

            # Re-roll for all tied players
            for player, _ in highest_rollers:
                roll = self._roll_dice()
                total = sum(roll)
                new_rolls.append((player, total))
            
            # Find new highest roll and update tied players
            max_roll = max(r[1] for r in new_rolls)
            highest_rollers = [r for r in new_rolls if r[1] == max_roll]

        # Step 5: Sort all players by their final roll (descending order)
        rolls.sort(key=lambda x: x[1], reverse=True)

        # Step 6: Set turn order and advance phase
        self.game.turn_order = [player.id for player, _ in rolls]
        self.game.current_phase = GamePhase.FIRST_SETTLEMENT_ROUND
        self.game.current_player_idx = 0

        return [(player.name, roll) for player, roll in rolls]
        
    def _roll_dice(self) -> tuple[int, int]:
        """
        Roll two six-sided dice.
        
        Returns:
            Tuple of (die1, die2) with values 1-6 each
        """
        return (random.randint(1, 6), random.randint(1, 6))

    def can_place_initial_settlement(self, player_id: int, vertex_id: str) -> tuple[bool, str]:
        """
        Check if a player can place their initial settlement at a vertex.
        
        Validation steps:
        1. Verify game exists
        2. Verify vertex exists on board
        3. Check vertex is empty (no existing settlement/city)
        4. Check distance rule: no neighbouring vertices have settlements
        
        Args:
            player_id: ID of the player attempting placement
            vertex_id: ID of the vertex to check

        Returns:
            Tuple of (can_place: bool, reason: str)
        """
        if not self.game:
            return False, "Game not created"
        
        board = self.game.board
        vertex = board.vertices.get(vertex_id)

        # Step 1: Verify vertex exists
        if not vertex:
            return False, "The vertex ID is invalid"
        
        # Step 2: Check if vertex is empty
        if vertex.owner is not None:
            return False, "The vertex you are trying to access is already occupied"
        
        # Step 3: Check distance rule - no settlements within 2 edges
        for neighbour_id in board.neighbors(vertex_id):
            neighbour = board.vertices[neighbour_id]
            if neighbour.owner is not None:
                return False, "The vertex you want to build in is too close to another settlement (distance rule)"
        
        return True, "Valid placement"
    
    def place_initial_settlement(self, vertex_id: str) -> bool:
        """
        Place an initial settlement for the current player.
        
        Steps:
        1. Verify game is in setup phase
        2. Get current player
        3. Validate placement using can_place_initial_settlement
        4. Update vertex ownership
        5. Decrement player's remaining settlements
        6. Award victory point
        
        Args:
            vertex_id: ID of the vertex where settlement should be placed
            
        Returns:
            True if placement successful, False otherwise
        """
        if not self.game:
            return False
        
        # Step 1: Verify we're in a setup phase
        if self.game.current_phase not in [
            GamePhase.FIRST_SETTLEMENT_ROUND,
            GamePhase.SECOND_SETTLEMENT_ROUND
        ]:
            return False
        
        current_player = self.game.get_current_player()

        # Step 2: Validate placement
        can_place, reason = self.can_place_initial_settlement(current_player.id, vertex_id)
        if not can_place:
            print(f"The settlement cannot be placed: {reason}")
            return False
        
        # Step 3: Place the settlement
        vertex = self.game.board.vertices[vertex_id]
        vertex.owner = current_player.id
        vertex.is_city = False
        current_player.settlements_remaining -= 1
        current_player.victory_points += 1

        print(f"{current_player.name} placed settlement at {vertex_id}")

        return True

    def can_place_initial_road(self, player_id: int, vertex_id: str, edge_id: int) -> tuple[bool, str]:
        """
        Check if a player can place their initial road on an edge.
        
        Validation steps:
        1. Verify game exists
        2. Verify edge exists on board
        3. Check edge is empty (no existing road)
        4. Check edge connects to the settlement just placed
        
        Args:
            player_id: ID of the player attempting placement
            vertex_id: ID of the settlement vertex
            edge_id: ID of the edge to check
            
        Returns:
            Tuple of (can_place: bool, reason: str)
        """
        if not self.game:
            return False, "Game not created"
        
        board = self.game.board
        edge = board.edges.get(edge_id)

        # Step 1: Verify edge exists
        if not edge:
            return False, "The edge ID is invalid"
        
        # Step 2: Check edge is empty
        if edge.owner is not None:
            return False, "This edge already has a road built on it"
        
        # Step 3: Check edge connects to the settlement
        if vertex_id not in [edge.v1, edge.v2]:
            return False, "The road must connect to your settlement"
        
        return True, "Valid placement"
    
    def place_initial_road(self, settlement_vertex_id: str, edge_id: int) -> bool:
        """
        Place an initial road for the current player.
        
        Steps:
        1. Get current player
        2. Validate placement using can_place_initial_road
        3. Update edge ownership
        4. Decrement player's remaining roads
        5. Store placement in setup_placements history
        
        Args:
            settlement_vertex_id: ID of the settlement vertex this road connects to
            edge_id: ID of the edge where road should be placed
            
        Returns:
            True if placement successful, False otherwise
        """
        if not self.game:
            return False
        
        current_player = self.game.get_current_player()

        # Step 1: Validate placement
        can_place, reason = self.can_place_initial_road(current_player.id, settlement_vertex_id, edge_id)
        if not can_place:
            print(f"Cannot place road: {reason}")
            return False

        # Step 2: Place the road
        edge = self.game.board.edges[edge_id]
        edge.owner = current_player.id
        current_player.roads_remaining -= 1

        print(f"{current_player.name} placed road at edge {edge_id}")
        
        # Step 3: Store placement for resource distribution later
        self.game.setup_placements.append((current_player.id, settlement_vertex_id, edge_id))

        return True
    
    def complete_initial_placement(self, settlement_vertex: str, road_edge: int):
        """
        Complete both settlement and road placement for current player, then advance turn.
        
        Steps:
        1. Attempt to place settlement
        2. If settlement succeeds, attempt to place road
        3. If road fails, undo settlement placement (rollback)
        4. If both succeed, advance to next player's turn
        
        This ensures atomic placement: either both succeed or both fail.
        
        Args:
            settlement_vertex: Vertex ID for settlement placement
            road_edge: Edge ID for road placement
            
        Returns:
            True if both placements successful, False otherwise
        """
        # Step 1: Place settlement
        if not self.place_initial_settlement(settlement_vertex):
            return False
        
        # Step 2: Place road
        if not self.place_initial_road(settlement_vertex, road_edge):
            # Step 3: Rollback settlement if road placement fails
            vertex = self.game.board.vertices[settlement_vertex]
            current_player = self.game.get_current_player()
            vertex.owner = None
            current_player.settlements_remaining += 1
            current_player.victory_points -= 1
            return False
        
        # Step 4: Advance to next player
        self.game.next_turn()
        return True
    
    def distribute_initial_resources(self):
        """
        Distribute resources to all players based on their second settlement.
        
        Steps:
        1. Verify game is in MAIN_GAME phase
        2. Extract second settlement placements (last N placements)
        3. For each player's second settlement:
           - Get all hexes adjacent to that settlement
           - Award one resource per hex (if hex produces resources, not desert)
        
        This is called after all second settlements are placed in snake order.
        """
        if not self.game:
            return
        
        if self.game.current_phase != GamePhase.MAIN_GAME:
            print("Not in the main game phase yet")
            return

        # Step 1: Get second settlement placements (last N, where N = number of players)
        num_players = len(self.game.players)
        second_settlements = self.game.setup_placements[-num_players:]

        # Step 2: Distribute resources for each second settlement
        for player_id, settlement_vertex, _ in second_settlements:
            player = self.game.players[player_id]
            vertex = self.game.board.vertices[settlement_vertex]

            # Step 3: Award resources from adjacent hexes
            for hex_id in vertex.hex_ids:
                hex_tile = self.game.board.hexes[hex_id]

                # Only award if hex produces resources (not desert)
                if hex_tile.resource is not None:
                    player.add_resource(hex_tile.resource, 1)
                    print(f"{player.name} receives 1 {hex_tile.resource.value} from hex {hex_id}")

        print("The initial resources were distributed")

    def _print_player_resources(self):
        """
        Helper method to print all players' current resource counts.

        Displays each player's name followed by their resources in format:
        "ResourceName: amount, ResourceName: amount"
        """
        if not self.game:
            return
        
        for player in self.game.players:
            resources_str = ", ".join([f"{res.value}: {amt}" for res, amt in player.resources.items() if amt > 0])
            print(f"{player.name}: {resources_str if resources_str else 'No resources'}")

    def run_full_setup(
        self,
        player_names: list[str],
        player_colours: list[str],
        placements: list[tuple[str, int]]
    ) -> GameState:
        """
        Run the entire setup sequence automatically.
        
        Steps:
        1. Create game with players
        2. Display board setup message
        3. Determine turn order via dice rolling
        4. Place initial settlements and roads (first round forward, second round reverse)
        5. Distribute initial resources
        
        Args:
            player_names: List of player names
            player_colours: List of player colours
            placements: List of (settlement_vertex, road_edge) tuples
                       Order: P1_first, P2_first, P3_first, [P4_first], 
                              [P4_second], P3_second, P2_second, P1_second
        
        Returns:
            GameState ready to start main game
        """
        # Step 1: Create game
        print("1. The Game is Being Created")
        self.create_game(player_names, player_colours)
        print(f"The game was created with {len(player_names)} players\n")

        # Step 2: Board setup
        print("2. Board Setup")
        print("The board was created and randomised")

        # Step 3: Determine turn order
        print("3. Determining Turn Order")
        order = self.determine_turn_order()
        for name, roll in order:
            print(f"{name} rolled {roll}")
        print(f"Turn order: {' -> '.join([p.name for p in self.game.players])}\n")

        # Step 4: Initial placement (snake order)
        print("4. Initial Placement")
        print("First round (forward):")

        placement_idx = 0
        num_players = len(self.game.players)
        
        # First round: forward order
        for i in range(num_players):
            player = self.game.get_current_player()
            vertex, edge = placements[placement_idx]
            print(f"  {player.name}: Settlement at {vertex}, Road at edge {edge}")
            self.complete_initial_placement(vertex, edge)
            placement_idx += 1
        
        # Second round: reverse order (snake order)
        print("Second round (reverse):")
        for i in range(num_players):
            player = self.game.get_current_player()
            vertex, edge = placements[placement_idx]
            print(f"  {player.name}: Settlement at {vertex}, Road at edge {edge}")
            self.complete_initial_placement(vertex, edge)
            placement_idx += 1
        
        print()

        # Step 5: Distribute initial resources
        print("5. Distributing Initial Resources")
        self.distribute_initial_resources()

        print("The setup was finalised")

        return self.game

    # ==================== MAIN GAME LOOP INTEGRATION ====================

    def run_main_game_loop(self, max_turns: int = 10):
        """
        Run the main game loop with building integration for human and CPU players.
        
        Steps:
        1. Verify game and building service exist
        2. Ensure game is in MAIN_GAME phase
        3. Loop through turns:
           a. Get current player
           b. Display turn information and resources
           c. Run human turn (prompts) or CPU turn (automatic)
           d. Check for victory condition (10 victory points)
           e. Advance to next player
        4. End when victory achieved or turn limit reached
        
        This integrates the building service, pathfinding, and building rules
        that were created separately.
        
        Args:
            max_turns: Maximum number of turns to simulate (default 10)
        """
        # Step 1: Verify game exists
        if not self.game:
            print("Game not created")
            return

        # Step 2: Ensure building service is initialised
        if not self.building_service:
            self.building_service = BuildingService(self.game)

        # Step 3: Ensure we're in main game phase
        if self.game.current_phase != GamePhase.MAIN_GAME:
            print("Warning: main game loop started before MAIN_GAME phase")
            self.game.current_phase = GamePhase.MAIN_GAME

        # Step 4: Main game loop
        turn_counter = 0
        while self.game.current_phase == GamePhase.MAIN_GAME and turn_counter < max_turns:
            player = self.game.get_current_player()
            print(f"\n--- Turn {turn_counter + 1}: {player.name} ({'CPU' if player.is_cpu else 'Human'}) ---")

            dice_events = self._execute_dice_phase(player)
            if dice_events:
                self._summarise_dice_events(player, dice_events)

            self._print_player_resources()

            # Step 4c: Run appropriate turn handler
            if player.is_cpu:
                self._run_cpu_turn(player)
            else:
                self._run_human_turn(player)

            # Step 4d: Check victory condition
            if player.victory_points >= 10:
                print(f"{player.name} wins the game!")
                self.game.current_phase = GamePhase.GAME_OVER
                break

            # Step 4e: Advance to next player
            self.game.next_turn()
            turn_counter += 1

        # Step 5: End game message
        if self.game.current_phase == GamePhase.MAIN_GAME:
            print("Main game loop ended (turn limit reached).")

    def _ensure_turn_engine_adapter(self) -> TurnEngineAdapter:
        if not self.game:
            raise ValueError("Game not created")
        if self.turn_engine_adapter is None:
            self.turn_engine_adapter = TurnEngineAdapter(self.game)
        return self.turn_engine_adapter

    def _execute_dice_phase(self, player: Player) -> Optional[Dict[str, object]]:
        if not self.game:
            return None
        adapter = self._ensure_turn_engine_adapter()
        events = adapter.run_dice_phase(player.id)
        self.game.last_dice_total = events["roll"]
        return events

    def _summarise_dice_events(self, player: Player, events: Dict[str, object]) -> None:
        roll = events["roll"]
        print(f"{player.name} rolled {roll}")

        if roll == 7:
            discards = events.get("discards", {})
            if discards:
                for pid, removed in discards.items():
                    victim = self.game.players[int(pid)]
                    print(f"  {victim.name} discarded {removed}")

            robber_info = events.get("robber", {})
            if robber_info:
                print(f"  Robber moved to hex {robber_info.get('moved_to')}")

            steal_info = events.get("steal", {})
            if steal_info and steal_info.get("from"):
                thief = player.name
                victim = self.game.players[int(steal_info["from"])].name
                resource = steal_info.get("resource")
                print(f"  {thief} stole 1 {resource} from {victim}")
            return

        gains = events.get("gains", {})
        if not gains:
            print("  No one produced resources.")
            return
        for pid, resources in gains.items():
            target_player = self.game.players[int(pid)]
            gains_str = ", ".join(f"{amt} {res}" for res, amt in resources.items())
            print(f"  {target_player.name} gains {gains_str}")

    def _run_human_turn(self, player: Player):
        """
        Handle a human player's turn with interactive prompts.
        
        Steps:
        1. Display action menu (road/settlement/city/pass)
        2. Get user input for action choice
        3. For building actions, prompt for location (edge/vertex ID)
        4. Call building service to execute action
        5. Display result message
        6. Allow multiple actions per turn (loop until 'pass')
        
        This provides the UI/prompts for human players to build.
        
        Args:
            player: The Player object whose turn it is
        """
        if not self.building_service:
            return

        """we kinda have to show the player what they have, they odnt have cards like in the physical game"""

        print(f"{player.name}'s Turn")
   
        
        # Show current resources
        print("\nYour Resources:")
        for resource, amount in player.resources.items():
            #here we only show resources that are greater than 0
            if amount > 0:
                print(f"  {resource.name}: {amount}")
        
        print(f"\nVictory Points: {player.victory_points}")
        print(f"Settlements: {player.settlements_remaining} remaining")
        print(f"Cities: {player.cities_remaining} remaining")
        print(f"Roads: {player.roads_remaining} remaining")
        
        # Show what they can afford
        print("\nYou can afford:")
        affordable = []
        
        if player.has_resources({Resource.BRICK: 1, Resource.LUMBER: 1}):
            affordable.append("Road")
        if player.has_resources({Resource.BRICK: 1, Resource.LUMBER: 1, 
                                Resource.GRAIN: 1, Resource.WOOL: 1}):
            affordable.append("Settlement")
        if player.has_resources({Resource.GRAIN: 2, Resource.ORE: 3}):
            affordable.append("City")
        
        if affordable:
            print(f"  {', '.join(affordable)}")
        else:
            print("  Nothing (need more resources)")

        # Loop allows multiple actions per turn. Slay
    # Action loop
        while True:
            print("\n" + "-"*60)
            action = input("Action [road/settlement/city/pass/help]: ").strip().lower()

            if not action:
                print("Please enter an action.")
                continue
            #were nice developers and we give the player help if they ask for it.
            if action in {"help", "h", "?"}:
                print("\nAvailable Actions:")
                print("  road - Build a road (costs: 1 Brick, 1 Lumber)")
                print("  settlement - Build a settlement (costs: 1 Brick, 1 Lumber, 1 Grain, 1 Wool)")
                print("  city - Upgrade settlement to city (costs: 2 Grain, 3 Ore)")
                print("  pass - End your turn")
                continue
            # If the player passes (or hits enter), end the turn.
            if action in {"pass", "p", ""}:
                print("Turn ended.")
                break
            
            elif action in {"road", "r"}:
                # Show available edges
                connected = self.building_service.pathfinding.get_player_connected_vertices(player.id)
                print(f"\nYou're connected to vertices: {', '.join(connected)}")# Show connected vertices to help them choose where to build.
                
                edge_id = self._prompt_edge_id() # Ask the user for an edge ID using a helper method.
                if edge_id is None:
                    continue
                # Attempt to build the road via the building service.

                success, message = self.building_service.build_road(player.id, edge_id)
                print(f"\n>>> {message}")
                
                if success:
                    # Ask if they want to do more
                    more = input("\nBuild something else? (y/n): ").lower().strip()
                    if more != 'y':
                        break
            
            elif action in {"settlement", "s"}:
                # Show buildable vertices
                buildable = self.building_service._find_buildable_vertices(player.id)
                if buildable:
                    print(f"\nBuildable vertices: {', '.join(buildable[:10])}")
                    if len(buildable) > 10:
                        print(f"  ... and {len(buildable) - 10} more")
                
                vertex_id = input("Enter vertex ID: ").strip()
                success, message = self.building_service.build_settlement(player.id, vertex_id)
                print(f"\n>>> {message}")
                
                if success:
                    more = input("\nBuild something else? (y/n): ").lower().strip()
                    if more != 'y':
                        break
            
            elif action in {"city", "c"}:
                # Show upgradeable settlements
                upgradeable = []
                for vertex_id, vertex in self.game.board.vertices.items():
                    if vertex.owner == player.id and not vertex.is_city:
                        upgradeable.append(vertex_id)
                
                if upgradeable:
                    print(f"\nYour settlements: {', '.join(upgradeable)}")
                else:
                    print("\nYou have no settlements to upgrade.")
                    continue
                
                vertex_id = input("Enter vertex ID to upgrade: ").strip()
                success, message = self.building_service.upgrade_to_city(player.id, vertex_id)
                print(f"\n>>> {message}")
                
                if success:
                    more = input("\nBuild something else? (y/n): ").lower().strip()
                    if more != 'y':
                        break
            
            else:
                print("Unknown action. Type 'help' for available actions.")

    def _run_cpu_turn(self, player: Player):
        """
        Handle a CPU player's turn using automatic building decisions.
        
        Steps:
        1. Try to build a settlement using CPU building service
           (uses pathfinding and resource location scoring)
        2. If settlement building fails, try to build a road
           (uses shortest path algorithm to target resources)
        3. Display the result message
        
        This connects CPU building decisions to the pathfinding and
        building service logic.
        
        Args:
            player: The Player object whose turn it is (must be CPU)
        """
        if not self.building_service:
            return

        # Step 1: Try to build settlement (higher priority)
        built_settlement, settlement_msg = self.building_service.cpu_build_settlement(player.id)
        if built_settlement:
            print(settlement_msg)
            return

        # Step 2: If settlement fails, try to build road
        built_road, road_msg = self.building_service.cpu_build_road(player.id)
        print(road_msg)

    def _prompt_edge_id(self) -> Optional[int]:
        """
        Helper method to safely parse an edge ID from user input.
        
        Steps:
        1. Get user input
        2. Attempt to convert to integer
        3. Return integer or None if invalid
        
        Returns:
            Edge ID as integer, or None if input invalid
        """
        raw = input("Enter edge ID: ").strip()
        try:
            return int(raw)
        except ValueError:
            print("Edge ID must be an integer.")
            return None


    def display_board_info(self):
        """were super nice deveoples and we actually display board information"""
        if not self.game:#if the game is not set up, we return
            return
        
        print("\n Board Information:")
        print("\nVertex IDs (sample):")
        vertices = list(self.game.board.vertices.keys())
        print(f"  {', '.join(vertices[:20])}")
        if len(vertices) > 20:
            print(f"  ... and {len(vertices) - 20} more vertices")
        
        print("\nEdge IDs (sample):")
        edges = list(self.game.board.edges.keys())
        print(f"  {', '.join(map(str, edges[:20]))}")
        if len(edges) > 20:
            print(f"  ... and {len(edges) - 20} more edges")
        
        print("\nHex Resources:")
        for hex_id, hex_tile in sorted(self.game.board.hexes.items())[:10]:
            if hex_tile.resource:
                print(f"  Hex {hex_id}: {hex_tile.resource.name} (dice: {hex_tile.number})")

    def interactive_initial_placement(self) -> bool:
        """
        Guide players through initial placement interactively.
        Returns True if successful, False if cancelled.
        """
        if not self.game:
            return False
        
        self.display_board_info()
        
        # First round (forward)
        print("\n=== FIRST SETTLEMENT ROUND ===")
        print("Each player places one settlement and one road.")
        
        for i in range(len(self.game.players)):
            player = self.game.get_current_player()
            print(f"\n{player.name}'s placement:")
            
            if player.is_cpu:
                # Simple CPU placement - just use first available
                available_vertices = list(self.game.board.vertices.keys())
                for vertex_id in available_vertices:
                    can_place, _ = self.can_place_initial_settlement(player.id, vertex_id)
                    if can_place:
                        # Find a valid road
                        vertex = self.game.board.vertices[vertex_id]
                        for edge_id in vertex.edge_ids:
                            edge = self.game.board.edges[edge_id]
                            if edge.owner is None:
                                print(f"  CPU places: Settlement at {vertex_id}, Road at {edge_id}")
                                self.complete_initial_placement(vertex_id, edge_id)
                                break
                        break
            else:
                # Human placement with validation
                while True:
                    vertex_id = input("  Enter settlement vertex ID: ").strip()
                    can_place, reason = self.can_place_initial_settlement(player.id, vertex_id)
                    
                    if not can_place:
                        print(f"  Cannot place: {reason}")
                        retry = input("  Try again? (y/n): ").lower().strip()
                        if retry != 'y':
                            return False
                        continue
                    
                    # Show available edges for this vertex
                    vertex = self.game.board.vertices.get(vertex_id)
                    if vertex:
                        print(f"  Available edges from {vertex_id}: {vertex.edge_ids}")
                    
                    try:
                        edge_id = int(input("  Enter road edge ID: "))
                    except ValueError:
                        print("  Invalid edge ID. Must be a number.")
                        continue
                    
                    can_place_road, reason = self.can_place_initial_road(player.id, vertex_id, edge_id)
                    if not can_place_road:
                        print(f"  Cannot place road: {reason}")
                        continue
                    
                    # Valid placement
                    success = self.complete_initial_placement(vertex_id, edge_id)
                    if success:
                        print(f"  ✓ Placed settlement at {vertex_id} and road at {edge_id}")
                        break
                    else:
                        print("  Placement failed. Try again.")
        
        # Second round (reverse/snake)
        print("\n=== SECOND SETTLEMENT ROUND (REVERSE ORDER) ===")
        
        for i in range(len(self.game.players)):
            player = self.game.get_current_player()
            print(f"\n{player.name}'s placement:")
            
            if player.is_cpu:
                available_vertices = list(self.game.board.vertices.keys())
                for vertex_id in available_vertices:
                    can_place, _ = self.can_place_initial_settlement(player.id, vertex_id)
                    if can_place:
                        vertex = self.game.board.vertices[vertex_id]
                        for edge_id in vertex.edge_ids:
                            edge = self.game.board.edges[edge_id]
                            if edge.owner is None:
                                print(f"  CPU places: Settlement at {vertex_id}, Road at {edge_id}")
                                self.complete_initial_placement(vertex_id, edge_id)
                                break
                        break
            else:
                while True:
                    vertex_id = input("  Enter settlement vertex ID: ").strip()
                    can_place, reason = self.can_place_initial_settlement(player.id, vertex_id)
                    
                    if not can_place:
                        print(f"  Cannot place: {reason}")
                        continue
                    
                    vertex = self.game.board.vertices.get(vertex_id)
                    if vertex:
                        print(f"  Available edges from {vertex_id}: {vertex.edge_ids}")
                    
                    try:
                        edge_id = int(input("  Enter road edge ID: "))
                    except ValueError:
                        print("  Invalid edge ID.")
                        continue
                    
                    can_place_road, reason = self.can_place_initial_road(player.id, vertex_id, edge_id)
                    if not can_place_road:
                        print(f"  Cannot place road: {reason}")
                        continue
                    
                    success = self.complete_initial_placement(vertex_id, edge_id)
                    if success:
                        print(f"  ✓ Placed settlement at {vertex_id} and road at {edge_id}")
                        break
        
        return True


    
def run_interactive_game(self):
    """
    Run a fully interactive game from start to finish.
    """
    print("=== CATAN GAME SETUP ===\n")
    
    # Get players
    num_players = int(input("Number of players (3-4): "))
    player_names = []
    player_colours = []
    cpu_flags = []
    
    colours = ["red", "blue", "white", "orange"]
    
    for i in range(num_players):
        name = input(f"Player {i+1} name: ")
        player_names.append(name)
        
        is_cpu = input(f"Is {name} a CPU? (y/n): ").lower() == 'y'
        cpu_flags.append(is_cpu)
        
        print(f"Available colours: {colours}")
        colour = input(f"Colour for {name}: ")
        player_colours.append(colour)
        colours.remove(colour)
    
    # Create game
    self.create_game(player_names, player_colours, cpu_flags)
    print("\n✓ Game created")
    
    # Determine turn order
    print("\n=== TURN ORDER ===")
    order = self.determine_turn_order()
    for name, roll in order:
        print(f"  {name}: {roll}")
    
    # Initial placement
    if not self.interactive_initial_placement():
        print("Game cancelled.")
        return
    
    # Distribute resources
    self.distribute_initial_resources()
    print("\n✓ Initial resources distributed")
    
    # Main game
    print("\n=== MAIN GAME ===")
    self.run_main_game_loop(max_turns=200)
    
    # Game over
    winner = max(self.game.players, key=lambda p: p.victory_points)
    print(f"\n🏆 {winner.name} WINS with {winner.victory_points} victory points!")
