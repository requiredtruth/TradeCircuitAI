#!/usr/bin/env sh
set -eu
python -m unittest discover -s tests -v
python -m compileall -q tradecircuitai tests
./run.sh >/dev/null
echo "TradeCircuitAI verification complete"
