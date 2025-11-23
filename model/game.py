"""
This is what sets up the game before the actual rounds begin.
1. It tracks where each player is in the game (determining the order of rolling dice, placing the first and second settlements and providing the resources to each player)
COMPLEX TECHNIQUES WE'RE USING HERE:
* PYTHON DICTIONARIES
* RECURSION TO SEE WHO THROWS THE HIGHEST DIE
*using dfs for calculating the length (longest path) of each player's road

"""

from dataclasses import dataclass, field
import random
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random

from .board import BoardGraph, create_standard_board, Vertex, Edge
from .enums import Resource

class GamePhase(Enum):# This looks at the current stage of the game
    WAITING_FOR_PLAYERS= "waiting for players"
    DETERMINING_ORDER= "determining_order"
    FIRST_SETTLEMENT_ROUND= "first_settlement_round"
    SECOND_SETTLEMENT_ROUND= "second_settlement_round"
    MAIN_GAME= "main_game"
    GAME_OVER= "game_over"

@dataclass
class Player:#represents the player in the game
    id: int
    name: str
    colour: str

    resources: dict[Resource, int]= field(default_factory= lambda:{
        Resource.LUMBER:0,
        Resource.WOOL:0,
        Resource.GRAIN: 0,
        Resource.BRICK: 0,
        Resource.ORE:0

    })

    victory_points: int=0
    settlements_remaining: int=5
    cities_remaining: int =4
    roads_remaining: int= 15

    has_longest_road:bool= False

    def add_resource(self, resource: Resource, amount: int=1):
        self.resources[resource]+= amount
    def remove_resource(self, resource: Resource, amount: int=1)-> bool: #RETURNS FALSE IF THERE ARE NOT ENOUGH RESOURCES
        if self.resources[resource]>= amount:
            self.resources[resource]-=amount
            return True
        return False
    
    def has_resources(self, cost: dict[Resource, int])-> bool: #checks if the player has enough resources for a cost
        return all(self.resources[res]>= amt for res, amt in cost.items())




#this is used to teack everything related to the current game
@dataclass
class GameState:
    board: BoardGraph
    players: list[Player]
    current_phase: GamePhase= GamePhase.WAITING_FOR_PLAYERS

    # now checking the turn order
    turn_order: list[int]= field(default_factory=list)# this would be for the list of player IDs
    current_player_idx: int = 0

    #setup phase tracking
    setup_placements: list[tuple[int, str, int]]= field(default_factory=list)
    # Each tuple: (player_id, settlement_vertex, road_edge_or_vertex)

    #dice and robber:
    last_dice_roll: Tuple[int, int] | None = None
    robber_hex_id: int =11

    def get_current_player(self)-> Player:
        """Returns the player whose turn it is"""
        player_id= self.turn_order[self.current_player_idx]
        return self.players[player_id]
    
    def next_turn(self):
        """move to the next player's turn"""
        if self.current_phase ==GamePhase.FIRST_SETTLEMENT_ROUND:
            #this is in forward order.
            self.current_player_idx+=1
            if self.current_player_idx>=len(self.players):
                #once the first round is complete, do the second round in reverse(snake order)
                self.current_phase= GamePhase.SECOND_SETTLEMENT_ROUND
                self.current_player_idx= len(self.players)-1
        elif self.current_phase == GamePhase.SECOND_SETTLEMENT_ROUND:
            #here we're actually going in reverse, before we only changed the attribute so we would enter this else statement
            self.current_player_idx-=1 
            if self.current_player_idx<0:
                #now change the value to start the main game
                self.current_phase= GamePhase.MAIN_GAME
                self.current_player_idx =0
        else:
            #for a nurmal game: we cycle through the players in normal order
            self.current_player_idx= (self.current_player_idx +1)%len(self.players)
