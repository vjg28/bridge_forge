# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import random
from typing import Dict, List, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import BRIDGE_TYPES, MATERIALS, BridgeForgeAction, BridgeForgeObservation
except (ImportError, ValueError):
    from models import BRIDGE_TYPES, MATERIALS, BridgeForgeAction, BridgeForgeObservation

try:
    from .scenarios import SCENARIOS, get_scenario, get_visible_constraints
    from .simulation import run_simulation
    from .reward import compute_reward
except (ImportError, ValueError):
    from server.scenarios import SCENARIOS, get_scenario, get_visible_constraints
    from server.simulation import run_simulation
    from server.reward import compute_reward


class BridgeForgeEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._bridge_type: Optional[str] = None
        self._nodes: List[Dict] = []
        self._members: List[Dict] = []
        self._supports: List[Dict] = []
        self._loads: List[Dict] = []
        self._simulation_result: Optional[Dict] = None
        self._scenario: Optional[Dict] = None
        self._done = False

    def reset(self, seed: Optional[int] = None, **kwargs) -> BridgeForgeObservation:
        if seed is not None:
            random.seed(seed)

        scenario_id = kwargs.get("scenario_id")
        if scenario_id:
            self._scenario = get_scenario(scenario_id)
        else:
            self._scenario = random.choice(SCENARIOS)

        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._bridge_type = None
        self._nodes = []
        self._members = []
        self._supports = []
        self._loads = []
        self._simulation_result = None
        self._done = False

        return self._make_observation(message="Environment reset. Choose a bridge type to begin.")

    def step(self, action: BridgeForgeAction, **kwargs) -> BridgeForgeObservation:
        if self._done:
            return self._make_observation(message="Episode is done. Call reset() to start a new episode.")

        if self._scenario is None:
            return self._make_observation(message="No scenario loaded. Call reset() first.")

        self._state.step_count += 1
        action_type = action.action_type
        params = action.params

        handler = {
            "select_type": self._handle_select_type,
            "add_node": self._handle_add_node,
            "add_member": self._handle_add_member,
            "add_support": self._handle_add_support,
            "add_load": self._handle_add_load,
            "simulate": self._handle_simulate,
            "submit": self._handle_submit,
        }.get(action_type)

        if handler is None:
            return self._make_observation(
                message=f"Unknown action_type: {action_type}. "
                f"Valid types: select_type, add_node, add_member, add_support, add_load, simulate, submit"
            )

        return handler(params)

    def _handle_select_type(self, params: Dict) -> BridgeForgeObservation:
        bridge_type = params.get("bridge_type", "")
        if bridge_type not in BRIDGE_TYPES:
            return self._make_observation(
                message=f"Invalid bridge type '{bridge_type}'. Choose from: {BRIDGE_TYPES}"
            )
        self._bridge_type = bridge_type
        return self._make_observation(message=f"Bridge type set to '{bridge_type}'.")

    def _handle_add_node(self, params: Dict) -> BridgeForgeObservation:
        node_id = params.get("node_id")
        x = params.get("x")
        y = params.get("y")

        if node_id is None or x is None or y is None:
            return self._make_observation(message="add_node requires: node_id, x, y")

        for n in self._nodes:
            if n["node_id"] == node_id:
                return self._make_observation(message=f"Node '{node_id}' already exists.")

        self._nodes.append({"node_id": str(node_id), "x": float(x), "y": float(y)})
        return self._make_observation(message=f"Node '{node_id}' added at ({x}, {y}).")

    def _handle_add_member(self, params: Dict) -> BridgeForgeObservation:
        member_id = params.get("member_id")
        node_start = params.get("node_start")
        node_end = params.get("node_end")
        material = params.get("material", "steel")
        section_area = params.get("section_area", 0.01)

        if member_id is None or node_start is None or node_end is None:
            return self._make_observation(message="add_member requires: member_id, node_start, node_end")

        if material not in MATERIALS:
            return self._make_observation(
                message=f"Invalid material '{material}'. Choose from: {list(MATERIALS.keys())}"
            )

        node_ids = {n["node_id"] for n in self._nodes}
        if str(node_start) not in node_ids:
            return self._make_observation(message=f"Node '{node_start}' not found.")
        if str(node_end) not in node_ids:
            return self._make_observation(message=f"Node '{node_end}' not found.")

        for m in self._members:
            if m["member_id"] == member_id:
                return self._make_observation(message=f"Member '{member_id}' already exists.")

        self._members.append({
            "member_id": str(member_id),
            "node_start": str(node_start),
            "node_end": str(node_end),
            "material": material,
            "section_area": float(section_area),
        })
        return self._make_observation(
            message=f"Member '{member_id}' added: {node_start} -> {node_end} ({material}, A={section_area})."
        )

    def _handle_add_support(self, params: Dict) -> BridgeForgeObservation:
        node_id = params.get("node_id")
        support_type = params.get("support_type")

        if node_id is None or support_type is None:
            return self._make_observation(message="add_support requires: node_id, support_type (pin|roller)")

        if support_type not in ("pin", "roller"):
            return self._make_observation(message="support_type must be 'pin' or 'roller'.")

        node_ids = {n["node_id"] for n in self._nodes}
        if str(node_id) not in node_ids:
            return self._make_observation(message=f"Node '{node_id}' not found.")

        for s in self._supports:
            if s["node_id"] == str(node_id):
                return self._make_observation(message=f"Support already exists at node '{node_id}'.")

        self._supports.append({"node_id": str(node_id), "support_type": support_type})
        return self._make_observation(message=f"Support ({support_type}) added at node '{node_id}'.")

    def _handle_add_load(self, params: Dict) -> BridgeForgeObservation:
        node_id = params.get("node_id")
        Fx = params.get("Fx", 0.0)
        Fy = params.get("Fy", 0.0)

        if node_id is None:
            return self._make_observation(message="add_load requires: node_id")

        node_ids = {n["node_id"] for n in self._nodes}
        if str(node_id) not in node_ids:
            return self._make_observation(message=f"Node '{node_id}' not found.")

        self._loads.append({"node_id": str(node_id), "Fx": float(Fx), "Fy": float(Fy)})
        return self._make_observation(
            message=f"Load applied at node '{node_id}': Fx={Fx} kN, Fy={Fy} kN."
        )

    def _handle_simulate(self, params: Dict) -> BridgeForgeObservation:
        if not self._nodes or not self._members:
            return self._make_observation(message="Cannot simulate: add nodes and members first.")

        if not self._supports:
            return self._make_observation(message="Cannot simulate: add at least one support.")

        if not self._loads:
            return self._make_observation(message="Cannot simulate: add at least one load.")

        result = run_simulation(
            nodes=self._nodes,
            members=self._members,
            supports=self._supports,
            loads=self._loads,
            constraints=self._scenario["constraints"],
        )

        self._simulation_result = result

        reward = compute_reward(
            bridge_type=self._bridge_type or "",
            nodes=self._nodes,
            simulation_result=result,
            constraints=self._scenario["constraints"],
            is_submit=False,
        )

        return self._make_observation(
            message="Simulation complete.",
            reward=reward,
        )

    def _handle_submit(self, params: Dict) -> BridgeForgeObservation:
        if self._simulation_result is None:
            return self._make_observation(message="Run simulate() before submitting.")

        reward = compute_reward(
            bridge_type=self._bridge_type or "",
            nodes=self._nodes,
            simulation_result=self._simulation_result,
            constraints=self._scenario["constraints"],
            is_submit=True,
        )

        self._done = True
        return self._make_observation(
            message=f"Design submitted. Final reward: {reward}",
            reward=reward,
            done=True,
        )

    def _make_observation(
        self,
        message: str = "",
        reward: float = 0.0,
        done: bool = False,
    ) -> BridgeForgeObservation:
        visible_constraints = {}
        if self._scenario:
            visible_constraints = get_visible_constraints(self._scenario["constraints"])

        return BridgeForgeObservation(
            scenario=self._scenario["scenario"] if self._scenario else "",
            bridge_type=self._bridge_type,
            nodes=list(self._nodes),
            members=list(self._members),
            supports=list(self._supports),
            loads=list(self._loads),
            simulation_result=self._simulation_result,
            constraints=visible_constraints,
            step_count=self._state.step_count,
            done=done,
            reward=reward,
            message=message,
        )

    @property
    def state(self) -> State:
        return self._state
