"""Synthetic market with a common factor, sector factors and regime swings."""

import numpy as np
import pandas as pd

from breadth.data import MarketData
from breadth.universe import Universe


def make_market(n_days=900, n_assets=60, seed=0, end="2026-11-20", n_sectors=4):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=end, periods=n_days)
    drift = 0.0012 * np.sin(np.linspace(0, 6 * np.pi, n_days))           # alternating bull/bear phases
    mkt = drift + rng.normal(0, 0.009, n_days)
    sect = rng.normal(0, 0.005, (n_days, n_sectors))
    beta = rng.uniform(0.6, 1.4, n_assets)
    sector_of = np.arange(n_assets) % n_sectors
    rets = mkt[:, None] * beta + sect[:, sector_of] + rng.normal(0, 0.012, (n_days, n_assets))
    tickers = [f"T{i:03d}" for i in range(n_assets)]
    close = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=tickers)
    bench = pd.Series(1000 * np.exp(np.cumsum(mkt)), index=idx, name="BENCH")
    sectors = {t: f"Sector {sector_of[i]}" for i, t in enumerate(tickers)}
    uni = Universe(kind="US Indexes", name="TEST", tickers=tickers, sectors=sectors,
                   names={t: f"Company {t}" for t in tickers}, benchmark="BENCH", source="synthetic")
    data = MarketData(close=close, benchmark=bench, benchmark_ticker="BENCH")
    return uni, data
