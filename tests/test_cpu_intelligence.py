import unittest
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from engine import CPUPlayer, CPUWeights, ActionType
from model.enums import Resource


class FakeRulesAdapter:
	"""
	A lightweight, configurable adapter to simulate board states for CPU tests.
	Override attributes in each test to shape the AI's decision landscape.
	"""
	def __init__(self) -> None:
		# Game/players
		self._current_player: int = 1
		self._opponents: List[int] = [2, 3]
		self._phase: str = "early"  # "early" | "mid" | "late"

		# VP estimates (not heavily used by current AI but kept for completeness)
		self._visible_vp: Dict[int, int] = {1: 2, 2: 2, 3: 2}
		self._hidden_vp_estimate: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0}

		# Resources and costs
		self._player_resources: Dict[int, Dict[Resource, int]] = {
			1: {r: 0 for r in Resource}
		}
		self._production_profile: Dict[int, Dict[Resource, float]] = {
			1: {Resource.BRICK: 0.5, Resource.LUMBER: 0.5, Resource.ORE: 0.5, Resource.GRAIN: 0.5, Resource.WOOL: 0.5}
		}
		self._board_scarcity: Dict[Resource, float] = {
			Resource.BRICK: 0.0, Resource.LUMBER: 0.0, Resource.ORE: 0.0, Resource.GRAIN: 0.0, Resource.WOOL: 0.0
		}
		self._cost_settlement: Dict[Resource, int] = {
			Resource.BRICK: 1, Resource.LUMBER: 1, Resource.GRAIN: 1, Resource.WOOL: 1
		}
		self._cost_road: Dict[Resource, int] = {
			Resource.BRICK: 1, Resource.LUMBER: 1
		}
		self._cost_city: Dict[Resource, int] = {
			Resource.ORE: 3, Resource.GRAIN: 2
		}
		self._cost_dev: Dict[Resource, int] = {
			Resource.ORE: 1, Resource.GRAIN: 1, Resource.WOOL: 1
		}

		# Legal actions
		self._legal_settlement_vertices: List[int] = []
		self._legal_road_edges: List[int] = []
		self._upgradeable_vertices: List[int] = []
		self._can_buy_dev: bool = False
		self._bank_trades: List[Tuple[Resource, Resource, int]] = []
		self._robber_moves: List[Tuple[int, Optional[int]]] = []

		# Board metrics
		self._vertex_pip: Dict[int, float] = {}
		self._vertex_resources: Dict[int, List[Resource]] = {}
		self._road_towards_value: Dict[int, float] = {}
		self._road_contributes_longest: Dict[int, float] = {}
		self._settlement_blocks_value: Dict[int, float] = {}

		# Trade threat toggle
		self._trade_enables_win: bool = False

	# Protocol implementation
	def current_player_id(self) -> int:
		return self._current_player

	def opponents(self) -> Sequence[int]:
		return list(self._opponents)

	def visible_victory_points(self, player_id: int) -> int:
		return self._visible_vp.get(player_id, 0)

	def estimated_hidden_vp(self, player_id: int) -> float:
		return self._hidden_vp_estimate.get(player_id, 0.0)

	def total_victory_points_estimate(self, player_id: int) -> float:
		return self.visible_victory_points(player_id) + self.estimated_hidden_vp(player_id)

	def game_phase(self) -> str:
		return self._phase

	def player_resources(self, player_id: int) -> Dict[Resource, int]:
		return dict(self._player_resources.get(player_id, {}))

	def resource_production_profile(self, player_id: int) -> Dict[Resource, float]:
		return dict(self._production_profile.get(player_id, {}))

	def board_resource_scarcity(self) -> Dict[Resource, float]:
		return dict(self._board_scarcity)

	def build_cost_settlement(self) -> Dict[Resource, int]:
		return dict(self._cost_settlement)

	def build_cost_road(self) -> Dict[Resource, int]:
		return dict(self._cost_road)

	def build_cost_city(self) -> Dict[Resource, int]:
		return dict(self._cost_city)

	def build_cost_dev_card(self) -> Dict[Resource, int]:
		return dict(self._cost_dev)

	def legal_settlement_vertices(self, player_id: int) -> Iterable[int]:
		return list(self._legal_settlement_vertices)

	def legal_road_edges(self, player_id: int) -> Iterable[int]:
		return list(self._legal_road_edges)

	def upgradeable_vertices(self, player_id: int) -> Iterable[int]:
		return list(self._upgradeable_vertices)

	def can_buy_dev_card(self, player_id: int) -> bool:
		return self._can_buy_dev

	def bank_trade_options(self, player_id: int) -> Iterable[Tuple[Resource, Resource, int]]:
		return list(self._bank_trades)

	def robber_move_options(self, player_id: int) -> Iterable[Tuple[int, Optional[int]]]:
		return list(self._robber_moves)

	def vertex_pip(self, vertex_id: int) -> float:
		return float(self._vertex_pip.get(vertex_id, 0.0))

	def vertex_resource_set(self, vertex_id: int) -> Sequence[Resource]:
		return list(self._vertex_resources.get(vertex_id, []))

	def road_expands_towards_value(self, edge_id: int) -> float:
		return float(self._road_towards_value.get(edge_id, 0.0))

	def road_contributes_longest(self, player_id: int, edge_id: int) -> float:
		return float(self._road_contributes_longest.get(edge_id, 0.0))

	def settlement_blocks_opponent_value(self, vertex_id: int) -> float:
		return float(self._settlement_blocks_value.get(vertex_id, 0.0))

	def would_trade_enable_opponent_win(self, target_player_id: int, give: Resource, get: Resource, rate: int) -> bool:
		return bool(self._trade_enables_win)

	def execute(self, action) -> None:
		pass


