"""Market data loaders. Real data only, each loader names its source.

Sources
- Yahoo Finance chart API (query1.finance.yahoo.com): daily OHLCV, split/dividend adjusted.
- Coinbase Exchange public API (api.exchange.coinbase.com): daily crypto candles.
- Nasdaq screener API (api.nasdaq.com): current listed US stocks with market cap.

Known limits (must be repeated in reports)
- Yahoo and the Nasdaq screener only know companies listed TODAY: delisted names are missing,
  so any small/mid cap backtest built on them is optimistic (survivorship bias).
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import pandas as pd
import requests

CACHE = Path(__file__).resolve().parent.parent / "data_cache"
UA = {"User-Agent": "Mozilla/5.0"}


def _get(url: str, params: dict | None = None, tries: int = 4) -> requests.Response:
    last: Exception | None = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 200:
                return r
            if r.status_code in (400, 404):  # permanent: unknown symbol etc.
                r.raise_for_status()
            last = RuntimeError(f"HTTP {r.status_code} for {url}")
        except requests.HTTPError:
            raise
        except Exception as e:  # network hiccup: retry with backoff
            last = e
        time.sleep(2 ** i)
    raise RuntimeError(f"failed after {tries} tries: {last}")


def _today_utc() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).date())


def _cache_path(kind: str, key: str) -> Path:
    CACHE.mkdir(exist_ok=True)
    safe = key.replace("/", "_").replace("^", "_")
    return CACHE / f"{kind}_{safe}_{_today_utc().date()}.csv"


def yahoo_daily(symbol: str, start: str = "2015-01-01", use_cache: bool = True) -> pd.DataFrame:
    """Daily bars, adjusted for splits and dividends. Columns: open, high, low, close, volume.

    The bar dated today (UTC) is dropped because it may still be forming.
    """
    path = _cache_path("yahoo", f"{symbol}_{start}")
    if use_cache and path.exists():
        return pd.read_csv(path, index_col=0, parse_dates=True)
    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int(time.time())
    r = _get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        {"period1": p1, "period2": p2, "interval": "1d", "events": "div,splits"},
    )
    res = r.json()["chart"]["result"][0]
    if "timestamp" not in res:
        raise RuntimeError(f"no data for {symbol}")
    q = res["indicators"]["quote"][0]
    adj = res["indicators"]["adjclose"][0]["adjclose"]
    df = pd.DataFrame(
        {"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"],
         "volume": q["volume"], "adj": adj},
        index=pd.to_datetime(res["timestamp"], unit="s").normalize(),
    ).dropna(subset=["open", "close", "adj"])
    df = df[~df.index.duplicated(keep="last")]
    f = df["adj"] / df["close"]  # adjustment factor applied to the whole bar
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] * f
    df["volume"] = df["volume"] / f  # keeps dollar volume unchanged
    df = df.drop(columns="adj")
    df = df[df.index < _today_utc()]
    df.index.name = "date"
    df.to_csv(path)
    return df


def coinbase_daily(product: str = "BTC-USD", start: str = "2017-01-01", use_cache: bool = True) -> pd.DataFrame:
    """Daily UTC candles from Coinbase Exchange. The candle still forming today is dropped."""
    path = _cache_path("coinbase", f"{product}_{start}")
    if use_cache and path.exists():
        return pd.read_csv(path, index_col=0, parse_dates=True)
    rows = []
    end = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    first = dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc)
    while end > first:
        s = max(first, end - dt.timedelta(days=299))
        r = _get(
            f"https://api.exchange.coinbase.com/products/{product}/candles",
            {"granularity": 86400, "start": s.isoformat(), "end": end.isoformat()},
        )
        chunk = r.json()
        if not chunk:
            break
        rows += chunk
        end = s - dt.timedelta(days=1)
        time.sleep(0.25)
    df = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"])
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("t"), unit="s")).normalize()
    df = df[~df.index.duplicated()].sort_index()[["open", "high", "low", "close", "volume"]]
    df = df[df.index < _today_utc()]
    df.index.name = "date"
    df.to_csv(path)
    return df


def panel(symbols: list[str], start: str = "2015-01-01", loader=yahoo_daily) -> dict[str, pd.DataFrame]:
    """Load many symbols into aligned frames: {'open','high','low','close','volume'} x symbols.

    Symbols that fail to load are skipped and listed in panel['_missing'].
    """
    frames, missing = {}, []
    for s in symbols:
        try:
            frames[s] = loader(s, start)
        except Exception:
            missing.append(s)
    out = {f: pd.DataFrame({s: d[f] for s, d in frames.items()}).sort_index()
           for f in ("open", "high", "low", "close", "volume")}
    out["_missing"] = missing
    return out


def nasdaq_screener(use_cache: bool = True) -> pd.DataFrame:
    """All US-listed stocks known to Nasdaq's screener TODAY, with market cap in USD.

    Current listings only: using this as a historical universe creates survivorship bias.
    """
    path = _cache_path("nasdaq", "screener")
    if use_cache and path.exists():
        return pd.read_csv(path, index_col=0)
    r = _get("https://api.nasdaq.com/api/screener/stocks", {"tableonly": "true", "download": "true"})
    df = pd.DataFrame(r.json()["data"]["rows"])
    df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df["lastsale"] = pd.to_numeric(df["lastsale"].str.replace("$", "", regex=False), errors="coerce")
    df = df.set_index("symbol")
    df.to_csv(path)
    return df


def small_mid_universe(min_cap: float = 3e8, max_cap: float = 1e10, min_price: float = 5.0,
                       min_dollar_vol: float = 5e6, n: int | None = None) -> list[str]:
    """Today's liquid US small/mid caps (cap 300M to 10B by default), largest dollar volume first."""
    s = nasdaq_screener()
    s = s[(s.marketCap >= min_cap) & (s.marketCap <= max_cap) & (s.lastsale >= min_price)]
    s = s[s.index.str.fullmatch(r"[A-Z]+")]  # drop warrants, units, preferreds
    dv = (s.lastsale * s.volume).sort_values(ascending=False)
    dv = dv[dv >= min_dollar_vol]
    return list(dv.index[:n] if n else dv.index)
