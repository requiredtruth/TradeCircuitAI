# TradeCircuitAI

TradeCircuitAI is a deterministic **paper-only** safety boundary for model-generated trading intents. It answers: *would this proposed action pass explicit, replayable risk circuits, and what exact state transition would the paper simulator record?*

```sh
./install.sh
```

The one command runs the tests, compiles every module, and replays bundled synthetic events. It downloads nothing and needs no credentials.

## What it does

- Treats every model intent as untrusted structured input.
- Requires fresh allow-listed quotes and strictly increasing UTC timestamps.
- Enforces maximum order units, position units, gross notional, drawdown, and daily loss.
- Supports an irreversible-in-replay manual halt event.
- Applies explicit adverse slippage to deterministic paper fills.
- Hash-chains every quote, rejection, halt, fill, and resulting account snapshot.
- Recomputes a saved audit report from the original config and events.

It does **not** predict markets, recommend trades, optimize a strategy, connect to an exchange, manage credentials, sign anything, or submit orders.

## Immediate demo

```sh
./run.sh
```

The output contains one synthetic paper fill, an oversized-intent rejection, a manual halt, and a post-halt rejection.

## Use your own replay

```sh
python -m tradecircuitai replay config.json events.jsonl --output audit.json
python -m tradecircuitai verify config.json events.jsonl audit.json
```

Useful failure strings are stable and explicit:

```text
error: event timestamps must strictly increase
"reasons": ["max_order_units", "max_position_units"]
"reasons": ["stale_quote"]
"reasons": ["manual_halt"]
```

## Why this is separate from a backtester

A backtester measures strategy behavior over historical data. TradeCircuitAI models the policy boundary between any proposal source—including an LLM—and a paper account. Its artifact is a decision audit: which gate fired, whether state changed, and a hash-chain head for exact replay. The model cannot override a circuit.

## Limitations

- Paper fills are deliberately simple: the current quote plus configured adverse slippage, with no queue, latency, liquidity, fees, funding, borrow, or partial fills.
- Drawdown and daily loss use the latest supplied quotes; missing quotes are not invented.
- A hash chain reveals later modification when recomputed; it is not a signature or external timestamp.
- Inputs can still be unrealistic or biased. Determinism does not make a simulation predictive.
- This is research/measurement software, not financial advice or a production risk system.

## Support

Donations can fund more production and may request priority for a compatible paper-only direction by opening the issue template with a public transaction hash. They do not guarantee implementation or purchase support, ownership, returns, or preference. See [SUPPORT.md](SUPPORT.md) and verify the asset and network before sending.

Apache-2.0 licensed.


## Standard launcher

`./run.sh` is the normal entry point. It runs `./install.sh` automatically when setup is missing, then opens the PySide6 control panel with live output and actions for the demo, tests, repair, and stop. Use `./cli.sh` for CLI-only operation.
