from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple
import heapq
import math

# External enums expected from model
try:
    from ColabCatan.model.enums import Resource
except Exception:  # Keep module import-safe before model is complete
    # Fallback version of resources just so the CPU code doesn't explode
    class Resource(Enum):  # type: ignore
        BRICK = auto()
        LUMBER = auto()
        ORE = auto()
        GRAIN = auto()
        WOOL = auto()
        DESERT = auto()


class ActionType(Enum):
    """
    All the possible things the CPU can decide to do.
    Pretty much every major move in Catan is listed here.
    """
    BUILD_SETTLEMENT = auto()
    BUILD_ROAD = auto()
    BUILD_CITY = auto()
    BUY_DEV_CARD = auto()
    BANK_TRADE = auto()
    PLAYER_TRADE = auto()  # not implemented here, but listed for completeness
    MOVE_ROBBER = auto()
    PASS = auto()


@dataclass(order=True)
class CPUAction:
    """
    Represents one possible action the CPU might take.
    Each action gets a score, and we use that score to decide what’s “best”.
    
    sort_index:
        heapq only supports min-heaps, so we store negative scores so the
        highest-scoring action comes out first.
    """
    sort_index: float = field(init=False, repr=False)
    score: float  # this will be updated later
    action_type: ActionType = field(compare=False)
    params: Dict[str, Any] = field(default_factory=dict, compare=False)
    explanation: Optional[str] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        # Negative score because heapq pops the smallest element first.
        self.sort_index = -self.score


@dataclass
class CPUWeights:
    """
    These are basically dials we can tweak to change how the AI behaves.
    They influence how much the CPU "cares" about different types of actions.
    """
    # Phase weighting — we scale actions based on the part of the game
    early_weight_settlement: float = 2.0
    early_weight_road: float = 1.2
    mid_weight_city: float = 2.0
    mid_weight_dev: float = 1.4
    late_weight_city: float = 2.2
    late_weight_dev: float = 1.8
    late_weight_blocking: float = 2.3

    # Basic action values — kind of like default attractiveness
    base_value_settlement: float = 8.0
    base_value_road: float = 2.5
    base_value_city: float = 10.0
    base_value_dev: float = 4.0
    base_value_robber_block: float = 3.0

    # Production-based modifiers
    pip_value_per_point: float = 0.6
    resource_diversity_bonus: float = 1.5
    city_on_high_pip_bonus_factor: float = 0.25

    # Points for longest road or largest army progression
    longest_road_push: float = 1.6
    largest_army_push: float = 1.6

    # Trade danger factors — basically: don't help opponents win
    trade_enable_opponent_win_penalty: float = 1000.0
    block_leader_bonus: float = 3.5
    avoid_self_harm_penalty: float = 6.0

    # Trade scoring weights
    bank_trade_progress_weight: float = 3.5
    bank_trade_scarcity_penalty: float = 2.0
    bank_trade_excess_bonus: float = 1.2

    # Passing is usually not great
    pass_small_penalty: float = 0.8


