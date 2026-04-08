"""
Test reward robustness across good, bad, and edge-case bridge designs.
Runs locally against the environment (no server needed).
"""

import sys
sys.path.insert(0, ".")

from server.bridge_forge_environment import BridgeForgeEnvironment
from models import BridgeForgeAction


def run_design(name, scenario_id, steps):
    env = BridgeForgeEnvironment()
    env.reset(scenario_id=scenario_id)
    sim_reward = None
    submit_reward = None
    last_msg = ""
    sim_result = None

    for s in steps:
        obs = env.step(BridgeForgeAction(action_type=s[0], params=s[1]))
        last_msg = obs.message
        if s[0] == "simulate":
            sim_reward = obs.reward
            sim_result = obs.simulation_result
        if s[0] == "submit":
            submit_reward = obs.reward

    print(f"\n{'='*60}")
    print(f"  {name} (scenario={scenario_id})")
    print(f"{'='*60}")
    if sim_result:
        print(f"  structural_status: {sim_result.get('structural_status')}")
        print(f"  max_deflection_mm: {sim_result.get('max_deflection_mm')}")
        print(f"  max_stress_ratio:  {sim_result.get('max_stress_ratio')}")
        print(f"  total_mass_kg:     {sim_result.get('total_mass_kg')}")
        print(f"  cost_inr:          {sim_result.get('cost_inr')}")
        print(f"  member_count:      {sim_result.get('member_count')}")
        print(f"  failed_members:    {sim_result.get('failed_members')}")
        if sim_result.get("errors"):
            print(f"  errors:            {sim_result.get('errors')}")
    else:
        print(f"  No simulation ran. Last message: {last_msg}")
    print(f"  simulate reward:   {sim_reward}")
    print(f"  submit reward:     {submit_reward}")
    return submit_reward


# ============================================================
# EASY SCENARIO (8m span, 50kN, no budget)
# ============================================================

