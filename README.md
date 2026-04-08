---
title: Bridge Forge Environment Server
emoji: "\U0001F309"
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# BridgeForge — Structural Engineering RL Environment

An RL environment where an AI agent designs 2D truss bridges. Given a real-world scenario in natural language, the agent selects a bridge type, places nodes and members, runs structural simulation (via anastruct), and iterates until the design meets all constraints.

## How It Works

1. **Reset** with a scenario (easy / medium / hard)
2. **Select a bridge type** (warren_truss, pratt_truss, howe_truss, arch, simply_supported_beam)
3. **Add nodes** at (x, y) coordinates in meters
4. **Add members** connecting nodes with a material and cross-section area
5. **Add supports** (pin or roller) at bridge ends
6. **Add loads** (forces in kN) at load-bearing nodes
7. **Simulate** — runs 2D truss analysis, returns deflection, stress, cost, mass
8. **Submit** — finalizes the design and returns a reward in [0, 1]

## Action Reference

| Action | Params | Example |
|---|---|---|
| `select_type` | `{"bridge_type": "warren_truss"}` | Pick bridge topology |
| `add_node` | `{"node_id": "n1", "x": 0.0, "y": 0.0}` | Place a node |
| `add_member` | `{"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}` | Connect two nodes |
| `add_support` | `{"node_id": "n1", "support_type": "pin"}` | Pin or roller support |
| `add_load` | `{"node_id": "n2", "Fx": 0.0, "Fy": -50.0}` | Apply force in kN |
| `simulate` | `{}` | Run structural analysis |
| `submit` | `{}` | Finalize and get reward |

## Materials

| Material | E (GPa) | Density (kg/m³) | Cost (₹/kg) | Yield Stress (MPa) |
|---|---|---|---|---|
| Steel | 200 | 7850 | 85 | 250 |
| Concrete | 30 | 2400 | 12 | 30 |
| Timber | 12 | 600 | 30 | 40 |

## Tasks

| Task | Span | Load | Budget | Key Challenge |
|---|---|---|---|---|
| **Easy** | 8m | 50 kN | No limit | Just make it hold |
| **Medium** | 22m | 200 kN | ₹65 lakhs | Minimize mass under budget |
| **Hard** | 35m | 150 kN | ₹1.8 crore | 6m deck height, seismic zone III, max 24 members |

## Reward Function

Score is 0.0–1.0, computed as:

**Hard constraints** (binary, multiplicative): structural pass × span met × deck height met

**Soft constraints** (weighted sum):
- 30% deflection score
- 25% cost efficiency
- 20% mass efficiency
- 15% bridge type match
- 10% complexity (fewer members = simpler)

## Quick Start

```python
from bridge_forge import BridgeForgeAction, BridgeForgeEnv

async with BridgeForgeEnv(base_url="https://eventhorizon28-bridge-forge.hf.space") as env:
    result = await env.reset(scenario_id="easy")

    await env.step(BridgeForgeAction(action_type="select_type", params={"bridge_type": "warren_truss"}))
    await env.step(BridgeForgeAction(action_type="add_node", params={"node_id": "n1", "x": 0, "y": 0}))
    await env.step(BridgeForgeAction(action_type="add_node", params={"node_id": "n2", "x": 4, "y": 3}))
    await env.step(BridgeForgeAction(action_type="add_node", params={"node_id": "n3", "x": 8, "y": 0}))

    await env.step(BridgeForgeAction(action_type="add_member", params={"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}))
    await env.step(BridgeForgeAction(action_type="add_member", params={"member_id": "m2", "node_start": "n2", "node_end": "n3", "material": "steel", "section_area": 0.01}))
    await env.step(BridgeForgeAction(action_type="add_member", params={"member_id": "m3", "node_start": "n1", "node_end": "n3", "material": "steel", "section_area": 0.01}))

    await env.step(BridgeForgeAction(action_type="add_support", params={"node_id": "n1", "support_type": "pin"}))
    await env.step(BridgeForgeAction(action_type="add_support", params={"node_id": "n3", "support_type": "roller"}))
    await env.step(BridgeForgeAction(action_type="add_load", params={"node_id": "n2", "Fx": 0, "Fy": -50}))

    result = await env.step(BridgeForgeAction(action_type="simulate", params={}))
    print(result.observation.simulation_result)

    result = await env.step(BridgeForgeAction(action_type="submit", params={}))
    print(f"Score: {result.reward}")
```

## API Endpoints

- `POST /reset` — Reset environment (pass `{"scenario_id": "easy"}`)
- `POST /step` — Execute action
- `GET /state` — Current state
- `GET /schema` — Action/Observation schemas
- `GET /health` — Health check
- `WS /ws` — WebSocket for persistent sessions
- `GET /static/{filename}` — Bridge visualization PNGs