class RulesAdapter(Protocol):
    """
    This is an interface that the actual game engine will implement.
    The CPU doesn’t know anything about the real board — it only talks
    through these methods.

    Basically: this avoids the CPU depending on any specific internal structure.
    """

    # Core lookups
    def current_player_id(self) -> int: ...
    def opponents(self) -> Sequence[int]: ...
    def visible_victory_points(self, player_id: int) -> int: ...
    def estimated_hidden_vp(self, player_id: int) -> float: ...
    def total_victory_points_estimate(self, player_id: int) -> float: ...
    def game_phase(self) -> str: ...  # "early" | "mid" | "late"

    # Resource / cost info
    def player_resources(self, player_id: int) -> Dict[Resource, int]: ...
    def resource_production_profile(self, player_id: int) -> Dict[Resource, float]: ...
    def board_resource_scarcity(self) -> Dict[Resource, float]: ...
    def build_cost_settlement(self) -> Dict[Resource, int]: ...
    def build_cost_road(self) -> Dict[Resource, int]: ...
    def build_cost_city(self) -> Dict[Resource, int]: ...
    def build_cost_dev_card(self) -> Dict[Resource, int]: ...

    # What’s currently legal for the CPU to build
    def legal_settlement_vertices(self, player_id: int) -> Iterable[int]: ...
    def legal_road_edges(self, player_id: int) -> Iterable[int]: ...
    def upgradeable_vertices(self, player_id: int) -> Iterable[int]: ...
    def can_buy_dev_card(self, player_id: int) -> bool: ...
    def bank_trade_options(self, player_id: int) -> Iterable[Tuple[Resource, Resource, int]]: ...
    def robber_move_options(self, player_id: int) -> Iterable[Tuple[int, Optional[int]]]: ...

    # Board scoring things
    def vertex_pip(self, vertex_id: int) -> float: ...
    def vertex_resource_set(self, vertex_id: int) -> Sequence[Resource]: ...
    def road_expands_towards_value(self, edge_id: int) -> float: ...
    def road_contributes_longest(self, player_id: int, edge_id: int) -> float: ...
    def settlement_blocks_opponent_value(self, vertex_id: int) -> float: ...

    # Trade safety check
    def would_trade_enable_opponent_win(
        self,
        target_player_id: int,
        give: Resource,
        get: Resource,
        rate: int
    ) -> bool: ...

    # Optional) if CPU executes the action directly
    def execute(self, action: CPUAction) -> None: ...