class TestCPUIntelligence(unittest.TestCase):
	def setUp(self) -> None:
		self.rules = FakeRulesAdapter()
		self.weights = CPUWeights()  # default weights unless overridden
		self.cpu = CPUPlayer(self.rules, self.weights)

	def _debug_dump(self, title: str, chosen) -> None:
		if os.environ.get("AI_TEST_DEBUG") != "1":
			return
		actions = self.cpu.generate_candidate_actions()
		scored = []
		for a in actions:
			score = self.cpu.score_action(a)
			scored.append((score, a.action_type.name, a.params))
		scored.sort(key=lambda x: x[0], reverse=True)
		print(f"\n[DEBUG] {title}: chosen={chosen.action_type.name} {chosen.params}")
		for score, kind, params in scored:
			print(f"  {kind:16s} score={score:7.3f} params={params}")

	def test_early_prefers_settlement_over_dev(self):
		self.rules._phase = "early"
		self.rules._legal_settlement_vertices = [1]
		self.rules._vertex_pip = {1: 8.0}
		self.rules._vertex_resources = {1: [Resource.BRICK, Resource.LUMBER, Resource.GRAIN]}
		self.rules._can_buy_dev = True
		action = self.cpu.choose_action()
		self._debug_dump("early_prefers_settlement_over_dev", action)
		self.assertEqual(action.action_type, ActionType.BUILD_SETTLEMENT)
		self.assertEqual(action.params.get("vertex_id"), 1)

	def test_early_settlement_prefers_high_pip(self):
		self.rules._phase = "early"
		self.rules._legal_settlement_vertices = [1, 2]
		self.rules._vertex_pip = {1: 4.0, 2: 10.0}
		self.rules._vertex_resources = {
			1: [Resource.BRICK, Resource.LUMBER],
			2: [Resource.BRICK, Resource.LUMBER]
		}
		action = self.cpu.choose_action()
		self._debug_dump("early_settlement_prefers_high_pip", action)
		self.assertEqual(action.action_type, ActionType.BUILD_SETTLEMENT)
		self.assertEqual(action.params.get("vertex_id"), 2)

	def test_early_settlement_prefers_diversity(self):
		self.rules._phase = "early"
		self.rules._legal_settlement_vertices = [1, 2]
		# Equal pip, diversity distinguishes
		self.rules._vertex_pip = {1: 6.0, 2: 6.0}
		self.rules._vertex_resources = {
			1: [Resource.BRICK],  # low diversity
			2: [Resource.BRICK, Resource.LUMBER]  # higher diversity
		}
		action = self.cpu.choose_action()
		self._debug_dump("early_settlement_prefers_diversity", action)
		self.assertEqual(action.action_type, ActionType.BUILD_SETTLEMENT)
		self.assertEqual(action.params.get("vertex_id"), 2)

	def test_trade_threat_avoided(self):
		self.rules._phase = "mid"
		# Provide both a trade that would enable win and a safe settlement
		self.rules._bank_trades = [(Resource.BRICK, Resource.GRAIN, 4)]
		self.rules._trade_enables_win = True
		self.rules._legal_settlement_vertices = [1]
		self.rules._vertex_pip = {1: 7.0}
		self.rules._vertex_resources = {1: [Resource.BRICK, Resource.GRAIN]}
		action = self.cpu.choose_action()
		self._debug_dump("trade_threat_avoided", action)
		self.assertEqual(action.action_type, ActionType.BUILD_SETTLEMENT)

	def test_late_game_blocking_road_preferred(self):
		self.rules._phase = "late"
		self.rules._legal_road_edges = [11, 22]
		# Edge 11 is blocking/valuable
		self.rules._road_towards_value = {11: 5.0, 22: 1.0}
		self.rules._road_contributes_longest = {11: 2.0, 22: 0.0}
		action = self.cpu.choose_action()
		self._debug_dump("late_game_blocking_road_preferred", action)
		self.assertEqual(action.action_type, ActionType.BUILD_ROAD)
		self.assertEqual(action.params.get("edge_id"), 11)

	def test_robber_targets_leader_when_available(self):
		self.rules._phase = "late"
		# Provide two robber options; one steals from someone (treat as leader)
		self.rules._robber_moves = [(101, None), (202, 2)]
		action = self.cpu.choose_action()
		self._debug_dump("robber_targets_leader_when_available", action)
		self.assertEqual(action.action_type, ActionType.MOVE_ROBBER)
		self.assertEqual(action.params.get("hex_id"), 202)
		self.assertEqual(action.params.get("steal_from"), 2)

	def test_city_upgrade_prioritizes_high_pip_vertex(self):
		self.rules._phase = "mid"
		self.rules._upgradeable_vertices = [5, 6]
		self.rules._vertex_pip = {5: 7.0, 6: 11.0}
		action = self.cpu.choose_action()
		self._debug_dump("city_upgrade_prioritizes_high_pip_vertex", action)
		self.assertEqual(action.action_type, ActionType.BUILD_CITY)
		self.assertEqual(action.params.get("vertex_id"), 6)

	def test_longest_road_value_outweighs_low_value_road(self):
		self.rules._phase = "mid"
		self.rules._legal_road_edges = [1, 2]
		self.rules._road_towards_value = {1: 1.0, 2: 1.0}
		self.rules._road_contributes_longest = {1: 0.0, 2: 4.0}
		action = self.cpu.choose_action()
		self._debug_dump("longest_road_value_outweighs_low_value_road", action)
		self.assertEqual(action.action_type, ActionType.BUILD_ROAD)
		self.assertEqual(action.params.get("edge_id"), 2)

	def test_bank_trade_prefers_excess_to_scarce(self):
		self.rules._phase = "mid"
		self.rules._can_buy_dev = False
		# Offer two trades: ORE->BRICK and ORE->WOOL; BRICK is scarce and needed for settlement
		self.rules._bank_trades = [
			(Resource.ORE, Resource.BRICK, 4),
			(Resource.ORE, Resource.WOOL, 4),
		]
		self.rules._trade_enables_win = False
		self.rules._player_resources[1] = {
			Resource.ORE: 5, Resource.GRAIN: 0, Resource.BRICK: 0, Resource.LUMBER: 0, Resource.WOOL: 0
		}
		# Production profile shows excess ORE
		self.rules._production_profile[1] = {
			Resource.ORE: 2.0, Resource.BRICK: 0.3, Resource.LUMBER: 0.3, Resource.GRAIN: 0.3, Resource.WOOL: 0.3
		}
		# Scarcity: BRICK is scarce
		self.rules._board_scarcity = {
			Resource.BRICK: 2.0, Resource.LUMBER: 0.0, Resource.ORE: 0.0, Resource.GRAIN: 0.0, Resource.WOOL: 0.5
		}
		# Costs require BRICK for settlement; verify progress improves
		self.rules._cost_settlement = {
			Resource.BRICK: 1, Resource.LUMBER: 1, Resource.GRAIN: 1, Resource.WOOL: 1
		}
		action = self.cpu.choose_action()
		self._debug_dump("bank_trade_prefers_excess_to_scarce", action)
		self.assertEqual(action.action_type, ActionType.BANK_TRADE)
		self.assertEqual(action.params.get("give"), Resource.ORE)
		self.assertEqual(action.params.get("get"), Resource.BRICK)
		self.assertEqual(action.params.get("rate"), 4)

	def test_pass_not_chosen_when_useful_action_exists(self):
		self.rules._phase = "early"
		self.rules._legal_settlement_vertices = [9]
		self.rules._vertex_pip = {9: 5.0}
		self.rules._vertex_resources = {9: [Resource.BRICK, Resource.LUMBER]}
		action = self.cpu.choose_action()
		self._debug_dump("pass_not_chosen_when_useful_action_exists", action)
		self.assertNotEqual(action.action_type, ActionType.PASS)

	def test_pass_chosen_when_no_actions(self):
		self.rules._phase = "mid"
		# No legal actions at all; only PASS remains
		self.rules._legal_settlement_vertices = []
		self.rules._legal_road_edges = []
		self.rules._upgradeable_vertices = []
		self.rules._can_buy_dev = False
		self.rules._bank_trades = []
		self.rules._robber_moves = []
		action = self.cpu.choose_action()
		self._debug_dump("pass_chosen_when_no_actions", action)
		self.assertEqual(action.action_type, ActionType.PASS)

	def test_mid_phase_weights_dev_and_city(self):
		self.rules._phase = "mid"
		self.rules._can_buy_dev = True
		# Provide a low-value road and a city option; city should win in mid
		self.rules._legal_road_edges = [1]
		self.rules._road_towards_value = {1: 0.0}
		self.rules._road_contributes_longest = {1: 0.0}
		self.rules._upgradeable_vertices = [4]
		self.rules._vertex_pip = {4: 8.0}
		action = self.cpu.choose_action()
		self._debug_dump("mid_phase_weights_dev_and_city", action)
		self.assertEqual(action.action_type, ActionType.BUILD_CITY)

	def test_late_phase_weights_blocking_and_robber(self):
		self.rules._phase = "late"
		# Include a robber that steals and a minor road; robber should be very appealing late
		self.rules._robber_moves = [(300, 2)]
		self.rules._legal_road_edges = [7]
		self.rules._road_towards_value = {7: 0.1}
		self.rules._road_contributes_longest = {7: 0.0}
		action = self.cpu.choose_action()
		self._debug_dump("late_phase_weights_blocking_and_robber", action)
		self.assertEqual(action.action_type, ActionType.MOVE_ROBBER)
		self.assertEqual(action.params.get("hex_id"), 300)


if __name__ == "__main__":
	unittest.main()