# 1. Good triangle truss — proper design
run_design("GOOD: Proper triangle truss", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# 2. BAD: Tiny cross-section — should fail structurally
run_design("BAD: Tiny cross-section (stress failure)", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.0001}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.0001}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.0001}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# 3. BAD: Span too short — doesn't meet 8m requirement
run_design("BAD: Span too short (4m vs 8m required)", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 2, "y": 2}),
    ("add_node", {"node_id": "n3", "x": 4, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# 4. BAD: Wrong bridge type
run_design("BAD: Wrong bridge type (arch vs warren)", "easy", [
    ("select_type", {"bridge_type": "arch"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# 5. BAD: Timber instead of steel — weak material, may fail
run_design("BAD: Timber members (weak material)", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "timber", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "timber", "section_area": 0.01}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "timber", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# 6. EDGE: No bridge type selected
run_design("EDGE: No bridge type selected", "easy", [
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# 7. EDGE: Submit without simulate
run_design("EDGE: Submit without simulate", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("submit", {}),
])

# 8. EDGE: Simulate with no members
run_design("EDGE: Simulate with no members", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("simulate", {}),
])

# 9. EDGE: Simulate with no supports
run_design("EDGE: Simulate with no supports", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("simulate", {}),
])

# 10. EDGE: Simulate with no loads
run_design("EDGE: Simulate with no loads", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n2", "support_type": "roller"}),
    ("simulate", {}),
])

# 11. GOOD: Overbuilt bridge — huge cross-sections
run_design("GOOD: Overbuilt (huge cross-sections)", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.1}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.1}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.1}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# ============================================================
# MEDIUM SCENARIO (22m span, 200kN, ₹65L budget)
# ============================================================

# 12. GOOD: Proper Pratt truss for medium
run_design("GOOD: Proper Pratt truss (medium)", "medium", [
    ("select_type", {"bridge_type": "pratt_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 5.5, "y": 0}),
    ("add_node", {"node_id": "n3", "x": 11, "y": 0}),
    ("add_node", {"node_id": "n4", "x": 16.5, "y": 0}),
    ("add_node", {"node_id": "n5", "x": 22, "y": 0}),
    ("add_node", {"node_id": "n6", "x": 5.5, "y": 4}),
    ("add_node", {"node_id": "n7", "x": 11, "y": 4}),
    ("add_node", {"node_id": "n8", "x": 16.5, "y": 4}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m3", "node_start": "n3", "node_end": "n4", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m4", "node_start": "n4", "node_end": "n5", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m5", "node_start": "n6", "node_end": "n7", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m6", "node_start": "n7", "node_end": "n8", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m7", "node_start": "n1", "node_end": "n6", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m8", "node_start": "n5", "node_end": "n8", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m9", "node_start": "n2", "node_end": "n6", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m10", "node_start": "n3", "node_end": "n7", "material": "steel", "section_area": 0.005}),
    ("add_member", {"member_id": "m11", "node_start": "n4", "node_end": "n8", "material": "steel", "section_area": 0.005}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n5", "support_type": "roller"}),
    ("add_load", {"node_id": "n3", "Fx": 0, "Fy": -200}),
    ("simulate", {}),
    ("submit", {}),
])

# 13. BAD: Over-budget design for medium
run_design("BAD: Overbuilt, over-budget (medium)", "medium", [
    ("select_type", {"bridge_type": "pratt_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 11, "y": 5}),
    ("add_node", {"node_id": "n3", "x": 22, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.5}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.5}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.5}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -200}),
    ("simulate", {}),
    ("submit", {}),
])

# ============================================================
# HARD SCENARIO (35m span, 150kN, 6m deck, seismic zone III)
# ============================================================

# 14. BAD: No deck height for hard (needs 6m)
run_design("BAD: No deck height (hard, needs 6m)", "hard", [
    ("select_type", {"bridge_type": "howe_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 17.5, "y": 3}),
    ("add_node", {"node_id": "n3", "x": 35, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -150}),
    ("simulate", {}),
    ("submit", {}),
])

# 15. EDGE: Unstable structure — collinear nodes (all y=0, single beam)
run_design("EDGE: Unstable collinear beam (no triangulation)", "easy", [
    ("select_type", {"bridge_type": "simply_supported_beam"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n2", "x": 4, "y": 0}),
    ("add_node", {"node_id": "n3", "x": 8, "y": 0}),
    ("add_member", {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}),
    ("add_member", {"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}),
    ("add_support", {"node_id": "n1", "support_type": "pin"}),
    ("add_support", {"node_id": "n3", "support_type": "roller"}),
    ("add_load", {"node_id": "n2", "Fx": 0, "Fy": -50}),
    ("simulate", {}),
    ("submit", {}),
])

# 16. EDGE: Duplicate node ID
run_design("EDGE: Duplicate node ID", "easy", [
    ("select_type", {"bridge_type": "warren_truss"}),
    ("add_node", {"node_id": "n1", "x": 0, "y": 0}),
    ("add_node", {"node_id": "n1", "x": 8, "y": 0}),
])

# 17. EDGE: Step after done
def test_step_after_done():
    env = BridgeForgeEnvironment()
    env.reset(scenario_id="easy")
    env.step(BridgeForgeAction(action_type="select_type", params={"bridge_type": "warren_truss"}))
    env.step(BridgeForgeAction(action_type="add_node", params={"node_id": "n1", "x": 0, "y": 0}))
    env.step(BridgeForgeAction(action_type="add_node", params={"node_id": "n2", "x": 4, "y": 3}))
    env.step(BridgeForgeAction(action_type="add_node", params={"node_id": "n3", "x": 8, "y": 0}))
    env.step(BridgeForgeAction(action_type="add_member", params={"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}))
    env.step(BridgeForgeAction(action_type="add_member", params={"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}))
    env.step(BridgeForgeAction(action_type="add_member", params={"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}))
    env.step(BridgeForgeAction(action_type="add_support", params={"node_id": "n1", "support_type": "pin"}))
    env.step(BridgeForgeAction(action_type="add_support", params={"node_id": "n3", "support_type": "roller"}))
    env.step(BridgeForgeAction(action_type="add_load", params={"node_id": "n2", "Fx": 0, "Fy": -50}))
    env.step(BridgeForgeAction(action_type="simulate", params={}))
    obs = env.step(BridgeForgeAction(action_type="submit", params={}))
    after = env.step(BridgeForgeAction(action_type="add_node", params={"node_id": "n99", "x": 0, "y": 0}))
    print(f"\n{'='*60}")
    print(f"  EDGE: Step after done")
    print(f"{'='*60}")
    print(f"  submit reward: {obs.reward}")
    print(f"  after-done message: {after.message}")
    print(f"  after-done reward: {after.reward}")

test_step_after_done()

print("\n" + "="*60)
print("  SUMMARY COMPLETE")
print("="*60)