class CPUPlayer:
    """
    This is the main AI class. It creates possible actions,
    scores them, and picks whichever one seems best.
    
    Note: This AI is heuristic-based — so it is not perfect, but tries to act smart
    using weighted scoring for each possible move.
    """

    def __init__(self, rules: RulesAdapter, weights: Optional[CPUWeights] = None) -> None:
        self.rules = rules
        self.weights = weights or CPUWeights()

    # Step 1: Generate all possible moves it could do
    def generate_candidate_actions(self) -> List[CPUAction]:
        """
        Generate all possible actions the CPU can take.
        
        Time Complexity: O(A) where A = number of candidate actions
        - Linear scan through legal moves (settlements, roads, cities, trades, etc.)
        - Space: O(A) for action list
        """
        player_id = self.rules.current_player_id()
        actions: List[CPUAction] = []

        # Add every settlement spot the player is allowed to build
        for v in self.rules.legal_settlement_vertices(player_id):
            actions.append(CPUAction(
                score=0.0,
                action_type=ActionType.BUILD_SETTLEMENT,
                params={"vertex_id": v},
                explanation="Build settlement"
            ))

        # Add every place they can build a road in
        for e in self.rules.legal_road_edges(player_id):
            actions.append(CPUAction(
                score=0.0,
                action_type=ActionType.BUILD_ROAD,
                params={"edge_id": e},
                explanation="Build road"
            ))

        # Add every possible settlement→city upgrade
        for v in self.rules.upgradeable_vertices(player_id):
            actions.append(CPUAction(
                score=0.0,
                action_type=ActionType.BUILD_CITY,
                params={"vertex_id": v},
                explanation="Upgrade settlement to city"
            ))

        # Dev card buy is just a yes/no based on resources
        if self.rules.can_buy_dev_card(player_id):
            actions.append(CPUAction(
                score=0.0,
                action_type=ActionType.BUY_DEV_CARD,
                params={},
                explanation="Buy development card"
            ))

        # Add all 4:1 trades (or port trades if the adapter gives them)
        for give, get, rate in self.rules.bank_trade_options(player_id):
            actions.append(CPUAction(
                score=0.0,
                action_type=ActionType.BANK_TRADE,
                params={"give": give, "get": get, "rate": rate},
                explanation=f"Bank trade {rate}:1 {give.name}->{get.name}"
            ))

        # Add all legal robber targets
        for hex_id, steal_from in self.rules.robber_move_options(player_id):
            actions.append(CPUAction(
                score=0.0,
                action_type=ActionType.MOVE_ROBBER,
                params={"hex_id": hex_id, "steal_from": steal_from},
                explanation="Move robber"
            ))

        # Always include “do nothing”
        actions.append(CPUAction(
            score=0.0,
            action_type=ActionType.PASS,
            params={},
            explanation="Pass / save resources"
        ))

        return actions

    # Step 2: Assign a score to each action
    def score_action(self, action: CPUAction) -> float:
        """
        Heuristic scoring algorithm for CPU actions.
        
        Time Complexity: 
        - Average: O(1) for most actions (constant-time scoring)
        - Worst: O(O) for bank trades where O = number of opponents
        - Uses weighted multi-factor scoring system
        """
        phase = self.rules.game_phase()
        player_id = self.rules.current_player_id()
        weights = self.weights

        score = 0.0  # will gradually add to this

        # Helper to scale actions depending on what stage of the game we’re in
        def phase_multiplier_for(action_type: ActionType) -> float:
            if phase == "early":
                if action_type == ActionType.BUILD_SETTLEMENT:
                    return weights.early_weight_settlement
                if action_type == ActionType.BUILD_ROAD:
                    return weights.early_weight_road
            elif phase == "mid":
                if action_type == ActionType.BUILD_CITY:
                    return weights.mid_weight_city
                if action_type == ActionType.BUY_DEV_CARD:
                    return weights.mid_weight_dev
            elif phase == "late":
                if action_type == ActionType.BUILD_CITY:
                    return weights.late_weight_city
                if action_type == ActionType.BUY_DEV_CARD:
                    return weights.late_weight_dev
                # In late game, blocking actions (roads, robber, settlements) matter a lot
                if action_type in (ActionType.MOVE_ROBBER, ActionType.BUILD_ROAD, ActionType.BUILD_SETTLEMENT):
                    return weights.late_weight_blocking
            return 1.0  # default multiplier

        pm = phase_multiplier_for(action.action_type)

        # Scoring logic for each kind of action
        if action.action_type == ActionType.BUILD_SETTLEMENT:
            vertex_id = int(action.params["vertex_id"])
            vertex_pip = self.rules.vertex_pip(vertex_id)
            resources_here = set(self.rules.vertex_resource_set(vertex_id))

            # Growing earlier and increasing production + diversity is valuable
            diversity_bonus = weights.resource_diversity_bonus if len(resources_here) >= 2 else 0.0
            block_bonus = self.rules.settlement_blocks_opponent_value(vertex_id) * weights.block_leader_bonus

            score = (
                weights.base_value_settlement
                + vertex_pip * weights.pip_value_per_point
                + diversity_bonus
                + block_bonus
            ) * pm

        elif action.action_type == ActionType.BUILD_CITY:
            vertex_id = int(action.params["vertex_id"])
            vertex_pip = self.rules.vertex_pip(vertex_id)
            high_pip_bonus = vertex_pip * weights.city_on_high_pip_bonus_factor

            score = (
                weights.base_value_city
                + high_pip_bonus
            ) * pm

        elif action.action_type == ActionType.BUILD_ROAD:
            edge_id = int(action.params["edge_id"])
            towards_value = self.rules.road_expands_towards_value(edge_id)
            longest_pressure = self.rules.road_contributes_longest(player_id, edge_id) * weights.longest_road_push

            score = (
                weights.base_value_road
                + towards_value
                + longest_pressure
            ) * pm

        elif action.action_type == ActionType.BUY_DEV_CARD:
            score = (weights.base_value_dev + weights.largest_army_push) * pm

        elif action.action_type == ActionType.BANK_TRADE:
            give: Resource = action.params["give"]
            get: Resource = action.params["get"]
            rate: int = int(action.params["rate"])

            # First: check whether doing this trade would let someone else win.
            for opp in self.rules.opponents():
                if self.rules.would_trade_enable_opponent_win(opp, give, get, rate):
                    # Huge negative score so the CPU absolutely avoids this
                    return -weights.trade_enable_opponent_win_penalty

            profile = self.rules.resource_production_profile(player_id)
            scarcity = self.rules.board_resource_scarcity()

            # This is a rough guess at how much the player “has too much” of a resource
            excess = max(0.0, profile.get(give, 0.0) - 1.0)
            # And how much they “need” the resource they would receive
            need = 1.0 + scarcity.get(get, 0.0)

            # How much the trade progresses the player toward useful builds
            progress = self._trade_progress_towards_builds(give, get, rate)

            score = (
                progress * weights.bank_trade_progress_weight
                + excess * weights.bank_trade_excess_bonus
                - scarcity.get(give, 0.0) * weights.bank_trade_scarcity_penalty
                + need
            ) * pm

        elif action.action_type == ActionType.MOVE_ROBBER:
            hex_id = int(action.params["hex_id"])
            steal_from = action.params.get("steal_from")

            # Stealing from someone gives extra value,
            # especially if they’re in the lead.
            block_value = 0.0
            if steal_from is not None:
                block_value += weights.block_leader_bonus

            score = (weights.base_value_robber_block + block_value) * pm

        elif action.action_type == ActionType.PASS:
            score = -weights.pass_small_penalty

        # Return final score
        return score

    # Step 3: Pick the highest-scoring action using a max-heap
    def choose_action(self) -> CPUAction:
        """
        Main decision point.
        Creates a priority queue, scores every action, and returns the one
        with the highest score.
        
        Algorithm: Priority Queue (Heap) - uses min-heap with negated scores to simulate max-heap
        Time Complexity: O(A log A) average and worst case
        - A = number of candidate actions
        - Building heap: O(A log A)
        - Extract max: O(log A)
        - Space: O(A) for priority queue
        """
        actions = self.generate_candidate_actions()
        pq: List[CPUAction] = []

        for a in actions:
            a.score = self.score_action(a)
            a.sort_index = -a.score  # keep heap ordering correct
            heapq.heappush(pq, a)

        if not pq:
            return CPUAction(score=0.0, action_type=ActionType.PASS, params={}, explanation="No actions")

        # Best action = highest score = lowest negative sort_index
        best = heapq.heappop(pq)
        return best

    # Helper: check affordability (not heavily used yet)
    def _can_afford(self, cost: Dict[Resource, int]) -> bool:
        player_id = self.rules.current_player_id()
        res = self.rules.player_resources(player_id)
        for r, c in cost.items():
            if res.get(r, 0) < c:
                return False
        return True

    # Helper: estimate how helpful a trade is
    def _trade_progress_towards_builds(self, give: Resource, get: Resource, rate: int) -> float:
        """
        Approximates how much a trade improves your ability to afford
        common builds (settlement, city, road, dev card).
        
        Very rough heuristic, but helps guide "good" trades.
        
        Time Complexity: O(1) - checks 4 build types (settlement, city, road, dev card)
        - Constant number of resource comparisons
        """
        player_id = self.rules.current_player_id()
        res_before = self.rules.player_resources(player_id).copy()

        # Hypothetical new resource state after trade
        res_after = res_before.copy()
        res_after[give] = res_after.get(give, 0) - rate
        res_after[get] = res_after.get(get, 0) + 1

        def progress(res: Dict[Resource, int], cost: Dict[Resource, int]) -> float:
            have = 0
            need = 0
            for r, needed in cost.items():
                need += max(0, needed)
                have += min(res.get(r, 0), needed)
            if need == 0:
                return 0.0
            return have / need  # 0.0 = no progress, 1.0 = can afford

        # Check progress before vs after trade
        settle_cost = self.rules.build_cost_settlement()
        city_cost = self.rules.build_cost_city()
        road_cost = self.rules.build_cost_road()
        dev_cost = self.rules.build_cost_dev_card()

        before = (
            progress(res_before, settle_cost) +
            progress(res_before, city_cost) +
            progress(res_before, road_cost) +
            progress(res_before, dev_cost)
        )
        after = (
            progress(res_after, settle_cost) +
            progress(res_after, city_cost) +
            progress(res_after, road_cost) +
            progress(res_after, dev_cost)
        )

        return max(0.0, after - before)

#to do:
#test code
#add more weights maybe
#add more actions maybe (maybe i forgot some)
