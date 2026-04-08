from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

import gradio as gr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

PARAM_EXAMPLES = {
    "select_type": '{"bridge_type": "warren_truss"}',
    "add_node": '{"node_id": "n1", "x": 0.0, "y": 0.0}',
    "add_member": '{"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel", "section_area": 0.01}',
    "add_support": '{"node_id": "n1", "support_type": "pin"}',
    "add_load": '{"node_id": "n2", "Fx": 0.0, "Fy": -50.0}',
    "simulate": "{}",
    "submit": "{}",
}

ACTION_TYPES = list(PARAM_EXAMPLES.keys())

SCENARIO_IDS = ["easy", "medium", "hard"]

STATIC_DIR = "/tmp/bridge_forge_static"


def _render_bridge(obs: Dict[str, Any]) -> Optional[str]:
    nodes = obs.get("nodes", [])
    if not nodes:
        return None

    node_map = {n["node_id"]: n for n in nodes}
    members = obs.get("members", [])
    supports = obs.get("supports", [])
    loads = obs.get("loads", [])
    sim = obs.get("simulation_result")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_facecolor("#0d1117")
    fig.patch.set_facecolor("#0d1117")

    for m in members:
        n1 = node_map.get(m.get("node_start"))
        n2 = node_map.get(m.get("node_end"))
        if n1 and n2:
            color = "#58a6ff"
            if sim and m.get("member_id") in (sim.get("failed_members") or []):
                color = "#f85149"
            ax.plot(
                [n1["x"], n2["x"]], [n1["y"], n2["y"]],
                color=color, linewidth=2.5, solid_capstyle="round", zorder=2,
            )
            mx = (n1["x"] + n2["x"]) / 2
            my = (n1["y"] + n2["y"]) / 2
            ax.text(mx, my, m.get("member_id", ""), fontsize=7,
                    color="#8b949e", ha="center", va="bottom", zorder=5)

    sup_set = {s["node_id"] for s in supports}
    load_set = {ld["node_id"] for ld in loads}

    for n in nodes:
        color = "#3fb950"
        if n["node_id"] in sup_set:
            color = "#d29922"
        if n["node_id"] in load_set:
            color = "#f85149"
        ax.plot(n["x"], n["y"], "o", color=color, markersize=10, zorder=4)
        ax.text(n["x"], n["y"] + 0.3, n["node_id"], fontsize=9,
                color="#c9d1d9", ha="center", va="bottom", fontweight="bold", zorder=5)

    for s in supports:
        n = node_map.get(s["node_id"])
        if not n:
            continue
        if s["support_type"] == "pin":
            tri = patches.RegularPolygon(
                (n["x"], n["y"] - 0.4), numVertices=3, radius=0.35,
                orientation=0, facecolor="none", edgecolor="#d29922", linewidth=2, zorder=3,
            )
            ax.add_patch(tri)
        elif s["support_type"] == "roller":
            circle = patches.Circle(
                (n["x"], n["y"] - 0.4), radius=0.2,
                facecolor="none", edgecolor="#d29922", linewidth=2, zorder=3,
            )
            ax.add_patch(circle)
            ax.plot(
                [n["x"] - 0.3, n["x"] + 0.3], [n["y"] - 0.65, n["y"] - 0.65],
                color="#d29922", linewidth=2, zorder=3,
            )

    for ld in loads:
        n = node_map.get(ld["node_id"])
        if not n:
            continue
        fx = ld.get("Fx", 0)
        fy = ld.get("Fy", 0)
        mag = max(abs(fx), abs(fy), 1)
        scale = 1.5 / mag
        ax.annotate(
            "", xy=(n["x"], n["y"]),
            xytext=(n["x"] - fx * scale, n["y"] - fy * scale),
            arrowprops=dict(arrowstyle="->,head_width=0.3,head_length=0.2",
                            color="#f85149", lw=2),
            zorder=6,
        )
        ax.text(
            n["x"] - fx * scale * 0.5, n["y"] - fy * scale * 0.5 + 0.3,
            f"{abs(fy):.0f}kN", fontsize=8, color="#f85149", ha="center", zorder=6,
        )

    xs = [n["x"] for n in nodes]
    ys = [n["y"] for n in nodes]
    pad_x = max((max(xs) - min(xs)) * 0.15, 1.5)
    pad_y = max((max(ys) - min(ys)) * 0.25, 1.5)
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.15, color="#30363d")
    ax.tick_params(colors="#8b949e")
    for spine in ax.spines.values():
        spine.set_color("#30363d")

    title_parts = []
    if obs.get("bridge_type"):
        title_parts.append(obs["bridge_type"].replace("_", " ").title())
    title_parts.append(f"{len(nodes)} nodes, {len(members)} members")
    if sim:
        status = sim.get("structural_status", "?")
        title_parts.append(f"Status: {status.upper()}")
    ax.set_title(" | ".join(title_parts), color="#c9d1d9", fontsize=12, pad=10)

    os.makedirs(STATIC_DIR, exist_ok=True)
    path = os.path.join(STATIC_DIR, f"preview_{uuid.uuid4().hex[:8]}.png")
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def _format_obs(data: Dict[str, Any]) -> str:
    obs = data.get("observation", {})
    lines: List[str] = []

    if obs.get("message"):
        lines.append(f"**Message:** {obs['message']}")
    if obs.get("scenario"):
        lines.append(f"\n**Scenario:** {obs['scenario'][:200]}...")
    if obs.get("bridge_type"):
        lines.append(f"**Bridge type:** `{obs['bridge_type']}`")
    if obs.get("constraints"):
        lines.append(f"**Constraints:** `{obs['constraints']}`")

    nodes = obs.get("nodes", [])
    members = obs.get("members", [])
    supports = obs.get("supports", [])
    loads = obs.get("loads", [])
    if nodes:
        lines.append(f"\n**Nodes ({len(nodes)}):** {', '.join(n.get('node_id','?') for n in nodes)}")
    if members:
        lines.append(f"**Members ({len(members)}):** {', '.join(m.get('member_id','?') for m in members)}")
    if supports:
        lines.append(f"**Supports ({len(supports)}):** {', '.join(s.get('node_id','?')+' ('+s.get('support_type','?')+')' for s in supports)}")
    if loads:
        lines.append(f"**Loads ({len(loads)}):** {', '.join(l.get('node_id','?') for l in loads)}")

    sim = obs.get("simulation_result")
    if sim:
        lines.append("\n### Simulation Results")
        lines.append(f"- **Status:** `{sim.get('structural_status', '?')}`")
        lines.append(f"- **Max deflection:** `{sim.get('max_deflection_mm', 0):.4f} mm`")
        lines.append(f"- **Max stress ratio:** `{sim.get('max_stress_ratio', 0):.4f}`")
        lines.append(f"- **Total mass:** `{sim.get('total_mass_kg', 0):.2f} kg`")
        lines.append(f"- **Cost:** `{sim.get('cost_inr', 0):,.0f} INR`")
        lines.append(f"- **Members:** `{sim.get('member_count', 0)}`")
        if sim.get("failed_members"):
            lines.append(f"- **Failed:** `{sim['failed_members']}`")

    reward = data.get("reward")
    done = data.get("done")
    if reward is not None:
        lines.append(f"\n**Reward:** `{reward}`")
    if done is not None:
        lines.append(f"**Done:** `{done}`")

    return "\n".join(lines) if lines else "*No observation data*"


