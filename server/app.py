# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import BridgeForgeAction, BridgeForgeObservation
    from .bridge_forge_environment import BridgeForgeEnvironment
except (ImportError, ValueError):
    from models import BridgeForgeAction, BridgeForgeObservation
    from server.bridge_forge_environment import BridgeForgeEnvironment

app = create_app(
    BridgeForgeEnvironment,
    BridgeForgeAction,
    BridgeForgeObservation,
    env_name="bridge_forge",
    max_concurrent_envs=4,
)

STATIC_DIR = "/tmp/bridge_forge_static"
os.makedirs(STATIC_DIR, exist_ok=True)

from starlette.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
