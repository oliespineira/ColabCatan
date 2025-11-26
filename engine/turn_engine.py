from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple
import random

# Basic type aliases
Resource = str  # "wood", "brick", etc.
StructureKind = str  # "settlement" or "city"
PlayerID = str  # player identifier (string to keep adapter flexible)


@dataclass
class PlayerView:
    """Information the turn engine needs about a player."""

    player_id: PlayerID
    name: str
    resources: Counter = field(default_factory=Counter)

    def total_cards(self) -> int:
        """
        Count total resource cards.
        
        Time Complexity: O(k) where k = number of unique resource types (typically 5)
        - Counter iteration: O(k)
        - Space: O(1)
        """
        return sum(self.resources.values())

    def add(self, res: Resource, n: int = 1) -> None:
        if n > 0:
            self.resources[res] += n

    def remove(self, res: Resource, n: int = 1) -> bool:
        if self.resources[res] >= n:
            self.resources[res] -= n
            if self.resources[res] == 0:
                del self.resources[res]
            return True
        return False

    def remove_random_cards(self, n: int) -> Counter:
        """
        Remove n random cards from player's resources.
        
        Time Complexity: O(n * C) where C = total cards
        - Creates weighted pool each iteration: O(C)
        - Random selection: O(1)
        - Worst case: O(n * C) if pool rebuilt each time
        - Space: O(C) for pool creation
        """
        removed = Counter()
        for _ in range(n):
            if not self.resources:
                break
            pool = [r for r, cnt in self.resources.items() for _ in range(cnt)]
            res = random.choice(pool)
            self.remove(res, 1)
            removed[res] += 1
        return removed


@dataclass(frozen=True)
class TileView:
    """Simplified view of a board tile."""

    tile_id: int
    number: int
    resource: Optional[Resource]
    vertices: Tuple[str, ...]
    has_robber: bool = False


VertexOwner = Tuple[Optional[PlayerID], Optional[StructureKind]]


@dataclass
class BoardSnapshot:
    """Compact representation of the board for the turn engine."""

    tiles: Dict[int, TileView]
    vertex_owners: Dict[str, VertexOwner]
    robber_tile_id: Optional[int]


# Callback type aliases
ChooseRobberTarget = Callable[[BoardSnapshot, PlayerID], int]
ChooseRobberVictim = Callable[[Iterable[PlayerView]], Optional[PlayerView]]
ChooseDiscard = Callable[[PlayerView, int], Counter]
ChooseStealResource = Callable[[PlayerView], Optional[Resource]]


def default_choose_discard(player: PlayerView, n: int) -> Counter:
    return player.remove_random_cards(n)


def default_choose_victim(candidates: Iterable[PlayerView]) -> Optional[PlayerView]:
    """
    Random victim selection for robber.
    
    Time Complexity: O(P) where P = number of candidates
    - Linear scan to filter: O(P)
    - Random choice: O(1)
    """
    cands = [p for p in candidates if p.total_cards() > 0]
    return random.choice(cands) if cands else None


def default_choose_steal_resource(victim: PlayerView) -> Optional[Resource]:
    """
    Random resource selection from victim.
    
    Time Complexity: O(C) where C = total cards victim has
    - Creates weighted pool: O(C)
    - Random choice: O(1)
    - Space: O(C) for pool
    """
    if victim.total_cards() == 0:
        return None
    pool = [r for r, cnt in victim.resources.items() for _ in range(cnt)]
    return random.choice(pool) if pool else None


