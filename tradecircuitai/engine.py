"""Deterministic paper execution and pre-trade circuits."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from .core import CircuitError, Config, decimal, timestamp


def text(value: Decimal) -> str:
    rendered = format(value.quantize(Decimal("0.00000001")), "f")
    return rendered.rstrip("0").rstrip(".") or "0"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class State:
    cash: Decimal
    positions: dict[str, Decimal]
    quotes: dict[str, tuple[Decimal, datetime]] = field(default_factory=dict)
    peak_equity: Decimal = Decimal(0)
    day_start_equity: dict[str, Decimal] = field(default_factory=dict)
    halted: bool = False
    previous_time: datetime | None = None
    previous_hash: str = "0" * 64


def replay(config: Config, events: list[Any]) -> dict[str, Any]:
    state = State(config.initial_cash, {symbol: Decimal(0) for symbol in config.symbols}, peak_equity=config.initial_cash)
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        record = process(config, state, event, index)
        record["previous_hash"] = state.previous_hash
        record["record_hash"] = digest(record)
        state.previous_hash = record["record_hash"]
        records.append(record)
    return {
        "schema": "tradecircuitai/paper-audit-1",
        "mode": "paper_only",
        "records": records,
        "final": snapshot(state),
        "audit_head": state.previous_hash,
    }


def equity(state: State) -> Decimal:
    return state.cash + sum(state.positions[s] * state.quotes[s][0] for s in state.positions if s in state.quotes)


def snapshot(state: State) -> dict[str, Any]:
    return {"cash": text(state.cash), "positions": {k: text(v) for k, v in sorted(state.positions.items())}, "equity": text(equity(state)), "halted": state.halted}


def process(config: Config, state: State, event: Any, index: int) -> dict[str, Any]:
    if not isinstance(event, dict) or "type" not in event or "timestamp" not in event:
        raise CircuitError(f"event {index} requires type and timestamp")
    now = timestamp(event["timestamp"])
    if state.previous_time is not None and now <= state.previous_time:
        raise CircuitError("event timestamps must strictly increase")
    state.previous_time = now
    kind = event["type"]
    if kind == "quote":
        if set(event) != {"type", "timestamp", "symbol", "price"}:
            raise CircuitError("quote fields are incomplete or unexpected")
        symbol = symbol_for(config, event)
        price = decimal(event["price"], "price", positive=True)
        state.quotes[symbol] = (price, now)
        current = equity(state)
        state.peak_equity = max(state.peak_equity, current)
        state.day_start_equity.setdefault(now.date().isoformat(), current)
        return base(index, event, "quote_accepted", state, {"price": text(price)})
    if kind == "halt":
        if set(event) != {"type", "timestamp", "reason"} or not isinstance(event["reason"], str) or not event["reason"].strip():
            raise CircuitError("halt requires a non-empty reason")
        state.halted = True
        return base(index, event, "halted", state, {"reason": event["reason"][:200]})
    if kind != "intent" or set(event) != {"type", "timestamp", "symbol", "side", "units", "model_ref"}:
        raise CircuitError("event type or fields are unsupported")
    symbol = symbol_for(config, event)
    side = event["side"]
    if side not in {"buy", "sell"}:
        raise CircuitError("intent side must be buy or sell")
    units = decimal(event["units"], "units", positive=True)
    model_ref = event["model_ref"]
    if not isinstance(model_ref, str) or not model_ref or len(model_ref) > 128:
        raise CircuitError("model_ref must be a short non-empty identifier")
    reasons: list[str] = []
    quote = state.quotes.get(symbol)
    if state.halted: reasons.append("manual_halt")
    if quote is None: reasons.append("missing_quote")
    elif (now - quote[1]).total_seconds() > config.max_quote_age_seconds: reasons.append("stale_quote")
    if units > config.max_order_units: reasons.append("max_order_units")
    delta = units if side == "buy" else -units
    next_position = state.positions[symbol] + delta
    if abs(next_position) > config.max_position_units: reasons.append("max_position_units")
    if quote is not None:
        projected = dict(state.positions); projected[symbol] = next_position
        gross = sum(abs(projected[s] * state.quotes[s][0]) for s in projected if s in state.quotes)
        if gross > config.max_gross_notional: reasons.append("max_gross_notional")
        current = equity(state)
        drawdown = (state.peak_equity - current) / state.peak_equity * 100 if state.peak_equity else Decimal(0)
        if drawdown >= config.max_drawdown_percent: reasons.append("max_drawdown")
        day = now.date().isoformat(); start = state.day_start_equity.setdefault(day, current)
        if start - current >= config.max_daily_loss: reasons.append("max_daily_loss")
    if reasons:
        return base(index, event, "rejected", state, {"reasons": sorted(set(reasons)), "model_ref": model_ref})
    assert quote is not None
    multiplier = Decimal(1) + (config.slippage_bps / Decimal(10000)) * (Decimal(1) if side == "buy" else Decimal(-1))
    fill = quote[0] * multiplier
    state.cash -= delta * fill
    state.positions[symbol] = next_position
    current = equity(state)
    state.peak_equity = max(state.peak_equity, current)
    return base(index, event, "paper_fill", state, {"side": side, "units": text(units), "fill_price": text(fill), "model_ref": model_ref})


def symbol_for(config: Config, event: dict[str, Any]) -> str:
    symbol = event.get("symbol")
    if symbol not in config.symbols:
        raise CircuitError(f"symbol is not allow-listed: {symbol}")
    return symbol


def base(index: int, event: dict[str, Any], outcome: str, state: State, details: dict[str, Any]) -> dict[str, Any]:
    return {"index": index, "timestamp": event["timestamp"], "type": event["type"], "outcome": outcome, "details": details, "state": snapshot(state)}


def verify(config: Config, events: list[Any], report: Any) -> bool:
    return isinstance(report, dict) and digest(replay(config, events)) == digest(report)
