import numpy as np
import pandas as pd
import pytest

from quantlib import backtest, stats
from quantlib.evaluate import evaluate, score_all


def market(n=1500, k=4, seed=0, drift=0.0003):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    cols = [f"S{i}" for i in range(k)]
    oc = pd.DataFrame(rng.normal(drift, 0.01, (n, k)), idx, cols)   # open -> close
    co = pd.DataFrame(rng.normal(0, 0.004, (n, k)), idx, cols)      # close -> next open
    closes = 100 * ((1 + oc) * (1 + co)).cumprod()
    opens = closes / (1 + oc)
    return opens, closes


def test_no_lookahead_signal_on_close_cannot_capture_same_day():
    opens, closes = market()
    # "Cheating" signal: hold the asset on days it goes up open->close, known only at the close.
    up = (closes / opens - 1) > 0
    target = up.astype(float) / up.shape[1]
    res = backtest.run(target, opens, closes, fee_bps=0, slip_bps=0, delay=1)
    # If the engine leaked the same-day move, Sharpe would be enormous. It must look like noise.
    assert abs(stats.sharpe(res["net"], 252)) < 1.5


def test_delay_zero_is_refused():
    opens, closes = market(100)
    with pytest.raises(ValueError):
        backtest.run(closes * 0, opens, closes, fee_bps=0, slip_bps=0, delay=0)


def test_leverage_and_shorts_are_refused():
    opens, closes = market(100)
    with pytest.raises(ValueError):
        backtest.run(closes * 0 + 0.5, opens, closes, fee_bps=0, slip_bps=0)
    with pytest.raises(ValueError):
        backtest.run(closes * 0 - 0.1, opens, closes, fee_bps=0, slip_bps=0)


def test_buy_and_hold_matches_price_return_and_costs_are_charged():
    opens, closes = market(300, k=1)
    target = closes * 0 + 1.0
    free = backtest.run(target, opens, closes, fee_bps=0, slip_bps=0)
    # Bought at the open of day 1 (delay=1), held to the last close.
    expected = closes.iloc[-1, 0] / opens.iloc[1, 0] - 1
    assert stats.total_return(free["net"]) == pytest.approx(expected, rel=1e-9)
    paid = backtest.run(target, opens, closes, fee_bps=5, slip_bps=10)
    assert paid["cost"].sum() == pytest.approx(15 / 1e4)   # one entry of 100 % notional
    assert paid["entries"] == 1


def test_max_drawdown_and_sharpe():
    r = pd.Series([0.10, -0.50, 0.20])
    assert stats.max_drawdown(r) == pytest.approx(0.5)
    assert stats.sharpe(pd.Series([0.01] * 10), 252) == 0.0   # zero variance: no Sharpe


def test_deflated_sharpe_falls_with_more_trials():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.0008, 0.01, 1000))
    one = stats.deflated_sharpe(r, 1, 0.03)
    many = stats.deflated_sharpe(r, 200, 0.03)
    assert 0 <= many < one <= 1
    assert stats.expected_max_sharpe(200, 0.03) > stats.expected_max_sharpe(10, 0.03) > 0


def test_monte_carlo_is_reproducible_and_worse_than_sample():
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.0003, 0.01, 1000))
    a, b = stats.monte_carlo_drawdown(r), stats.monte_carlo_drawdown(r)
    assert a == b and a["runs"] == 1000
    assert a["worst"] >= a["p95"] > 0


def test_noise_strategy_is_killed_and_scores_are_in_range():
    opens, closes = market(seed=3, drift=0.0)
    rng = np.random.default_rng(4)
    target = pd.DataFrame((rng.random(closes.shape) > 0.5) / closes.shape[1], closes.index, closes.columns)
    rep = evaluate("noise", target, opens, closes, oos_start="2021-01-01", periods=252, fee_bps=0, slip_bps=10)
    out = score_all([rep], save=False)[0]
    assert out["verdict"] == "KILL"
    assert all(1 <= v <= 5 for v in out["scores"].values())
    assert out["score"] == sum(out["scores"].values())
    assert out["trades"] > 30
