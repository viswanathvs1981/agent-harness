from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from home_control.app import create_app
from home_control.brain import ensure_anthropic_key
from home_control.hub import Hub


def main() -> None:
    parser = argparse.ArgumentParser(description="Control TVs and other devices on this Wi-Fi.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--demo", action="store_true", help="Load sample devices (no LAN required).")
    parser.add_argument("--plugin", help="Path to tv.py with discover() and command().")
    parser.add_argument(
        "--reset-claude-key",
        action="store_true",
        help="Ask for the Anthropic key again and overwrite ~/.room/anthropic.key.",
    )
    parser.add_argument(
        "--skip-claude",
        action="store_true",
        help="Do not prompt for a Claude key; use local phrase matching.",
    )
    args = parser.parse_args()
    if args.demo:
        os.environ["HOME_CONTROL_DEMO"] = "1"
    key = ensure_anthropic_key(reset=args.reset_claude_key, prompt=not args.skip_claude)
    store = Path.home() / ".room" / "state.json"
    hub = Hub(demo=args.demo, plugin_path=args.plugin, store_path=store, anthropic_key=key)
    bind = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    mode = "DEMO (fake TVs)" if args.demo else "LIVE (this Mac's Wi-Fi)"
    brain = "Claude" if key else "local rules"
    print(
        f"Room {mode}, agent={brain}: open http://{bind}:{args.port} in Safari on this Mac",
        flush=True,
    )
    uvicorn.run(create_app(hub, monitor=True), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
