# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict, List


def design_spans_required_distance(nodes: List[Dict], span_m: float) -> bool:
    if not nodes:
        return False
    xs = [n["x"] for n in nodes]
    return (max(xs) - min(xs)) >= span_m


def min_deck_height_ok(nodes: List[Dict], min_deck_height_m: float) -> bool:
    if min_deck_height_m <= 0:
        return True
    if not nodes:
        return False
    ys = [n["y"] for n in nodes]
    return max(ys) >= min_deck_height_m


def compute_reward(
    bridge_type: str,
    nodes: List[Dict],
    simulation_result: Dict,
    constraints: Dict,
    is_submit: bool = False,
) -> float:
    structural_pass = 1.0 if simulation_result.get("structural_status") == "pass" else 0.0
    span_met = 1.0 if design_spans_required_distance(nodes, constraints["span_m"]) else 0.0
    deck_height_met = 1.0 if min_deck_height_ok(nodes, constraints.get("min_deck_height_m", 0)) else 0.0

    max_defl = constraints.get("max_deflection_mm", 20)
    deflection_score = max(0.0, 1.0 - (simulation_result.get("max_deflection_mm", 0) / max_defl))

    budget = constraints.get("budget_inr")
    if budget is not None and budget > 0:
        cost_score = max(0.0, 1.0 - (simulation_result.get("cost_inr", 0) / budget))
    else:
        cost_score = 1.0

    baseline_mass = constraints.get("baseline_mass_kg", 50000)
    mass_score = max(0.0, 1.0 - (simulation_result.get("total_mass_kg", 0) / baseline_mass))

    max_mem = constraints.get("max_members")
    if max_mem is not None and max_mem > 0:
        complexity_score = max(0.0, 1.0 - (simulation_result.get("member_count", 0) / max_mem))
    else:
        complexity_score = 1.0

    recommended = constraints.get("recommended_type")
    type_score = 1.0 if bridge_type == recommended else 0.3

    if is_submit:
        reward = (
            structural_pass * span_met * deck_height_met
            * (
                0.30 * deflection_score
                + 0.25 * cost_score
                + 0.20 * mass_score
                + 0.15 * type_score
                + 0.10 * complexity_score
            )
        )
    else:
        reward = 0.3 * structural_pass + 0.2 * deflection_score + 0.1 * cost_score

    return round(reward, 4)
