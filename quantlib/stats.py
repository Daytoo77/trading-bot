"""Performance statistics: Sharpe, drawdown, deflated Sharpe, Monte Carlo, walk-forward."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

N = NormalDist()
EULER = 0.5772156649015329


def sharpe(r: pd.Series, periods: int) -> float:
    r = r.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(periods)) if len(r) > 2 and sd > 1e-12 else 0.0


def max_drawdown(r: pd.Series) -> float:
    """Worst peak-to-trough loss as a positive fraction (0.25 = -25 %)."""
    eq = (1 + r.fillna(0)).cumprod()
    return float((1 - eq / eq.cummax()).max()) if len(eq) else 0.0


def total_return(r: pd.Series) -> float:
    return float((1 + r.fillna(0)).prod() - 1)


def expected_max_sharpe(n_trials: int, sr_std: float) -> float:
    """Expected best per-period Sharpe among n_trials strategies with NO real edge
    (Bailey & Lopez de Prado 2014). sr_std = std of per-period Sharpes across trials."""
    if n_trials < 2:
        return 0.0
    return sr_std * ((1 - EULER) * N.inv_cdf(1 - 1 / n_trials)
                     + EULER * N.inv_cdf(1 - 1 / (n_trials * math.e)))


def deflated_sharpe(r: pd.Series, n_trials: int, sr_std: float) -> float:
    """Probability that the true Sharpe is above what luck alone gives after n_trials tests.
    Uses per-period (not annualised) Sharpe, skew and kurtosis of r."""
    r = r.dropna()
    t = len(r)
    sd = r.std(ddof=1)
    if t < 30 or sd < 1e-12:
        return 0.0
    sr = r.mean() / sd
    skew = float(r.skew())
    kurt = float(r.kurt()) + 3.0  # pandas gives excess kurtosis
    sr0 = expected_max_sharpe(n_trials, sr_std)
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if denom <= 0:
        return 0.0
    return float(N.cdf((sr - sr0) * math.sqrt(t - 1) / math.sqrt(denom)))


def monte_carlo_drawdown(r: pd.Series, runs: int = 1000, block: int = 10, seed: int = 7) -> dict:
    """Block-bootstrap the daily returns `runs` times, same length as the sample.
    Returns the worst and the 95th-percentile max drawdown across runs."""
    x = r.dropna().to_numpy()
    n = len(x)
    if n < block * 3:
        return {"worst": float("nan"), "p95": float("nan"), "runs": 0}
    rng = np.random.default_rng(seed)
    k = math.ceil(n / block)
    dds = np.empty(runs)
    for i in range(runs):
        starts = rng.integers(0, n - block + 1, size=k)
        path = np.concatenate([x[s:s + block] for s in starts])[:n]
        eq = np.cumprod(1 + path)
        dds[i] = (1 - eq / np.maximum.accumulate(eq)).max()
    return {"worst": float(dds.max()), "p95": float(np.quantile(dds, 0.95)), "runs": runs}


def yearly(r: pd.Series, periods: int) -> pd.DataFrame:
    g = r.dropna().groupby(r.dropna().index.year)
    return pd.DataFrame({"ret": g.apply(total_return), "sharpe": g.apply(lambda x: sharpe(x, periods)),
                         "max_dd": g.apply(max_drawdown), "days": g.size()})


def walk_forward_stability(r: pd.Series, periods: int, folds: int = 6) -> dict:
    """Split the out-of-sample returns into consecutive folds; share of folds with Sharpe > 0."""
    r = r.dropna()
    if len(r) < folds * 20:
        return {"positive_share": 0.0, "fold_sharpes": []}
    edges = np.linspace(0, len(r), folds + 1).astype(int)
    parts = [r.iloc[a:b] for a, b in zip(edges[:-1], edges[1:])]
    s = [sharpe(p, periods) for p in parts]
    return {"positive_share": float(np.mean([v > 0 for v in s])), "fold_sharpes": [round(v, 2) for v in s]}
