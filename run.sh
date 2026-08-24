#!/usr/bin/env sh
set -eu
python -m tradecircuitai replay tradecircuitai/data/demo_config.json tradecircuitai/data/demo_events.jsonl
