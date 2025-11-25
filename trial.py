"""
Quick start script for testing - uses predefined placements.
Run this to quickly see the game in action.
"""

from .model.game import GameSetup

def quick_game():
    """Start a quick test game with predefined setup."""
    
    setup = GameSetup()
    
    # Create players (2 human, 1 CPU for testing)
    player_names = ["Alice", "Bob", "Charlie"]
    player_colours = ["red", "blue", "white"]
    cpu_flags = [False, False, True]  # Charlie is CPU
    
    print("=== Quick Start Catan ===\n")
    print(f"Players: {', '.join(player_names)}")
    print(f"CPU players: {player_names[2]}\n")
    
    # Predefined placements (you'll need to adjust these based on your board)
    # Format: (vertex_id, edge_id) for each player's first and second settlements
    placements = [
        # First round
        ("A", 0),   # Alice first
        ("C", 5),   # Bob first  
        ("G", 10),  # Charlie first
        # Second round (reverse)
        ("N", 15),  # Charlie second
        ("F", 8),   # Bob second
        ("E", 3),   # Alice second
    ]
    
    # Run full setup
    game = setup.run_full_setup(player_names, player_colours, placements)
    
    # Show initial state
    print("\n=== Initial Resources ===")
    for player in game.players:
        resources = ", ".join([f"{r.name}: {amt}" for r, amt in player.resources.items() if amt > 0])
        print(f"{player.name}: {resources or 'None'}")
    
    # Start main game
    print("\n=== Starting Main Game ===")
    print("Commands: road, settlement, city, pass")
    
    setup.run_main_game_loop(max_turns=50)


if __name__ == "__main__":
    quick_game()