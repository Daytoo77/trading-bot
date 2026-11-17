"""Lookahead-safe daily backtest from target weights.

Timing convention (the only one allowed on the desk)
- target.loc[t] is decided with data up to and including the CLOSE of day t.
- With delay=1 it is executed at the OPEN of day t+1. delay=2 is the "one bar late" test.
- Long only, no leverage: weights must be >= 0 and sum to <= 1 on every day.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def run(target: pd.DataFrame, opens: pd.DataFrame, closes: pd.DataFrame, *,
        fee_bps: float, slip_bps: float, delay: int = 1) -> dict:
    """Return daily net returns, positions, turnover and entry count.

    fee_bps and slip_bps are charged per unit of traded notional, on each side.
    """
    if delay < 1:
        raise ValueError("delay must be >= 1: same-bar execution is lookahead")
    cols = target.columns
    opens, closes = opens[cols], closes[cols]
    target = target.reindex(closes.index).fillna(0.0)
    if (target.values < -1e-12).any():
        raise ValueError("negative weight: the desk is long only")
    if (target.sum(axis=1) > 1 + 1e-9).any():
        raise ValueError("weights sum above 1: the desk uses no leverage")

    pos = target.shift(delay).fillna(0.0)          # held during the session of each day
    tradable = opens.notna() & closes.notna()
    pos = pos.where(tradable, 0.0)                 # cannot hold what has no price that day
    ret_oc = (closes / opens - 1).fillna(0.0)      # open -> close, earned by today's position
    ret_co = (opens / closes.shift(1) - 1).fillna(0.0)  # prev close -> open, earned by yesterday's
    prev = pos.shift(1).fillna(0.0)
    # Overnight leg on yesterday's book, then the session leg on today's book (compounded).
    # Weights are treated as held constant between target changes; drift rebalancing is not charged.
    gross = (1 + (prev * ret_co).sum(axis=1)) * (1 + (pos * ret_oc).sum(axis=1)) - 1
    turnover = (pos - prev).abs().sum(axis=1)
    cost = turnover * (fee_bps + slip_bps) / 1e4
    entries = int(((pos > 0) & (prev <= 0)).sum().sum())
    return {"net": gross - cost, "gross": gross, "cost": cost, "pos": pos,
            "turnover": turnover, "entries": entries}


def capacity_estimate(pos: pd.DataFrame, closes: pd.DataFrame, volumes: pd.DataFrame,
                      participation: float = 0.01) -> float:
    """ESTIMATE of capital the strategy can carry: 5th percentile, over all held positions,
    of (participation x 20-day median dollar volume) / weight."""
    dv = (closes * volumes).rolling(20).median()[pos.columns].reindex(pos.index)
    cap = (participation * dv / pos.where(pos > 0)).stack()
    cap = cap[np.isfinite(cap)]
    return float(cap.quantile(0.05)) if len(cap) else float("nan")
