# Project specification

TradeCircuitAI is a deterministic paper simulator and policy boundary. It consumes quotes and untrusted model intents from files, rejects malformed or risk-limit-breaking actions, and records every outcome in a hash-chained audit report.

It never connects to a network, broker, exchange, wallet, or signing service. It cannot place a live order. Rejected intents never mutate cash or positions. All timestamps must increase, all symbols must be allow-listed, and all arithmetic uses decimal values.