def _make_viz(data: Dict[str, Any]) -> Optional[str]:
    obs = data.get("observation", {})
    sim = obs.get("simulation_result")
    if sim and sim.get("visualization_url"):
        local = os.path.join(STATIC_DIR, os.path.basename(sim["visualization_url"]))
        if os.path.exists(local):
            return local
    return _render_bridge(obs)


def build_bridge_forge_ui(
    web_manager: Any,
    action_fields: List[Dict[str, Any]],
    metadata: Any,
    is_chat_env: bool,
    title: str,
    quick_start_md: Optional[str],
) -> gr.Blocks:
    async def reset_env(scenario_id: str):
        try:
            data = await web_manager.reset_environment(
                {"scenario_id": scenario_id or "easy"}
            )
            obs_md = _format_obs(data)
            viz = _make_viz(data)
            return (obs_md, json.dumps(data, indent=2), f"Reset with scenario: {scenario_id}", viz)
        except Exception as e:
            return ("", "", f"Error: {e}", None)

    async def step_env(action_type: str, params_json: str):
        if not action_type:
            return ("", "", "Select an action type first.", None)
        try:
            params = json.loads(params_json) if params_json.strip() else {}
        except json.JSONDecodeError as e:
            return ("", "", f"Invalid JSON in params: {e}", None)

        action_data = {"action_type": action_type, "params": params}
        try:
            data = await web_manager.step_environment(action_data)
            obs_md = _format_obs(data)
            viz = _make_viz(data)
            return (obs_md, json.dumps(data, indent=2), "Step complete.", viz)
        except Exception as e:
            return ("", "", f"Error: {e}", None)

    def update_placeholder(action_type: str):
        return gr.update(value=PARAM_EXAMPLES.get(action_type, "{}"))

    with gr.Blocks(title=f"BridgeForge: {title}") as demo:
        gr.Markdown("## BridgeForge Playground")

        with gr.Row():
            with gr.Column(scale=1):
                scenario_dd = gr.Dropdown(
                    choices=SCENARIO_IDS,
                    value="easy",
                    label="Scenario",
                )
                reset_btn = gr.Button("Reset", variant="secondary")

                gr.Markdown("---")

                action_dd = gr.Dropdown(
                    choices=ACTION_TYPES,
                    value="select_type",
                    label="Action Type",
                )
                params_box = gr.Textbox(
                    label="Params (JSON)",
                    value=PARAM_EXAMPLES["select_type"],
                    lines=3,
                    placeholder='e.g. {"bridge_type": "warren_truss"}',
                )
                step_btn = gr.Button("Step", variant="primary")

                status_box = gr.Textbox(label="Status", interactive=False)

            with gr.Column(scale=2):
                obs_display = gr.Markdown(
                    value="Click **Reset** to start a new episode."
                )
                viz_image = gr.Image(
                    label="Bridge Visualization",
                    type="filepath",
                    interactive=False,
                )
                with gr.Accordion("Raw JSON", open=False):
                    raw_json = gr.Code(
                        label="Response",
                        language="json",
                        interactive=False,
                    )

        action_dd.change(
            fn=update_placeholder,
            inputs=[action_dd],
            outputs=[params_box],
        )

        reset_btn.click(
            fn=reset_env,
            inputs=[scenario_dd],
            outputs=[obs_display, raw_json, status_box, viz_image],
        )

        step_btn.click(
            fn=step_env,
            inputs=[action_dd, params_box],
            outputs=[obs_display, raw_json, status_box, viz_image],
        )

    return demo
