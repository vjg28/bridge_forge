# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from models import BridgeForgeAction, BridgeForgeObservation


class BridgeForgeEnv(
    EnvClient[BridgeForgeAction, BridgeForgeObservation, State]
):
    def _step_payload(self, action: BridgeForgeAction) -> Dict:
        return {
            "action_type": action.action_type,
            "params": action.params,
        }

    def _parse_result(self, payload: Dict) -> StepResult[BridgeForgeObservation]:
        obs_data = payload.get("observation", {})
        observation = BridgeForgeObservation(
            scenario=obs_data.get("scenario", ""),
            bridge_type=obs_data.get("bridge_type"),
            nodes=obs_data.get("nodes", []),
            members=obs_data.get("members", []),
            supports=obs_data.get("supports", []),
            loads=obs_data.get("loads", []),
            simulation_result=obs_data.get("simulation_result"),
            constraints=obs_data.get("constraints", {}),
            step_count=obs_data.get("step_count", 0),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            message=obs_data.get("message", ""),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
