"""
Reusable Tkinter canvas that renders the Catan board state (hexes, roads, settlements).
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Callable, Dict, List, Optional, Tuple

from ColabCatan.model.board import HEX_LAYOUT
from ColabCatan.model.enums import Resource


# Axial coordinates to lay out the 19 hexes in a standard shape
HEX_AXIAL_POSITIONS: Dict[int, Tuple[int, int]] = {
    0: (0, -2),
    1: (1, -2),
    2: (2, -2),
    3: (-1, -1),
    4: (0, -1),
    5: (1, -1),
    6: (2, -1),
    7: (-2, 0),
    8: (-1, 0),
    9: (0, 0),
    10: (1, 0),
    11: (2, 0),
    12: (-2, 1),
    13: (-1, 1),
    14: (0, 1),
    15: (1, 1),
    16: (-2, 2),
    17: (-1, 2),
    18: (0, 2),
}

RESOURCE_COLOURS = {
    Resource.BRICK: "#ff8a65",
    Resource.LUMBER: "#4caf50",
    Resource.ORE: "#b0bec5",
    Resource.GRAIN: "#ffd54f",
    Resource.WOOL: "#8bc34a",
    Resource.DESERT: "#e0c08d",
    None: "#cfd8dc",
}


class HexBoardCanvas(tk.Frame):
    """Canvas widget that draws the board using data from GameState."""

    def __init__(
        self,
        master: tk.Misc,
        game_getter: Callable[[], Optional["GameState"]],
        *,
        width: int = 900,
        height: int = 600,
        hex_size: int = 45,
    ) -> None:
        super().__init__(master, padx=5, pady=5)
        self.game_getter = game_getter
        self.hex_size = hex_size
        self.canvas = tk.Canvas(self, width=width, height=height, bg="#0d1117", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.offset_x = width // 2
        self.offset_y = height // 2
        self.hex_centers = self._compute_hex_centers()
        self.hex_polygons = {
            hid: self._hex_polygon_points(center)
            for hid, center in self.hex_centers.items()
        }
        self.vertex_positions: Dict[str, Tuple[float, float]] = {}

    # ------------------------------------------------------------------ helpers
    def _compute_hex_centers(self) -> Dict[int, Tuple[float, float]]:
        centres: Dict[int, Tuple[float, float]] = {}
        for hex_id, (q, r) in HEX_AXIAL_POSITIONS.items():
            # Standard pointy-top axial -> pixel conversion so neighbouring
            # hexes share edges without gaps.
            x = self.hex_size * math.sqrt(3) * (q + r / 2)
            y = self.hex_size * 1.5 * r
            centres[hex_id] = (x + self.offset_x, y + self.offset_y)
        return centres

    def _hex_polygon_points(self, center: Tuple[float, float]) -> List[float]:
        cx, cy = center
        points: List[float] = []
        for i in range(6):
            angle = math.radians(60 * i - 30)  # pointy-top hex
            x = cx + self.hex_size * math.cos(angle)
            y = cy + self.hex_size * math.sin(angle)
            points.extend([x, y])
        return points

    def _resource_colour(self, resource: Optional[Resource]) -> str:
        return RESOURCE_COLOURS.get(resource, RESOURCE_COLOURS[None])

    def _calculate_vertex_positions(self, board) -> Dict[str, Tuple[float, float]]:
        raw_points: Dict[str, List[Tuple[float, float]]] = {}
        for hex_id, vertex_ids in HEX_LAYOUT.items():
            polygon = self.hex_polygons.get(hex_id)
            if not polygon:
                continue
            corners = [(polygon[i], polygon[i + 1]) for i in range(0, len(polygon), 2)]
            for vid, point in zip(vertex_ids, corners):
                raw_points.setdefault(vid, []).append(point)

        final_positions: Dict[str, Tuple[float, float]] = {}
        for vid, points in raw_points.items():
            if not points:
                final_positions[vid] = (0.0, 0.0)
                continue
            x = sum(p[0] for p in points) / len(points)
            y = sum(p[1] for p in points) / len(points)
            final_positions[vid] = (x, y)

        # Some graph-only vertices (ports) might not appear in HEX_LAYOUT.
        for vid, vertex in board.vertices.items():
            if vid in final_positions:
                continue
            coords = []
            for edge_id in vertex.edge_ids:
                edge = board.edges.get(edge_id)
                if not edge:
                    continue
                other_vid = edge.v1 if edge.v2 == vid else edge.v2
                if other_vid in final_positions:
                    coords.append(final_positions[other_vid])
            if coords:
                x = sum(p[0] for p in coords) / len(coords)
                y = sum(p[1] for p in coords) / len(coords)
                final_positions[vid] = (x, y)
        return final_positions

    # ------------------------------------------------------------------ drawing
    def redraw(self) -> None:
        game = self.game_getter()
        self.canvas.delete("all")
        if not game:
            return

        board = game.board
        self.vertex_positions = self._calculate_vertex_positions(board)
        self._draw_hexes(board, getattr(game, "robber_hex_id", None))
        self._draw_edge_network(board)
        self._draw_roads(board, game.players)
        self._draw_settlements(board, game.players)
        self._draw_vertex_ids()

    def _draw_hexes(self, board, robber_hex_id: Optional[int]) -> None:
        for hex_id, polygon in self.hex_polygons.items():
            tile = board.hexes.get(hex_id)
            fill = self._resource_colour(tile.resource if tile else None)
            outline = "#f44336" if robber_hex_id == hex_id else "#37474f"

            self.canvas.create_polygon(
                polygon,
                fill=fill,
                outline="#90a4ae" if robber_hex_id != hex_id else "#f44336",
                width=3 if robber_hex_id == hex_id else 2,
            )

            if tile:
                cx, cy = self.hex_centers[hex_id]
                name = tile.resource.name.title() if tile.resource else "Desert"
                self.canvas.create_text(
                    cx,
                    cy - 10,
                    text=name,
                    fill="#212121",
                    font=("Helvetica", 10, "bold"),
                )
                if tile.number is not None:
                    self.canvas.create_text(
                        cx,
                        cy + 8,
                        text=str(tile.number),
                        fill="#212121",
                        font=("Helvetica", 12, "bold"),
                    )

    def _draw_edge_network(self, board) -> None:
        """Render all edges so players can see IDs even if no road is built."""
        for edge in board.edges.values():
            start = self.vertex_positions.get(edge.v1)
            end = self.vertex_positions.get(edge.v2)
            if not start or not end:
                continue
            self.canvas.create_line(
                start[0],
                start[1],
                end[0],
                end[1],
                fill="#90a4ae",
                width=2,
                dash=(4, 2),
            )
            mx = (start[0] + end[0]) / 2
            my = (start[1] + end[1]) / 2
            self.canvas.create_text(
                mx,
                my,
                text=str(edge.id),
                fill="#cfd8dc",
                font=("Helvetica", 8, "bold"),
            )

    def _brighten(self, colour: str, factor: float = 0.35) -> str:
        """Return a lighter shade of the provided colour."""
        try:
            colour = colour.lstrip("#")
            r = int(colour[0:2], 16)
            g = int(colour[2:4], 16)
            b = int(colour[4:6], 16)
        except Exception:
            return colour
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw_roads(self, board, players) -> None:
        for edge in board.edges.values():
            if edge.owner is None:
                continue
            start = self.vertex_positions.get(edge.v1)
            end = self.vertex_positions.get(edge.v2)
            if not start or not end:
                continue
            base_colour = players[edge.owner].colour if edge.owner < len(players) else "#ffffff"
            colour = self._brighten(base_colour)
            self.canvas.create_line(
                start[0],
                start[1],
                end[0],
                end[1],
                fill=colour,
                width=8,
                capstyle=tk.ROUND,
            )

    def _draw_settlements(self, board, players) -> None:
        for vertex in board.vertices.values():
            pos = self.vertex_positions.get(vertex.id)
            if not pos:
                continue
            x, y = pos
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#eceff1", outline="#263238")

            if vertex.owner is None:
                continue

            colour = players[vertex.owner].colour if vertex.owner < len(players) else "#ffffff"
            radius = 12 if vertex.is_city else 8
            self.canvas.create_oval(
                x - radius / 2,
                y - radius / 2,
                x + radius / 2,
                y + radius / 2,
                fill=colour,
                outline="#212121",
                width=2,
            )
            if vertex.is_city:
                self.canvas.create_rectangle(
                    x - radius / 3,
                    y - radius / 3,
                    x + radius / 3,
                    y + radius / 3,
                    fill="#fafafa",
                    outline="#212121",
                    width=1,
                )

    def _draw_vertex_ids(self) -> None:
        for vid, (x, y) in self.vertex_positions.items():
            self.canvas.create_text(
                x,
                y - 12,
                text=vid,
                fill="#f5f5f5",
                font=("Helvetica", 9, "bold"),
            )


