"""
Tkinter UI to play the ColabCatan prototype without dealing with raw CLI prompts.

Launch with:
    python -m ui.game_ui
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from dataclasses import dataclass
from typing import List, Optional

from ColabCatan.model.game import GameSetup, GamePhase
from ColabCatan.ui.board_canvas import HexBoardCanvas


MAX_PLAYERS = 4
MIN_PLAYERS = 3


@dataclass
class PlayerRow:
    """Keeps references to the widgets for a player setup row."""

    name_var: tk.StringVar
    cpu_var: tk.BooleanVar
    colour_var: tk.StringVar
    name_entry: tk.Entry
    cpu_check: tk.Checkbutton
    colour_entry: tk.Entry


class GameUI:
    """Simple Tkinter UI around the existing GameSetup engine."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("ColabCatan UI")
        self.root.geometry("900x650")

        # Core engine objects
        self.setup: GameSetup | None = None
        self.game = None

        # Tracking initial placement workflow
        self.placements_remaining = 0
        self.total_players = MIN_PLAYERS

        # Frames
        self.setup_frame = None
        self.placement_frame = None
        self.main_frame = None

        # Widgets reused later
        self.placement_player_label = None
        self.placement_round_label = None
        self.placement_vertex_entry = None
        self.placement_edge_entry = None

        self.current_player_label = None
        self.phase_label = None
        self.resources_text = None
        self.log_widget = None
        self.edge_entry = None
        self.vertex_entry = None
        self.last_roll_label = None
        self.player_color_label = None
        self.board_canvas: Optional[HexBoardCanvas] = None
        self.placement_board_canvas: Optional[HexBoardCanvas] = None

        self.player_rows: List[PlayerRow] = []

        self._build_setup_frame()

    # ---------- Frame builders ----------
    def _clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        # Remove references to destroyed canvases so we don't try to redraw them.
        self.board_canvas = None
        self.placement_board_canvas = None
        self.last_roll_label = None
        self.player_color_label = None

    def _build_setup_frame(self) -> None:
        self._clear_root()
        self.setup_frame = tk.Frame(self.root, padx=20, pady=20)
        self.setup_frame.pack(fill="both", expand=True)

        title = tk.Label(
            self.setup_frame,
            text="ColabCatan Setup",
            font=("Helvetica", 20, "bold"),
        )
        title.pack(pady=(0, 20))

        control_frame = tk.Frame(self.setup_frame)
        control_frame.pack(pady=(0, 15))
        tk.Label(control_frame, text="Number of players (3-4):").grid(
            row=0, column=0, sticky="w"
        )
        self.player_count_var = tk.IntVar(value=MIN_PLAYERS)
        tk.Spinbox(
            control_frame,
            from_=MIN_PLAYERS,
            to=MAX_PLAYERS,
            textvariable=self.player_count_var,
            width=5,
        ).grid(row=0, column=1, padx=10)

        self.player_rows = []
        players_frame = tk.Frame(self.setup_frame)
        players_frame.pack(fill="x")

        tk.Label(players_frame, text="Name").grid(row=0, column=0, sticky="w", padx=5)
        tk.Label(players_frame, text="Is CPU?").grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(players_frame, text="Colour").grid(row=0, column=2, sticky="w", padx=5)

        default_colours = ["red", "blue", "white", "orange"]

        for i in range(MAX_PLAYERS):
            name_var = tk.StringVar(value=f"Player {i+1}")
            cpu_var = tk.BooleanVar(value=False)
            colour_var = tk.StringVar(
                value=default_colours[i] if i < len(default_colours) else ""
            )

            name_entry = tk.Entry(players_frame, textvariable=name_var, width=20)
            name_entry.grid(row=i + 1, column=0, pady=5, padx=5)
            cpu_check = tk.Checkbutton(players_frame, variable=cpu_var)
            cpu_check.grid(row=i + 1, column=1, padx=5)
            colour_entry = tk.Entry(players_frame, textvariable=colour_var, width=15)
            colour_entry.grid(row=i + 1, column=2, padx=5)

            self.player_rows.append(
                PlayerRow(
                    name_var=name_var,
                    cpu_var=cpu_var,
                    colour_var=colour_var,
                    name_entry=name_entry,
                    cpu_check=cpu_check,
                    colour_entry=colour_entry,
                )
            )

        tk.Button(
            self.setup_frame,
            text="Start Game",
            font=("Helvetica", 14, "bold"),
            command=self.start_game,
        ).pack(pady=15)

    def _build_placement_frame(self) -> None:
        self._clear_root()
        self.placement_frame = tk.Frame(self.root, padx=20, pady=20)
        self.placement_frame.pack(fill="both", expand=True)

        tk.Label(
            self.placement_frame, text="Initial Placements", font=("Helvetica", 20, "bold")
        ).pack(pady=(0, 15))

        self.placement_round_label = tk.Label(self.placement_frame, text="")
        self.placement_round_label.pack(pady=(0, 10))

        self.placement_player_label = tk.Label(
            self.placement_frame, text="", font=("Helvetica", 16, "bold")
        )
        self.placement_player_label.pack(pady=(0, 10))

        form_frame = tk.Frame(self.placement_frame)
        form_frame.pack(pady=10)

        tk.Label(form_frame, text="Settlement Vertex ID:").grid(
            row=0, column=0, sticky="e", padx=5, pady=5
        )
        self.placement_vertex_entry = tk.Entry(form_frame, width=20)
        self.placement_vertex_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Road Edge ID:").grid(
            row=1, column=0, sticky="e", padx=5, pady=5
        )
        self.placement_edge_entry = tk.Entry(form_frame, width=20)
        self.placement_edge_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Button(
            self.placement_frame,
            text="Place Settlement + Road",
            command=self.handle_initial_placement,
        ).pack(pady=10)

        self.log_widget = tk.Text(self.placement_frame, height=6, state="disabled")
        self.log_widget.pack(fill="x", pady=10)

        self.placement_board_canvas = HexBoardCanvas(self.placement_frame, self._get_game)
        self.placement_board_canvas.pack(fill="both", expand=True)

        self._update_placement_labels()
        self._refresh_board_views()

    def _build_main_game_frame(self) -> None:
        self._clear_root()
        self.main_frame = tk.Frame(self.root, padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        header = tk.Label(
            self.main_frame, text="ColabCatan Main Game", font=("Helvetica", 20, "bold")
        )
        header.pack(pady=(0, 15))

        info_frame = tk.Frame(self.main_frame)
        info_frame.pack(fill="x", pady=(0, 15))

        self.current_player_label = tk.Label(info_frame, text="Current Player: -")
        self.current_player_label.pack(side="left", padx=5)

        self.phase_label = tk.Label(info_frame, text="Phase: MAIN_GAME")
        self.phase_label.pack(side="left", padx=20)

        tk.Button(
            info_frame,
            text="Run CPU Turn",
            command=self.handle_cpu_turn,
        ).pack(side="right")

        self.board_canvas = HexBoardCanvas(self.main_frame, self._get_game)
        self.board_canvas.pack(fill="both", expand=True, pady=(0, 15))

        action_frame = tk.Frame(self.main_frame)
        action_frame.pack(fill="x", pady=(0, 15))

        self.last_roll_label = tk.Label(
            action_frame,
            text="Last Roll: -",
            font=("Helvetica", 12, "bold"),
            fg="#212121",
            bg=self.main_frame.cget("bg"),
        )
        self.last_roll_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        tk.Button(action_frame, text="Roll Dice", command=self.roll_dice).grid(
            row=0, column=1, padx=5, pady=5
        )

        tk.Label(action_frame, text="Edge ID:").grid(row=0, column=2, sticky="e")
        self.edge_entry = tk.Entry(action_frame, width=10)
        self.edge_entry.grid(row=0, column=3, padx=5)

        tk.Button(
            action_frame, text="Build Road", command=self.build_road
        ).grid(row=0, column=4, padx=5)

        tk.Label(action_frame, text="Vertex ID:").grid(row=1, column=2, sticky="e")
        self.vertex_entry = tk.Entry(action_frame, width=10)
        self.vertex_entry.grid(row=1, column=3, padx=5)

        tk.Button(
            action_frame, text="Build Settlement", command=self.build_settlement
        ).grid(row=1, column=4, padx=5)

        tk.Button(
            action_frame, text="Upgrade to City", command=self.upgrade_city
        ).grid(row=1, column=5, padx=5)

        tk.Button(action_frame, text="Pass Turn", command=self.pass_turn).grid(
            row=0, column=5, padx=5
        )

        cost_frame = tk.LabelFrame(self.main_frame, text="Build Costs")
        cost_frame.pack(fill="x", pady=(0, 10))
        cost_text = (
            "Road: 1 Lumber, 1 Brick    "
            "Settlement: 1 Lumber, 1 Brick, 1 Grain, 1 Wool    "
            "City: 2 Grain, 3 Ore"
        )
        tk.Label(cost_frame, text=cost_text, anchor="w").pack(fill="x", padx=10, pady=3)

        color_frame = tk.LabelFrame(self.main_frame, text="Player Colours")
        color_frame.pack(fill="x", pady=(0, 10))
        self.player_color_label = tk.Label(color_frame, anchor="w")
        self.player_color_label.pack(fill="x", padx=10, pady=3)

        resources_frame = tk.LabelFrame(self.main_frame, text="Player Resources")
        resources_frame.pack(fill="x", pady=(0, 15))
        self.resources_text = tk.Text(resources_frame, height=6, state="disabled")
        self.resources_text.pack(fill="x")

        log_frame = tk.LabelFrame(self.main_frame, text="Game Log")
        log_frame.pack(fill="both", expand=True)
        self.log_widget = tk.Text(log_frame, state="disabled")
        self.log_widget.pack(fill="both", expand=True)

        self._update_game_state_labels()
        self._refresh_board_views()
        self._update_player_color_key()

    # ---------- Setup helpers ----------
    def start_game(self) -> None:
        num_players = self.player_count_var.get()
        if num_players not in (MIN_PLAYERS, MAX_PLAYERS):
            messagebox.showerror("Invalid player count", "Choose 3 or 4 players.")
            return

        player_names: List[str] = []
        player_colours: List[str] = []
        cpu_flags: List[bool] = []

        for idx in range(num_players):
            row = self.player_rows[idx]
            name = row.name_var.get().strip()
            colour = row.colour_var.get().strip().lower()
            if not name:
                messagebox.showerror("Invalid data", f"Player {idx+1} name is empty.")
                return
            if not colour:
                messagebox.showerror("Invalid data", f"Player {idx+1} colour is empty.")
                return
            if colour in player_colours:
                messagebox.showerror("Invalid data", "Colours must be unique.")
                return
            player_names.append(name)
            player_colours.append(colour)
            cpu_flags.append(bool(row.cpu_var.get()))

        self.setup = GameSetup()
        self.game = self.setup.create_game(player_names, player_colours, cpu_flags)
        order = self.setup.determine_turn_order()
        order_summary = "Turn order: " + ", ".join(f"{name} ({roll})" for name, roll in order)
        self.total_players = num_players
        self.placements_remaining = num_players * 2

        self._build_placement_frame()
        self.log_text(order_summary)

    def handle_initial_placement(self) -> None:
        if not self.setup or not self.game:
            messagebox.showerror("Error", "Game not created.")
            return

        vertex = self.placement_vertex_entry.get().strip()
        edge_raw = self.placement_edge_entry.get().strip()
        if not vertex or not edge_raw:
            messagebox.showerror("Error", "Enter both vertex and edge IDs.")
            return
        try:
            edge_id = int(edge_raw)
        except ValueError:
            messagebox.showerror("Error", "Edge ID must be an integer.")
            return

        player = self.game.get_current_player()
        success = self.setup.complete_initial_placement(vertex, edge_id)
        if not success:
            messagebox.showerror(
                "Invalid placement", "Could not place here. Check the rules and try again."
            )
            return

        self.placements_remaining -= 1
        self.log_text(f"{player.name} placed settlement at {vertex} / road {edge_id}")

        self.placement_vertex_entry.delete(0, tk.END)
        self.placement_edge_entry.delete(0, tk.END)

        if self.placements_remaining <= 0:
            self.setup.distribute_initial_resources()
            messagebox.showinfo("Setup complete", "Initial placements done. Starting main game.")
            self._build_main_game_frame()
            return

        self._update_placement_labels()
        self._refresh_board_views()

    def _update_placement_labels(self) -> None:
        if not self.game:
            return
        phase = self.game.current_phase
        if phase == GamePhase.FIRST_SETTLEMENT_ROUND:
            round_text = "First Round (forward order)"
        else:
            round_text = "Second Round (reverse order)"

        self.placement_round_label.configure(text=round_text)
        current_player = self.game.get_current_player()
        self.placement_player_label.configure(
            text=f"{current_player.name}'s placement (colour: {current_player.colour})"
        )

    # ---------- Main game actions ----------
    def roll_dice(self) -> None:
        if not self.setup or not self.game:
            return
        player = self.game.get_current_player()
        events = self.setup._execute_dice_phase(player)  # type: ignore[attr-defined]
        roll = events["roll"]
        self.log_text(f"{player.name} rolled {roll}")
        if self.last_roll_label:
            self.last_roll_label.config(text=f"Last Roll: {roll}")

        if roll == 7:
            discards = events.get("discards", {})
            if discards:
                for pid, removed in discards.items():
                    victim = self.game.players[int(pid)]
                    self.log_text(f"{victim.name} discarded {removed}")
            robber = events.get("robber", {})
            if robber:
                self.log_text(f"Robber moved to tile {robber.get('moved_to')}")
            steal = events.get("steal", {})
            if steal and steal.get("from") is not None:
                victim = self.game.players[int(steal["from"])]
                res = steal.get("resource")
                self.log_text(f"{player.name} stole 1 {res} from {victim.name}")
        else:
            gains = events.get("gains", {})
            if not gains:
                self.log_text("No resources produced.")
            else:
                for pid, resources in gains.items():
                    target = self.game.players[int(pid)]
                    parts = ", ".join(f"{amt} {res}" for res, amt in resources.items())
                    self.log_text(f"{target.name} gains {parts}")

        self._update_game_state_labels()
        self._refresh_board_views()

    def build_road(self) -> None:
        if not self.setup or not self.game:
            return
        player = self.game.get_current_player()
        edge_raw = self.edge_entry.get().strip()
        if not edge_raw:
            messagebox.showerror("Error", "Enter an edge ID.")
            return
        try:
            edge_id = int(edge_raw)
        except ValueError:
            messagebox.showerror("Error", "Edge ID must be an integer.")
            return

        success, msg = self.setup.building_service.build_road(player.id, edge_id)  # type: ignore[union-attr]
        self.log_text(msg)
        if success:
            self.edge_entry.delete(0, tk.END)
            self._check_victory(player)
        self._update_game_state_labels()
        self._refresh_board_views()

    def build_settlement(self) -> None:
        if not self.setup or not self.game:
            return
        player = self.game.get_current_player()
        vertex = self.vertex_entry.get().strip()
        if not vertex:
            messagebox.showerror("Error", "Enter a vertex ID.")
            return
        success, msg = self.setup.building_service.build_settlement(player.id, vertex)  # type: ignore[union-attr]
        self.log_text(msg)
        if success:
            self.vertex_entry.delete(0, tk.END)
            self._check_victory(player)
        self._update_game_state_labels()
        self._refresh_board_views()

    def upgrade_city(self) -> None:
        if not self.setup or not self.game:
            return
        player = self.game.get_current_player()
        vertex = self.vertex_entry.get().strip()
        if not vertex:
            messagebox.showerror("Error", "Enter a vertex ID.")
            return
        success, msg = self.setup.building_service.upgrade_to_city(player.id, vertex)  # type: ignore[union-attr]
        self.log_text(msg)
        if success:
            self.vertex_entry.delete(0, tk.END)
            self._check_victory(player)
        self._update_game_state_labels()
        self._refresh_board_views()

    def pass_turn(self) -> None:
        if not self.game:
            return
        self.game.next_turn()
        self._update_game_state_labels()
        self._refresh_board_views()

    def handle_cpu_turn(self) -> None:
        if not self.setup or not self.game:
            return
        player = self.game.get_current_player()
        if not player.is_cpu:
            messagebox.showinfo("Info", "Current player is not a CPU.")
            return
        self.setup._run_cpu_turn(player)  # type: ignore[attr-defined]
        self.log_text(f"CPU {player.name} completed its turn.")
        self._check_victory(player)
        self.game.next_turn()
        self._update_game_state_labels()
        self._refresh_board_views()

    # ---------- Helpers ----------
    def _check_victory(self, player) -> None:
        if player.victory_points >= 10:
            messagebox.showinfo("Victory!", f"{player.name} wins the game!")

    def _update_game_state_labels(self) -> None:
        if not self.game:
            return
        player = self.game.get_current_player()
        self.current_player_label.configure(
            text=f"Current Player: {player.name} ({'CPU' if player.is_cpu else 'Human'})"
        )
        self.phase_label.configure(text=f"Phase: {self.game.current_phase.name}")

        resources_lines = []
        for pl in self.game.players:
            parts = ", ".join(f"{res.name}: {amt}" for res, amt in pl.resources.items())
            resources_lines.append(f"{pl.name} - VP {pl.victory_points} :: {parts}")

        if self.resources_text:
            self.resources_text.configure(state="normal")
            self.resources_text.delete("1.0", tk.END)
            self.resources_text.insert("1.0", "\n".join(resources_lines))
            self.resources_text.configure(state="disabled")
        self._update_player_color_key()
        self._refresh_board_views()

    def log_text(self, msg: str) -> None:
        if not self.log_widget:
            return
        self.log_widget.configure(state="normal")
        self.log_widget.insert(tk.END, msg + "\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state="disabled")

    def _refresh_board_views(self) -> None:
        for canvas in (self.placement_board_canvas, self.board_canvas):
            if not canvas:
                continue
            try:
                if canvas.winfo_exists():
                    canvas.redraw()
            except tk.TclError:
                continue

    def _get_game(self):
        return self.game

    def _update_player_color_key(self) -> None:
        if not self.player_color_label or not self.game:
            return
        entries = [f"{player.name}: {player.colour.title()}" for player in self.game.players]
        self.player_color_label.config(text="    ".join(entries))

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    GameUI().run()


