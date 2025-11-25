"""
This is the main entry point for our simplified implementation for settlers of Catan Game.
"""

from model.game import GameSetup

def get_player_setup():
    """This function is used to get the player setup from the user."""
    print("Welcome to the Settlers of Catan Game")
    num_players = 0
    while num_players not in [3, 4]:
        try:
            num_players = int(input("How many players? (3-4): "))
        except ValueError:
            print("Please enter a valid number.")
    
    player_names = []
    player_colours = []
    cpu_players = []
    
    available_colours = ["red", "blue", "white", "orange"]

    for i in range(num_players):#adding the actual players and their details to the game.
        name = input(f"Player {i+1} name: ").strip()
        while not name:
            name = input("Name cannot be empty. Try again: ").strip()
        player_names.append(name)
        
        is_cpu = input(f"Is {name} a CPU player? (y/n): ").lower().strip() == 'y'#adding the cpu player
        cpu_players.append(is_cpu)#adding to the actual list of cpu players
        
        print(f"Available colours: {', '.join(available_colours)}")
        colour = input(f"Choose colour for {name}: ").lower().strip()
        while colour not in available_colours:
            colour = input(f"Invalid. Choose from {available_colours}: ").lower().strip()
        player_colours.append(colour)
        available_colours.remove(colour)
    
    return player_names, player_colours, cpu_players


def get_initial_placements(game_setup):
    """This function is used to get the initial placements from the user."""
    placements= []
    #starting with the first round.
    print("\n First Settlement Round")
    for i in range(len(game_setup.game.players)): #iterate for the amount of players
        player = game_setup.game.get_current_player()
        print(f"\n{player.name}'s turn:")
    if player.is_cpu: #for the cpu player we didnt want to overcomplicate and make our lives more miserable than what they already are the placement will be random
        vertex = input(f"Enter settlement vertexfor CPU {player.name}: ").strip()
        edge = int(input(f"Enter road edge for CPU {player.name}: "))
    else:
        vertex = input("Enter settlement vertex ID: ").strip()
        edge = int(input("Enter road edge ID: "))
    placements.append((vertex, edge))#adding the settlement and roads to the list of placements. This is used so we can check that no other settlement is placed in the same or illegal spot. we hate players and matteo once beat me because he did this illegal move.
    game_setup.game.next_turn()#moving to the next player


#this is literally the same code as above but the other way around.
    print("\n=== Second Settlement Round ===")
    for i in range(len(game_setup.game.players)): #iterate for the amount of players
            player = game_setup.game.get_current_player()
            print(f"\n{player.name}'s turn:")
            
            if player.is_cpu:
                vertex = input(f"Enter settlement vertex for CPU {player.name}: ").strip()
                edge = int(input(f"Enter road edge for CPU {player.name}: "))
            else:
                vertex = input("Enter settlement vertex ID: ").strip()
                edge = int(input("Enter road edge ID: "))
            
            placements.append((vertex, edge))
            game_setup.game.next_turn()
        
    return placements#returns the wonderful list of placements.

def main(): #finally we add this guys, it took effort sweat and tears but we managed
    """Main game loop"""

    player_names, player_colours, cpu_players = get_player_setup()

    #here we create the game
    game_setup = GameSetup()
    game_setup.create_game(player_names, player_colours, cpu_players)

    #once all the players are ready, including christoph trying to understand what is going on, we can determine the turn order.
    print("\n Determining Turn Order")
    order= game_setup.determine_turn_order()
    for name, roll in order:
        print(f"{name} rolled {roll}")
    print(f"\nTurn order: {' -> '.join([p.name for p in game_setup.game.players])}")


    placements = get_initial_placements(game_setup)#getting the initial placement of the settielement

    #here we reset the game state and apply placement parameters
    game_setup.game.current_phase = game_setup.game.current_phase.__class__.FIRST_SETTLEMENT_ROUND
    game_setup.game.current_player_idx = 0

    # Apply placements
    for i, (vertex, edge) in enumerate(placements):
        player = game_setup.game.get_current_player()
        success = game_setup.complete_initial_placement(vertex, edge)
        if not success:
            print(f"Failed to place for {player.name}. Exiting.")
            return
    
    # Distribute initial resources
    game_setup.distribute_initial_resources()
    
    # Start main game
    print("\n Game Start")
    game_setup.run_main_game_loop(max_turns=100)
    
    print("\n Game Over")


if __name__ == "__main__":
    main()

