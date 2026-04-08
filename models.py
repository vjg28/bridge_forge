# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict, List, Literal, Optional

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


MATERIALS: Dict[str, Dict] = {
    "steel": {"E": 200e9, "density": 7850, "cost_per_kg": 85, "yield_stress": 250e6},
    "concrete": {"E": 30e9, "density": 2400, "cost_per_kg": 12, "yield_stress": 30e6},
    "timber": {"E": 12e9, "density": 600, "cost_per_kg": 30, "yield_stress": 40e6},
}

BRIDGE_TYPES = [
    "simply_supported_beam",
    "warren_truss",
    "pratt_truss",
    "howe_truss",
    "arch",
]


class BridgeForgeAction(Action):
    action_type: Literal[
        "select_type",
        "add_node",
        "add_member",
        "add_support",
        "add_load",
        "simulate",
        "submit",
    ] = Field(..., description="Type of action to perform")
    params: Dict = Field(default_factory=dict, description="Action parameters")


class SimulationResult(Observation):
    structural_status: Literal["pass", "fail"] = "fail"
    max_deflection_mm: float = 0.0
    max_stress_ratio: float = 0.0
    failed_members: List[str] = Field(default_factory=list)
    total_mass_kg: float = 0.0
    cost_inr: float = 0.0
    member_count: int = 0
    visualization_url: str = ""


class BridgeForgeObservation(Observation):
    scenario: str = ""
    bridge_type: Optional[str] = None
    nodes: List[Dict] = Field(default_factory=list)
    members: List[Dict] = Field(default_factory=list)
    supports: List[Dict] = Field(default_factory=list)
    loads: List[Dict] = Field(default_factory=list)
    simulation_result: Optional[Dict] = None
    constraints: Dict = Field(default_factory=dict)
    step_count: int = 0
    message: str = ""
