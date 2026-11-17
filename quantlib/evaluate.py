"""One standard evaluation and one standard score for every strategy on the desk.

Usage
    rep = evaluate("name", target, opens, closes, volumes, oos_start="2022-01-01",
                   periods=252, fee_bps=0, slip_bps=10)
    reports = score_all([rep, ...])   # adds deflated Sharpe, the 5 scores, total and verdict
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest, stats

TRIALS = Path(__file__).resolve().parent.parent / "desk" / "trials.json"
KEEP_SCORE = 18  # out of 25


def evaluate(name: str, target: pd.DataFrame, opens: pd.DataFrame, closes: pd.DataFrame,
             volumes: pd.DataFrame | None = None, *, oos_start: str, periods: int,
             fee_bps: float, slip_bps: float, thesis: str = "", loser: str = "") -> dict:
    """Run the base backtest plus the stress versions and collect every number the brief needs.

    oos_start: first out-of-sample date. Parameters must have been chosen ONLY on data before it.
    periods: 252 for stocks, 365 for crypto.
    """
    base = backtest.run(target, opens, closes, fee_bps=fee_bps, slip_bps=slip_bps, delay=1)
    stress = backtest.run(target, opens, closes, fee_bps=fee_bps, slip_bps=2 * slip_bps, delay=2)
    free = backtest.run(target, opens, closes, fee_bps=0, slip_bps=0, delay=1)
    # Only score the period where the strategy could trade at all.
    active = base["pos"].sum(axis=1) > 0
    if not active.any():
        raise ValueError(f"{name}: never holds a position")
    first = active.idxmax()
    net = base["net"].loc[first:]
    oos_ts = pd.Timestamp(oos_start)
    is_r, oos_r = net[net.index < oos_ts], net[net.index >= oos_ts]
    oos_stress = stress["net"].loc[first:]
    oos_stress = oos_stress[oos_stress.index >= oos_ts]
    oos_free = free["net"].loc[first:]
    oos_free = oos_free[oos_free.index >= oos_ts]
    pos = base["pos"]
    prev = pos.shift(1).fillna(0.0)
    ent = ((pos > 0) & (prev <= 0)).sum(axis=1)
    yr = stats.yearly(net, periods)
    rep = {
        "name": name, "thesis": thesis, "loser": loser,
        "start": str(net.index[0].date()), "end": str(net.index[-1].date()), "oos_start": oos_start,
        "fee_bps": fee_bps, "slip_bps": slip_bps, "periods": periods,
        "is": _block(is_r, periods), "oos": _block(oos_r, periods),
        "oos_stress_sharpe": stats.sharpe(oos_stress, periods),      # 1 bar late + double slippage
        "oos_gross_sharpe": stats.sharpe(oos_free, periods),         # before any cost
        "oos_cost_drag_ann": float((oos_free.mean() - oos_r.mean()) * periods),
        "trades": int(ent.sum()), "trades_oos": int(ent[ent.index >= oos_ts].sum()),
        "avg_net_bps_per_trade": float(net.sum() / max(ent.sum(), 1) * 1e4),
        "exposure": float(active.loc[first:].mean()),
        "mc": stats.monte_carlo_drawdown(net),
        "wf": stats.walk_forward_stability(oos_r, periods),
        "y2020": _year(yr, 2020), "y2022": _year(yr, 2022),
        "yearly": {int(k): {c: round(float(v[c]), 4) for c in ("ret", "sharpe", "max_dd")}
                   for k, v in yr.iterrows()},
        "capacity_est": (backtest.capacity_estimate(pos, closes, volumes)
                         if volumes is not None else float("nan")),
        "_oos_sr_daily": float(oos_r.mean() / oos_r.std(ddof=1)) if oos_r.std(ddof=1) > 0 else 0.0,
        "_oos_returns": oos_r,
    }
    return rep


def _block(r: pd.Series, periods: int) -> dict:
    return {"days": int(len(r)), "ret": stats.total_return(r), "sharpe": stats.sharpe(r, periods),
            "max_dd": stats.max_drawdown(r)}


def _year(yr: pd.DataFrame, y: int) -> dict | None:
    if y not in yr.index:
        return None
    return {c: round(float(yr.loc[y, c]), 4) for c in ("ret", "sharpe", "max_dd")}


def load_trials() -> list[dict]:
    return json.loads(TRIALS.read_text()) if TRIALS.exists() else []


def _band(x: float, cuts: list[float]) -> int:
    """1 + number of thresholds reached: _band(0.7, [0, .5, 1, 1.5]) == 3."""
    return 1 + sum(x >= c for c in cuts)


def score_all(reports: list[dict], date: str | None = None, save: bool = True) -> list[dict]:
    """Add deflated Sharpe (counting EVERY idea ever tested on the desk), the five 1-5 scores,
    the total out of 25, the hard gates and the verdict. Appends tonight's trials to desk/trials.json."""
    history = load_trials()
    srs = [t["sr_daily"] for t in history] + [r["_oos_sr_daily"] for r in reports]
    n_trials = len(srs)
    sr_std = float(np.std(srs, ddof=1)) if n_trials > 1 else 0.0
    for r in reports:
        oos = r["oos"]
        dsr = stats.deflated_sharpe(r["_oos_returns"], n_trials, sr_std)
        r["dsr"], r["n_trials"] = dsr, n_trials
        s_sharpe = _band(oos["sharpe"], [0.0001, 0.5, 1.0, 1.5])
        if dsr < 0.5:
            s_sharpe = min(s_sharpe, 2)   # indistinguishable from the luckiest of n_trials
        elif dsr < 0.8:
            s_sharpe = min(s_sharpe, 3)
        keep = r["oos_stress_sharpe"] / oos["sharpe"] if oos["sharpe"] > 0 else 0.0
        r["scores"] = {
            "oos_sharpe": s_sharpe,
            "max_drawdown": 6 - _band(max(oos["max_dd"], r["is"]["max_dd"]), [0.10, 0.20, 0.30, 0.40]),
            "trades": _band(r["trades"], [30, 60, 120, 250]),
            "edge_after_costs": 1 if r["oos_stress_sharpe"] <= 0 else _band(keep, [0, 0.25, 0.5, 0.75]),
            "walk_forward": _band(r["wf"]["positive_share"], [0.4, 0.55, 0.7, 0.85]),
        }
        r["score"] = int(sum(r["scores"].values()))
        gates = {
            "survives_oos": oos["sharpe"] > 0,
            "edge_after_costs": oos["sharpe"] > 0 and r["oos_gross_sharpe"] > 0,
            "one_bar_late_double_slippage": r["oos_stress_sharpe"] > 0,
            "at_least_30_trades": r["trades"] >= 30,
            "survived_2020_2022": all(y is None or y["max_dd"] < 0.35 for y in (r["y2020"], r["y2022"]))
                                  and any(y is not None for y in (r["y2020"], r["y2022"])),
        }
        r["gates"] = gates
        r["verdict"] = "KEEP" if r["score"] >= KEEP_SCORE and all(gates.values()) else "KILL"
    if save:
        history += [{"date": date or str(pd.Timestamp.now(tz="UTC").date()), "name": r["name"],
                     "sr_daily": r["_oos_sr_daily"], "score": r["score"], "verdict": r["verdict"]}
                    for r in reports]
        TRIALS.parent.mkdir(exist_ok=True)
        TRIALS.write_text(json.dumps(history, indent=1))
    return sorted(reports, key=lambda r: (r["verdict"] == "KEEP", r["score"], r["oos"]["sharpe"]), reverse=True)


def public(rep: dict) -> dict:
    """Report without the private working fields, ready for json.dump."""
    return {k: v for k, v in rep.items() if not k.startswith("_")}
