import asyncio
import json
import os
import textwrap
from typing import Dict, List, Optional

from openai import OpenAI

from client import BridgeForgeEnv
from models import BridgeForgeAction

IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", os.getenv("IMAGE_NAME", ""))
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

BENCHMARK = "bridge_forge"
TASKS = ["easy", "medium", "hard"]
MAX_STEPS = 50
TEMPERATURE = 0.3
MAX_TOKENS = 512

SYSTEM_PROMPT = textwrap.dedent("""\
You are a structural engineer AI. You design 2D truss bridges in a simulation environment.

You interact via JSON actions. Each turn, reply with EXACTLY one JSON object (no markdown, no explanation):
{"action_type": "<type>", "params": {<params>}}

Available actions (in recommended order):
1. select_type: {"bridge_type": "warren_truss"|"pratt_truss"|"howe_truss"|"simply_supported_beam"|"arch"}
2. add_node: {"node_id": "n1", "x": 0.0, "y": 0.0}
3. add_member: {"member_id": "m1", "node_start": "n1", "node_end": "n2", "material": "steel"|"concrete"|"timber", "section_area": 0.01}
4. add_support: {"node_id": "n1", "support_type": "pin"|"roller"}
5. add_load: {"node_id": "n2", "Fx": 0.0, "Fy": -50.0}
6. simulate: {} (run structural analysis)
7. submit: {} (finalize design, only after simulate passes)

Design guidelines:
- Place supports at both ends of the span (pin on left, roller on right)
- Bottom chord nodes along y=0, top chord nodes elevated
- Connect all nodes with members to form a rigid truss
- Apply the load as a downward force (negative Fy in kN) at the top center or deck nodes
- Use steel with section_area between 0.005 and 0.02 m²
- After simulate, check results. If stress_ratio > 1.0, increase section areas. If deflection is high, add more members.
- Submit only when simulation passes (structural_status == "pass")

Units: coordinates in meters, forces in kN, areas in m².
Reply with ONLY the JSON action object. No other text.""")


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


def format_observation(obs) -> str:
    parts = [
        f"Scenario: {obs.scenario}",
        f"Bridge type: {obs.bridge_type or 'not selected'}",
        f"Nodes ({len(obs.nodes)}): {json.dumps(obs.nodes)}",
        f"Members ({len(obs.members)}): {json.dumps(obs.members)}",
        f"Supports ({len(obs.supports)}): {json.dumps(obs.supports)}",
        f"Loads ({len(obs.loads)}): {json.dumps(obs.loads)}",
        f"Constraints: {json.dumps(obs.constraints)}",
        f"Step: {obs.step_count}",
        f"Message: {obs.message}",
    ]
    if obs.simulation_result:
        parts.append(f"Simulation result: {json.dumps(obs.simulation_result)}")
    return "\n".join(parts)


def fallback_action(obs) -> Optional[Dict]:
    if obs.simulation_result and obs.simulation_result.get("structural_status") == "pass":
        return {"action_type": "submit", "params": {}}
    if obs.nodes and obs.members and obs.supports and obs.loads:
        if obs.simulation_result is None:
            return {"action_type": "simulate", "params": {}}
        return {"action_type": "submit", "params": {}}
    return None


def get_model_action(client: OpenAI, obs, history: List[Dict]) -> Optional[Dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for h in history[-6:]:
        messages.append({"role": "assistant", "content": json.dumps(h["action"])})
        messages.append({"role": "user", "content": h["observation"]})

    messages.append({"role": "user", "content": format_observation(obs)})

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return fallback_action(obs)


async def run_task(task_id: str, llm: OpenAI) -> float:
    if IMAGE_NAME:
        env = await BridgeForgeEnv.from_docker_image(IMAGE_NAME)
    else:
        base_url = os.getenv("ENV_BASE_URL", "http://localhost:8000")
        env = BridgeForgeEnv(base_url=base_url)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(scenario_id=task_id)
        obs = result.observation
        history: List[Dict] = []
        consecutive_failures = 0

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            action_dict = get_model_action(llm, obs, history)

            if action_dict is None:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    print("[DEBUG] LLM unavailable and no valid fallback. Ending task.", flush=True)
                    break
                continue
            else:
                consecutive_failures = 0

            action_type = action_dict.get("action_type", "simulate")
            params = action_dict.get("params", {})

            try:
                action = BridgeForgeAction(action_type=action_type, params=params)
            except Exception:
                action = BridgeForgeAction(action_type="simulate", params={})
                action_dict = {"action_type": "simulate", "params": {}}

            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            error = obs.message if "not found" in obs.message.lower() or "invalid" in obs.message.lower() or "cannot" in obs.message.lower() else None

            rewards.append(reward)
            steps_taken = step

            action_str = f"{action_type}({json.dumps(params)})"
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            history.append({
                "action": action_dict,
                "observation": format_observation(obs),
            })

            if done:
                break

        score = rewards[-1] if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score > 0.0

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    llm = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = []
    for task_id in TASKS:
        score = await run_task(task_id, llm)
        scores.append(score)

    avg = sum(scores) / len(scores) if scores else 0.0
    print(f"\n[SUMMARY] tasks={len(TASKS)} avg_score={avg:.2f} scores={','.join(f'{s:.2f}' for s in scores)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