class GameSetup:
    """the pre-game setup logic"""
    def __init__(self):
        self.game: GameState | None = None

    #NOW ENTERING THE GAME
    def create_game(self, player_names: list[str], player_colours: list[str])-> GameState:
        """
        Creates a new game with the players input.
        player_names: list of 3-4 player names
        player_colours: list of colours(associated to each player)

        returns the GameState object

        THINK OF HOW TO USE CPU PLAYERS FOR THIS
        
        """
        if not (3<= len(player_names)<=4):
            raise ValueError("Catan requires 3-4 players")
        if len(player_names) != len(player_colours):
            raise ValueError("The amount of colours doesn't coincide with the amount of players")
        
        #here we create the players
        players= []
        for i, (name, colour) in enumerate(zip(player_names, player_colours)):
            players.append(Player(
                id=i,
                name= name,
                colour= colour
            ))
        #now we create the randomised board
        board= create_standard_board()

        #now we initialise the game state
        self.game= GameState(
            board= board,
            players=players,
            current_phase= GamePhase.DETERMINING_ORDER
        )
        return self.game
    
    def determine_turn_order(self)-> list[tuple[str, int]]:
        """
        here, each player rolls the dice. The highest roll goes first.
        Re-roll on ties.

        it returns a list of tuples(player_name, roll)
        """

        if not self.game:
            raise ValueError("The game has not yet been created")
        if self.game.current_phase != GamePhase.DETERMINING_ORDER:
            raise ValueError("Not in turn order determination phase")
        rolls= []

        for player in self.game.players:
            roll= self._roll_dice()
            total = sum(roll)
            rolls.append((player, total))


        #here we check for ties at the highest roll
        max_roll= max(r[1] for r in rolls)
        highest_rollers = [r for r in rolls if r[1]== max_roll]

            #highest_rollers contains the list of rollers that have the highest role and that is the same value, therefore we are using recursion to roll until 


        while len(highest_rollers)>1:
            print(f"tie betweeen players. They will re-roll: {[p.name for p, _ in highest_rollers]}")
            new_rolls=[]
            for player, _ in highest_rollers:
                roll= self._roll_dice()
                total= sum(roll)
                new_rolls.append((player, total))
            max_roll= max(r[1] for r in new_rolls)
            highest_rollers= [r for r in new_rolls if r[1]== max_roll]
        
        rolls.sort(key=lambda x:x[1], reverse= True) #sorting the players by their final roll (descending)

        #setting turn order
        self.game.turn_order = [player.id for player, _ in rolls ]
        self.game.current_phase = GamePhase.FIRST_SETTLEMENT_ROUND
        self.game.current_player_idx = 0

        return [(player.name, roll) for player, roll in rolls]
        
    def _roll_dice(self)-> tuple[int, int]:
        """
        Rolling 2 six sided dice
        """
        return (random.randint(1,6), random.randint(1,6))
    
    #NOW COMES THE INITIAL SETTLEMENT PLACEMENT IN SNAKE ORDER

    def can_place_initial_settlement(self, player_id: int, vertex_id: str)-> tuple[bool, str]:
        """
        First we check whether the player can actually place the initial settlement at the vertex.

        the rules that apply here are the following:
        - Vertex must be empty
        - No settlement within 2 edges 

        Returns:
        boolean
    
        """

        if not self.game:
            return False, "Game not created"
        board = self.game.board
        vertex= board.vertices.get(vertex_id)

        if not vertex:
            return False, "The vertex ID is invalid"
        
        #check if the vertex is empty
        if vertex.owner is not None:
            return False, "The vertex you are trying to access is already occupied"
        
        for neighbour_id in board.neighbors(vertex_id):
            neighbour = board.vertices[neighbour_id]
            if neighbour.owner is not None:
                return False, "The vertex you want to build in is too close to another settlement (distance rule)"
        return True, "Valid placement"
    
    def place_initial_settlement(self, vertex_id: str)-> bool:
        """
        This method places the initial settlement for current player.

        returns true id the placement is successful
        """

        if not self.game:
            return False
        if self.game.current_phase not in[
            GamePhase.FIRST_SETTLEMENT_ROUND,
            GamePhase.SECOND_SETTLEMENT_ROUND
        ]:
            return False
        
        current_player = self.game.get_current_player()

        #now we validat the placement
        can_place, reason= self.can_place_initial_settlement(current_player.id, vertex_id)
        if not can_place:
            print(f"The settlement cannot be placed: {reason}")
            return False
        
        #here we finally place the settlement
        vertex= self.game.board.vertices[vertex_id]
        vertex.owner = current_player.id
        vertex.is_city= False
        current_player.settlements_remaining -=1
        current_player.victory_points +=1

        print(f"{current_player.name} placed settlement at {vertex_id}")

        return True
    
    def can_place_initial_road(self, player_id: int, vertex_id: str, edge_id: int)->tuple[bool, str]:
        """
        This method is similar to the above but instead of checking vertex, we check for the edge

        RULES:
        - Must connect to the settlement just placed
        -Edge must be empty

        RETURNS:
        boolean and reason 
        """

        if not self.game:
            return False, "Game not created"
        
        board = self.game.board
        edge = board.edges.get(edge_id)

        if not edge:
            return False, "The edge ID is invalid"
        
        if edge.owner is not None:
            return False, "This edge already has an road built on it"
        
        #check if the edge connects to the settlement that the user created

        if vertex_id not in [edge.v1, edge.v2]:
            return False, "The road must connect to your settlement"
        
        return True, "Valid placement"
    
    def place_initial_road(self, settlement_vertex_id: str, edge_id: int)-> bool:
        """
        Similar to the place method before but with road instead of settlement

        RETURNS:
        true if placement was successfull
        
        """
        if not self.game:
            return False
        
        current_player = self.game.get_current_player()

        can_place, reason = self.can_place_initial_road(current_player.id, settlement_vertex_id, edge_id)
        if not can_place:
            print(f"Cannot place road: {reason}")
            return False
        
        edge= self.game.board.edges[edge_id]
        edge.owner= current_player.id
        current_player.roads_remaining-=1

        print(f"{current_player.name} placed road at edge {edge_id}")
        #now we store the placement
        self.game.setup_placements.append((current_player.id, settlement_vertex_id, edge_id))

        return True
    
    def complete_initial_placement(self, settlement_vertex: str, road_edge: int):
        """
        This method moves to the next player once the player has placed theur settlement and road.
        It either does both steps or backs out. If both actions succeed, advance to the next player.
        
        """

        if not self.place_initial_settlement(settlement_vertex):
            return False
        if not self.place_initial_road(settlement_vertex, road_edge):
            #undo settlement placement
            vertex= self.game.board.vertices[settlement_vertex]
            current_player= self.game.get_current_player()
            vertex.owner=None
            current_player.settlements_remaining +=1
            current_player.victory_points-=1
            return False
        
        self.game.next_turn()
        return True
    

    #NOW WE'RE DISTRIBUTING THE INITIAL RESOURCES
    def distribute_initial_resources(self):
        """
        With this method we procife resources to all players based on their SECOND settlement. 
        This is called after all second settlements are placed.
        """

        if not self.game:
            return
        if self.game.current_phase != GamePhase.MAIN_GAME:
            print("Not in the main game phase yet")
            return

        #Get the second settlement placements 
        num_players = len(self.game.players)
        second_settlements= self.game.setup_placements[-num_players:]# taking the last element from the list

        for player_id, settlement_vertex, _ in second_settlements:
            player= self.game.players[player_id]
            vertex= self.game.board.vertices[settlement_vertex]
        
            #getting all hexes adjacent to this settlement
            for hex_id in vertex.hex_ids:
                hex_tile = self.game.board.hexes[hex_id]

                if hex_tile.resource is not None: #give the resource if hex produces one (is not desert)
                    player.add_resource(hex_tile.resource, 1)
                    print(f"{player.name} receives 1 {hex_tile.resource.value} from hex {hex_id}")

        print("The initial resources were distributed")

    def _print_player_resources(self):
        """This is a helper method to print all players' resources"""

        if not self.game:
            return
        
        for player in self.game.players:
            resources_str= ", ".join([f"{res.value}: {amt}" for res, amt in player.resources.items() if amt>0])
            print(f"{player.name}: {resources_str if resources_str else 'No resources'}")
    
    #now the game flow summary

    def run_full_setup(self, player_names: list[str], player_colours: list[str], placements: list[tuple[str,int]])-> GameState:
        """
        Run the entire setup sequence automatically.
        
        Args:
            player_names: List of player names
            player_colors: List of player colors
            placements: List of (settlement_vertex, road_edge) for each placement
                       Order: P1_first, P2_first, P3_first, [P4_first], 
                              [P4_second], P3_second, P2_second, P1_second
        
        Returns:
            GameState ready to start main game
        """
        #1 create game
        print("1. The Game is Being Created")
        self.create_game(player_names, player_colours)
        print(f" the game was created with {len(player_names)} players\n")

        #2 board setup
        print("2. Board Setup")
        print("The board was created and randomised")

        #3 determining turn order
        print("3. Determining tURN order")
        order= self.determine_turn_order()
        for name, roll in order:
            print(f"{name} rolled {roll}")
        print(f"Turn order: {' -> '.join([p.name for p in self.game.players])}\n")

        #4 placing initial settlements(snake order)
        print("4. Initial Placement")
        print("First round (forward):")

        placement_idx= 0
        num_players= len(self.game.players)
        # First round
        for i in range(num_players):
            player = self.game.get_current_player()
            vertex, edge = placements[placement_idx]
            print(f"  {player.name}: Settlement at {vertex}, Road at edge {edge}")
            self.complete_initial_placement(vertex, edge)
            placement_idx += 1
        
        # Second round (reverse)
        print("Second round (reverse):")
        for i in range(num_players):
            player = self.game.get_current_player()
            vertex, edge = placements[placement_idx]
            print(f"  {player.name}: Settlement at {vertex}, Road at edge {edge}")
            self.complete_initial_placement(vertex, edge)
            placement_idx += 1
        
        print()

        #5. Distributing initial resources
        print("5. Distributing Initial Resources")
        self.distribute_initial_resources()

        print(" The setup was finalised")

        return self.game            
    
    def calculate_longest_road_for_player(self, player_id: int)-> int:
        """
        This method calculates the longest road for a specific player using DFS.
        It then returns the length of the longest continuous road
        """
        #getting all the edges owned by the player that has been passed in to the method.
        player_edges=[edgeid for edgeid, edge in self.board.edges.items() if edge.owner == player_id]
        if len(player_edges)<5: #the player needs at least 5 roads to be considered for the longest road
            return 0
        
        #here we need to build an adjacency list of vertices (undirected) connected by player's roads. 
        #for each owned edge, we ensure both endpoints exist in the dict, then add each to the other's neighbour list
        road_graph={}
        for edgeid in player_edges:
            edge = self.board.edges[edgeid]
            if edge.v1 not in road_graph:
                road_graph[edge.v1]= []
            if edge.v2 not in road_graph:
                road_graph[edge.v2]= []
            road_graph[edge.v1].append(edge.v2)
            road_graph[edge.v2].append(edge.v1)
        
        #DFS to find the longest path
        
    # DFS to find longest path
        def dfs(vertex: str, visited_edges: set) -> int:
            """DFS to find longest road from this vertex
            visited_edges tracks which edges have been used on the current path(this is used to prevent reusing an edge and inflating length via cycles or zigzags)
            """
            max_length = 0
            
            for neighbor in road_graph.get(vertex, []):
                # here we are checking if we can traverse the edge we're on right now
                edge_key = tuple(sorted([vertex, neighbor])) #we sort them so (a,b) is the same as (b,a)
                
                if edge_key not in visited_edges: #only proceed if thee edge has not already been visited
                    # Here we Check if there is a neighbour vertex that blocks the path
                    neighbor_vertex = self.board.vertices[neighbor]
                    if neighbor_vertex.owner is not None and neighbor_vertex.owner != player_id:
                        continue  # If this is the case we can't continue counting through opponent's settlement
                    
                    # Marking edge as visited and using recursion to go through the entire length
                    visited_edges.add(edge_key)
                    length = 1 + dfs(neighbor, visited_edges)
                    max_length = max(max_length, length)
                    visited_edges.remove(edge_key)
            
            return max_length
        
        # Try starting from each vertex in the road network
        longest = 0
        for start_vertex in road_graph.keys():
            # Check if this vertex blocks us (opponent's settlement)
            vertex = self.board.vertices[start_vertex]
            if vertex.owner is not None and vertex.owner != player_id:
                continue
            
            length = dfs(start_vertex, set())
            longest = max(longest, length)
        
        return longest
