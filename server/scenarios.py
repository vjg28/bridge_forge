# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict, List, Optional

SCENARIOS: List[Dict] = [
    {
        "id": "easy",
        "scenario": (
            "A small village in rural Maharashtra needs a footbridge over a seasonal "
            "stream. The stream is about 8 meters wide at its narrowest crossing point. "
            "The bridge will primarily be used by villagers carrying agricultural goods "
            "and livestock — estimated max load at any time is around 5 tonnes. Local "
            "PWD has approved a basic steel truss design. Budget is flexible. Just make "
            "sure it holds."
        ),
        "constraints": {
            "span_m": 8,
            "load_kn": 50,
            "budget_inr": None,
            "max_deflection_mm": 20,
            "min_deck_height_m": 0,
            "recommended_type": "warren_truss",
            "max_members": None,
            "baseline_mass_kg": 5000,
        },
    },
    {
        "id": "medium",
        "scenario": (
            "The NHAI is building a service road bridge over an irrigation canal in "
            "Rajasthan. The canal is 22 meters wide. The bridge needs to carry "
            "construction vehicles — trucks up to 20 tonnes. The state government has "
            "allocated ₹65 lakhs for this bridge and will not approve cost overruns. "
            "The project manager has specifically asked the design to be as lightweight "
            "as possible since the soil bearing capacity on the canal banks is low."
        ),
        "constraints": {
            "span_m": 22,
            "load_kn": 200,
            "budget_inr": 6_500_000,
            "max_deflection_mm": 15,
            "min_deck_height_m": 0,
            "recommended_type": "pratt_truss",
            "max_members": None,
            "minimize": "mass",
            "baseline_mass_kg": 25000,
        },
    },
    {
        "id": "hard",
        "scenario": (
            "A coastal district in Odisha needs a bridge connecting two fishing villages "
            "across a tidal estuary, roughly 35 meters wide. The region was severely "
            "affected by Cyclone Fani in 2019 — the previous bridge was destroyed. The "
            "new bridge must have its deck at least 6 meters above normal water level to "
            "handle storm surge. The area sits in seismic zone III. The district "
            "collector's brief mentions that 'the structure must be maintainable by "
            "local contractors without specialized equipment' and that 'the fishing "
            "community needs this operational within 8 months.' The total funds available "
            "from NDRF and state government together are ₹1.8 crore."
        ),
        "constraints": {
            "span_m": 35,
            "load_kn": 150,
            "budget_inr": 18_000_000,
            "max_deflection_mm": 12,
            "min_deck_height_m": 6.0,
            "seismic_zone": 3,
            "recommended_type": "howe_truss",
            "max_members": 24,
            "construction_time_days": 240,
            "baseline_mass_kg": 50000,
        },
    },
]


def get_scenario(scenario_id: str) -> Optional[Dict]:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None


def get_visible_constraints(constraints: Dict) -> Dict:
    return {
        "span_m": constraints["span_m"],
        "load_kn": constraints["load_kn"],
    }
