"""Strict configuration and event validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


class CircuitError(ValueError):
    pass


def decimal(value: Any, label: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise CircuitError(f"{label} must be a decimal string or integer")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise CircuitError(f"{label} is not decimal") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise CircuitError(f"{label} must be finite{' and positive' if positive else ''}")
    return result


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CircuitError("timestamp must be canonical UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CircuitError("timestamp must be ISO-8601 UTC") from exc
    if parsed.tzinfo != timezone.utc or parsed.isoformat().replace("+00:00", "Z") != value:
        raise CircuitError("timestamp must be canonical UTC ending in Z")
    return parsed


@dataclass(frozen=True)
class Config:
    initial_cash: Decimal
    symbols: tuple[str, ...]
    max_order_units: Decimal
    max_position_units: Decimal
    max_gross_notional: Decimal
    max_drawdown_percent: Decimal
    max_daily_loss: Decimal
    slippage_bps: Decimal
    max_quote_age_seconds: int


def parse_config(raw: Any) -> Config:
    expected = {"initial_cash", "symbols", "max_order_units", "max_position_units", "max_gross_notional", "max_drawdown_percent", "max_daily_loss", "slippage_bps", "max_quote_age_seconds"}
    if not isinstance(raw, dict) or set(raw) != expected:
        raise CircuitError("config fields are incomplete or unexpected")
    symbols = raw["symbols"]
    if not isinstance(symbols, list) or not symbols or symbols != sorted(set(symbols)):
        raise CircuitError("symbols must be a non-empty sorted unique list")
    if any(not isinstance(x, str) or not x.replace("-", "").isalnum() or x.upper() != x for x in symbols):
        raise CircuitError("symbols must be uppercase identifiers")
    age = raw["max_quote_age_seconds"]
    if type(age) is not int or not 0 <= age <= 86400:
        raise CircuitError("max_quote_age_seconds must be an integer from 0 to 86400")
    drawdown = decimal(raw["max_drawdown_percent"], "max_drawdown_percent", positive=True)
    slip = decimal(raw["slippage_bps"], "slippage_bps")
    if drawdown > 100 or slip < 0 or slip > 1000:
        raise CircuitError("drawdown or slippage bound is unsafe")
    return Config(
        decimal(raw["initial_cash"], "initial_cash", positive=True), tuple(symbols),
        decimal(raw["max_order_units"], "max_order_units", positive=True),
        decimal(raw["max_position_units"], "max_position_units", positive=True),
        decimal(raw["max_gross_notional"], "max_gross_notional", positive=True), drawdown,
        decimal(raw["max_daily_loss"], "max_daily_loss", positive=True), slip, age,
    )