def update_longest_road(self)-> bool:
    """
    This method serves to calculate the longest road for all players and award the longeest road bonus.
    Returns True if longest road holder changed.
    """
    #Calculate longest road for each player
    road_lengths= {}
    for player in self.players:
        road_lengths[player.id]=self.calculate_longest_road_for_player(player.id)

    max_length = max(road_lengths.values())
    if max_length<5: #in this case no one has the longest path according to the rules
        changed = False
        for player in self.players:
            if player.has_longest_road:
                player.has_longest_road=False
                player.victory_points -=2
                changed = True
        return changed
    #here you find all the players with the max length
    longest_players= [playerid for playerid, length in road_lengths.items() if length == max_length]

    #If there is a tie, the current holder keeps the title
    current_holder = None
    for player in self.players:
        if player.has_longest_road:
            current_holder= player.id
            break
    changed = False

    if len(longest_players)==1:
        #this means only one person can have the victory points for longest road
        winner_id= longest_players[0]

        #if a different player has the title, remove it
        if current_holder is not None and current_holder != winner_id:
            self.players[current_holder].has_longest_road = False
            self.players[current_holder].victory_points-=2
            changed = True
        #gice the points to the winner
        if not self.players[winner_id].has_longest_road:
            self.players[winner_id].has_longest_road = True
            self.players[winner_id].victory_points+=2
            changed = True
            
    else:
        #if tie current holder keeps it
        if current_holder is not None and current_holder not in longest_players:
            self.players[current_holder].has_longest_road = False
            self.players[current_holder].victory_points -=2
            changed = True
    return changed

