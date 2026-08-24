from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import CircuitError, parse_config
from .engine import replay, verify


def load(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_events(path: str) -> list[object]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tradecircuitai", description="Paper-only model-intent risk circuits")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("replay"); run.add_argument("config"); run.add_argument("events"); run.add_argument("--output")
    check = sub.add_parser("verify"); check.add_argument("config"); check.add_argument("events"); check.add_argument("report")
    args = parser.parse_args(argv)
    try:
        config, events = parse_config(load(args.config)), load_events(args.events)
        if args.command == "replay":
            report = replay(config, events)
            rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
            if args.output: Path(args.output).write_text(rendered, encoding="utf-8")
            else: print(rendered, end="")
        elif not verify(config, events, load(args.report)):
            raise CircuitError("report does not match deterministic replay")
        else:
            print("verified deterministic paper audit")
    except (OSError, json.JSONDecodeError, CircuitError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2
    return 0