class TurnEngine:
    """Handles the dice + robber portion of a player's turn."""

    def __init__(
        self,
        players: Dict[PlayerID, PlayerView],
        board: BoardSnapshot,
        choose_robber_target: ChooseRobberTarget,
        choose_robber_victim: ChooseRobberVictim = default_choose_victim,
        choose_discard: ChooseDiscard = default_choose_discard,
        choose_steal: ChooseStealResource = default_choose_steal_resource,
    ):
        self.players = players
        self.board = board
        self.choose_robber_target = choose_robber_target
        self.choose_robber_victim = choose_robber_victim
        self.choose_discard = choose_discard
        self.choose_steal = choose_steal

    @staticmethod
    def roll_dice() -> int:
        return random.randint(1, 6) + random.randint(1, 6)

    def distribute_resources(self, roll: int) -> Dict[PlayerID, Counter]:
        """
        Distribute resources to players based on dice roll.
        
        Time Complexity: O(T * V) where T = tiles, V = vertices per tile
        - Iterates through all tiles: O(T)
        - For each tile, checks vertices: O(V) where V ≈ 6 per tile
        - Counter operations: O(1) average
        - Space: O(P * R) where P = players, R = resource types
        """
        gained: Dict[PlayerID, Counter] = defaultdict(Counter)

        for tile in self.board.tiles.values():
            robber_on_tile = tile.has_robber or self.board.robber_tile_id == tile.tile_id
            if tile.number != roll or robber_on_tile or tile.resource is None:
                continue

            for vertex_id in tile.vertices:
                owner, structure = self.board.vertex_owners.get(vertex_id, (None, None))
                if owner is None:
                    continue
                amount = 2 if structure == "city" else 1
                gained[owner][tile.resource] += amount

        for pid, resources in gained.items():
            for res, amount in resources.items():
                self.players[pid].add(res, amount)

        return gained

    def handle_seven(self, current_player_id: PlayerID) -> Dict[str, object]:
        events: Dict[str, object] = {"discards": {}, "robber": {}, "steal": {}}

        for player in self.players.values():
            if player.total_cards() > 7:
                to_discard = player.total_cards() // 2
                removed = self.choose_discard(player, to_discard)
                removed_total = sum(removed.values())
                if removed_total < to_discard:
                    removed += player.remove_random_cards(to_discard - removed_total)
                events["discards"][player.player_id] = dict(removed)

        target_tile_id = self.choose_robber_target(self.board, current_player_id)
        if self.board.robber_tile_id is not None and self.board.robber_tile_id in self.board.tiles:
            old_tile = self.board.tiles[self.board.robber_tile_id]
            self.board.tiles[self.board.robber_tile_id] = TileView(
                old_tile.tile_id,
                old_tile.number,
                old_tile.resource,
                old_tile.vertices,
                has_robber=False,
            )

        new_tile = self.board.tiles[target_tile_id]
        self.board.tiles[target_tile_id] = TileView(
            new_tile.tile_id,
            new_tile.number,
            new_tile.resource,
            new_tile.vertices,
            has_robber=True,
        )
        self.board.robber_tile_id = target_tile_id
        events["robber"] = {"moved_to": target_tile_id}

        adjacent: set[PlayerID] = set()
        for vertex_id in new_tile.vertices:
            owner, _ = self.board.vertex_owners.get(vertex_id, (None, None))
            if owner and owner != current_player_id:
                adjacent.add(owner)

        candidates = [self.players[pid] for pid in adjacent if self.players[pid].total_cards() > 0]
        victim = self.choose_robber_victim(candidates)

        if victim:
            res = self.choose_steal(victim) or random.choice(
                [r for r, cnt in victim.resources.items() for _ in range(cnt)]
            )
            victim.remove(res, 1)
            self.players[current_player_id].add(res, 1)
            events["steal"] = {"from": victim.player_id, "resource": res}
        else:
            events["steal"] = {"from": None, "resource": None}

        return events

    def dice_phase(self, current_player_id: PlayerID, roll: Optional[int] = None) -> Dict[str, object]:
        roll = self.roll_dice() if roll is None else roll
        if roll == 7:
            events = self.handle_seven(current_player_id)
            return {"roll": 7, **events}
        gains = self.distribute_resources(roll)
        return {"roll": roll, "gains": {pid: dict(cnt) for pid, cnt in gains.items()}}


__all__ = [
    "TurnEngine",
    "PlayerView",
    "BoardSnapshot",
    "TileView",
    "ChooseRobberTarget",
    "ChooseRobberVictim",
    "ChooseDiscard",
    "ChooseStealResource",
    "default_choose_discard",
    "default_choose_victim",
    "default_choose_steal_resource",
]