def count_victory_points(self, player_id: int)-> int:
    """
    Counting the total victory points for a player
    returns the total VP for the player"""

    player = self.players[player_id]

    vp=0

    #counting the number of settlements, each one sums 1 vp.
    settlements= sum (1 for v in self.board.vertices.values() if v.owner == player_id and not v.is_city)
    vp+=settlements

    #doing the same for cities(count 2 vp each)
    cities= sum (1 for v in self.board.vertices.values() if v.owner == player_id and v.is_city)
    vp+=cities*2

    #now we add the longest road bonus if the player has the longest road
    if player.has_longest_road:
        vp +=2
        
    return vp

def check_win_conditions(self)-> tuple[bool, Optional[int]]:
    """Checks if any player reached 10 VP
    
    If so, returns a boolean and the id of the winner(if there is one)"""

    for player in self.players:
        vp= self.count_victory_points(player.id)
        if vp>=10:
            return True, player.id
    return False, None






def end_of_turn_check(self)-> Optional[int]:
    """
    This performs all end of turn calculations.
    This needs to be called after each player's turn.
    
    returns winner id if someone won, else non"""

    #1 longest road update
    road_changed = self.update_longest_road()
    if road_changed:
        print("Longest road holder changed!")
        for player in self.players:
            if player.has_longest_road:
                print(f"  {player.name} has the longest road")
    #2 victory points
    print("\nVictory Points:")
    for player in self.players:
        vp = self.count_victory_points(player.id)
        player.victory_points = vp  # Update stored VP
        print(f"  {player.name}: {vp} VP")
    # 3 Check win condition
    has_winner, winner_id = self.check_win_condition()
    if has_winner:
        winner = self.players[winner_id]
        print(f" {winner.name} wins with {winner.victory_points} victory points")
        self.current_phase = GamePhase.GAME_OVER
        return winner_id
    return None
