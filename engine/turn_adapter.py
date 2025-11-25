from __future__ import annotations

from collections import Counter
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from model.enums import Resource

if TYPE_CHECKING:  # pragma: no cover - type-checking only
    from model.game import GameState, Player

from .turn_engine import (
    BoardSnapshot,
    PlayerView,
    TileView,
    TurnEngine,
    default_choose_discard,
    default_choose_steal_resource,
    default_choose_victim,
)

RESOURCE_TO_STR: Dict[Resource, str] = {
    Resource.BRICK: "brick",
    Resource.LUMBER: "wood",
    Resource.WOOL: "sheep",
    Resource.GRAIN: "wheat",
    Resource.ORE: "ore",
}

STR_TO_RESOURCE: Dict[str, Resource] = {v: k for k, v in RESOURCE_TO_STR.items()}


class TurnEngineAdapter:
    """
    Bridges the core GameState (BoardGraph, Player objects) with the modular TurnEngine.
    Rebuilds snapshots on demand so the engine stays decoupled from internal structures.
    """

    def __init__(self, game_state: "GameState"):
        self.game_state = game_state

    def run_dice_phase(self, current_player_id: int, roll: Optional[int] = None) -> Dict[str, object]:
        players, baselines = self._build_player_views()
        board = self._build_board_snapshot()
        engine = TurnEngine(
            players=players,
            board=board,
            choose_robber_target=self._choose_robber_target,
            choose_robber_victim=default_choose_victim,
            choose_discard=default_choose_discard,
            choose_steal=default_choose_steal_resource,
        )
        events = engine.dice_phase(str(current_player_id), roll=roll)
        self._sync_player_resources(players, baselines)
        self.game_state.robber_hex_id = board.robber_tile_id or self.game_state.robber_hex_id
        return events

    def _build_player_views(self) -> Tuple[Dict[str, PlayerView], Dict[str, Counter]]:
        players: Dict[str, PlayerView] = {}
        baselines: Dict[str, Counter] = {}

        for player in self.game_state.players:
            resources = Counter()
            for res_enum, amount in player.resources.items():
                if res_enum == Resource.DESERT:
                    continue
                resources[RESOURCE_TO_STR[res_enum]] = amount

            view = PlayerView(player_id=str(player.id), name=player.name, resources=resources)
            players[view.player_id] = view
            baselines[view.player_id] = resources.copy()

        return players, baselines

    def _build_board_snapshot(self) -> BoardSnapshot:
        tiles: Dict[int, TileView] = {}
        vertex_owners: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

        hex_to_vertices: Dict[int, list[str]] = {hid: [] for hid in self.game_state.board.hexes}
        for vertex_id, vertex in self.game_state.board.vertices.items():
            for hid in vertex.hex_ids:
                hex_to_vertices[hid].append(vertex_id)

        for hex_id, hex_tile in self.game_state.board.hexes.items():
            resource = RESOURCE_TO_STR.get(hex_tile.resource, None) if hex_tile.resource else None
            tiles[hex_id] = TileView(
                tile_id=hex_id,
                number=hex_tile.number or 0,
                resource=resource,
                vertices=tuple(hex_to_vertices[hex_id]),
                has_robber=(self.game_state.robber_hex_id == hex_id),
            )

        for vertex_id, vertex in self.game_state.board.vertices.items():
            if vertex.owner is None:
                vertex_owners[vertex_id] = (None, None)
                continue
            structure = "city" if vertex.is_city else "settlement"
            vertex_owners[vertex_id] = (str(vertex.owner), structure)

        return BoardSnapshot(
            tiles=tiles,
            vertex_owners=vertex_owners,
            robber_tile_id=self.game_state.robber_hex_id,
        )

    def _sync_player_resources(self, players: Dict[str, PlayerView], baselines: Dict[str, Counter]) -> None:
        for pid, view in players.items():
            baseline = baselines[pid]
            player = self._get_player_by_id(int(pid))
            for res_name, new_amount in view.resources.items():
                old_amount = baseline.get(res_name, 0)
                delta = new_amount - old_amount
                if delta == 0:
                    continue
                res_enum = STR_TO_RESOURCE[res_name]
                player.resources[res_enum] += delta

            # Handle resources that were removed entirely (e.g., discard)
            for res_name in list(baseline.keys()):
                if res_name not in view.resources:
                    res_enum = STR_TO_RESOURCE[res_name]
                    player.resources[res_enum] = max(
                        0, player.resources[res_enum] - baseline[res_name]
                    )

    def _choose_robber_target(self, board: BoardSnapshot, current_player_id: str) -> int:
        """
        Extremely simple heuristic: move robber to the first tile that has enemies and a number token.
        Falls back to current robber tile.
        """
        for tile in board.tiles.values():
            if tile.tile_id == board.robber_tile_id or tile.resource is None:
                continue
            for vertex in tile.vertices:
                owner, _ = board.vertex_owners.get(vertex, (None, None))
                if owner and owner != current_player_id:
                    return tile.tile_id
        return board.robber_tile_id or next(iter(board.tiles))

    def _get_player_by_id(self, player_id: int):
        return self.game_state.players[player_id]


__all__ = ["TurnEngineAdapter"]

