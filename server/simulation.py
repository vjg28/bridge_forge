# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import math
import os
import uuid
from typing import Dict, List, Optional, Tuple

from anastruct import SystemElements

try:
    from ..models import MATERIALS
except (ImportError, ValueError):
    from models import MATERIALS


def _member_length(n1: Dict, n2: Dict) -> float:
    return math.sqrt((n2["x"] - n1["x"]) ** 2 + (n2["y"] - n1["y"]) ** 2)


def _member_mass(length: float, section_area: float, material: str) -> float:
    density = MATERIALS[material]["density"]
    return density * section_area * length


def _member_cost(mass_kg: float, material: str) -> float:
    return mass_kg * MATERIALS[material]["cost_per_kg"]


def run_simulation(
    nodes: List[Dict],
    members: List[Dict],
    supports: List[Dict],
    loads: List[Dict],
    constraints: Dict,
    static_dir: str = "/tmp/bridge_forge_static",
) -> Dict:
    os.makedirs(static_dir, exist_ok=True)

    if not nodes or not members:
        return {
            "structural_status": "fail",
            "max_deflection_mm": 0.0,
            "max_stress_ratio": 0.0,
            "failed_members": [],
            "total_mass_kg": 0.0,
            "cost_inr": 0.0,
            "member_count": 0,
            "visualization_url": "",
            "errors": ["No nodes or members defined"],
        }

    node_map = {n["node_id"]: n for n in nodes}

    ss = SystemElements()

    element_ids = {}
    member_props = {}

    for m in members:
        n1 = node_map.get(m["node_start"])
        n2 = node_map.get(m["node_end"])
        if n1 is None or n2 is None:
            continue

        material = m.get("material", "steel")
        section_area = m.get("section_area", 0.01)
        mat = MATERIALS.get(material, MATERIALS["steel"])

        E_kn = mat["E"] / 1000
        EA = E_kn * section_area

        elem_id = ss.add_truss_element(
            location=[[n1["x"], n1["y"]], [n2["x"], n2["y"]]],
            EA=EA,
        )

        if isinstance(elem_id, (list, tuple)):
            elem_id = elem_id[0]

        element_ids[m["member_id"]] = elem_id
        length = _member_length(n1, n2)
        mass = _member_mass(length, section_area, material)
        cost = _member_cost(mass, material)
        member_props[m["member_id"]] = {
            "material": material,
            "section_area": section_area,
            "length": length,
            "mass": mass,
            "cost": cost,
            "yield_stress": mat["yield_stress"],
            "E": mat["E"],
        }

    for sup in supports:
        nid = sup["node_id"]
        n = node_map.get(nid)
        if n is None:
            continue

        node_id_in_ss = ss.find_node_id(vertex=[n["x"], n["y"]])
        if node_id_in_ss is None:
            continue

        if sup["support_type"] == "pin":
            ss.add_support_hinged(node_id=node_id_in_ss)
        elif sup["support_type"] == "roller":
            ss.add_support_roll(node_id=node_id_in_ss)

    seismic_zone = constraints.get("seismic_zone", 0)
    lateral_factor = {0: 0, 1: 0.02, 2: 0.04, 3: 0.06, 4: 0.10, 5: 0.16}.get(
        seismic_zone, 0
    )

    for ld in loads:
        nid = ld["node_id"]
        n = node_map.get(nid)
        if n is None:
            continue

        node_id_in_ss = ss.find_node_id(vertex=[n["x"], n["y"]])
        if node_id_in_ss is None:
            continue

        Fx = ld.get("Fx", 0.0)
        Fy = ld.get("Fy", 0.0)

        if lateral_factor > 0:
            Fx += abs(Fy) * lateral_factor

        ss.point_load(node_id=node_id_in_ss, Fx=Fx, Fy=Fy)

    try:
        ss.solve()
    except Exception as e:
        return {
            "structural_status": "fail",
            "max_deflection_mm": 0.0,
            "max_stress_ratio": 0.0,
            "failed_members": [],
            "total_mass_kg": 0.0,
            "cost_inr": 0.0,
            "member_count": len(members),
            "visualization_url": "",
            "errors": [str(e)],
        }

    max_deflection_m = 0.0
    try:
        for node_id_ss in ss.node_map:
            displacements = ss.get_node_displacements(node_id=node_id_ss)
            if displacements:
                ux = float(displacements.get("ux", 0.0))
                uy = float(displacements.get("uy", 0.0))
                defl = math.sqrt(ux**2 + uy**2)
                max_deflection_m = max(max_deflection_m, defl)
    except Exception:
        pass
    max_deflection_mm = max_deflection_m * 1000

    max_stress_ratio = 0.0
    failed_members_list = []

    for mid, eid in element_ids.items():
        props = member_props[mid]
        try:
            element = ss.element_map.get(eid)
            if element is None:
                continue
            N = element.N_1 if hasattr(element, "N_1") else 0.0
            if N is None:
                N = 0.0
            N_newtons = abs(float(N)) * 1000
            actual_stress = N_newtons / props["section_area"]
            ratio = actual_stress / props["yield_stress"]
            max_stress_ratio = max(max_stress_ratio, ratio)
            if ratio > 1.0:
                failed_members_list.append(mid)
        except Exception:
            pass

    total_mass = sum(p["mass"] for p in member_props.values())
    total_cost = sum(p["cost"] for p in member_props.values())

    structural_status = "pass" if (max_stress_ratio <= 1.0 and len(failed_members_list) == 0) else "fail"

    viz_filename = f"bridge_{uuid.uuid4().hex[:8]}.png"
    viz_path = os.path.join(static_dir, viz_filename)
    try:
        fig = ss.show_structure(show=False, verbosity=0)
        if fig is not None:
            fig.savefig(viz_path, dpi=100, bbox_inches="tight")
            import matplotlib.pyplot as plt
            plt.close(fig)
    except Exception:
        viz_path = ""

    return {
        "structural_status": structural_status,
        "max_deflection_mm": round(max_deflection_mm, 4),
        "max_stress_ratio": round(max_stress_ratio, 4),
        "failed_members": failed_members_list,
        "total_mass_kg": round(total_mass, 2),
        "cost_inr": round(total_cost, 2),
        "member_count": len(members),
        "visualization_url": f"/static/{viz_filename}" if viz_path else "",
    }
