import pandas as pd
import pytest

from breadth import universe as uv


def offline(*a, **k):
    raise OSError("offline")


def test_normalize_constituent_table_variants():
    nse = pd.DataFrame({"Company Name": ["A Ltd"], "Industry": ["IT"], "Symbol": [" AAA "]})
    out = uv.normalize_constituent_table(nse)
    assert out.to_dict("records") == [{"symbol": "AAA", "sector": "IT", "name": "A Ltd"}]
    wiki = pd.DataFrame({"Company name": ["B"], "Symbol": ["BBB"], "Sector[15]": ["Banks"]})
    assert uv.normalize_constituent_table(wiki).iloc[0]["sector"] == "Banks"
    headerless = pd.DataFrame([["Company Name", "Industry", "Symbol"], ["C", "Auto", "CCC"]])
    assert uv.normalize_constituent_table(headerless).iloc[0]["symbol"] == "CCC"
    assert uv.normalize_constituent_table(pd.DataFrame({"x": [1]})) is None
    dummy = pd.DataFrame({"Symbol": ["AAA", "DUMMYHEG"]})
    assert list(uv.normalize_constituent_table(dummy)["symbol"]) == ["AAA"]


def test_india_fallback_flagged(monkeypatch):
    monkeypatch.setattr(uv.requests, "get", offline)
    u = uv.get_india_universe("NIFTY BANK")
    assert u.is_fallback and u.tickers == uv.FALLBACK_TICKERS and "fallback" in u.source.lower()
    assert u.benchmark == "^NSEBANK"


def test_us_fallback_only_for_dow(monkeypatch):
    monkeypatch.setattr(uv, "_read_html_tables", offline)
    u = uv.get_us_universe("DOW JONES")
    assert u.is_fallback and len(u.tickers) == 30 and "GOOGL" in u.tickers
    with pytest.raises(uv.ConstituentFetchError):
        uv.get_us_universe("S&P 500")


def test_us_universe_maps_share_classes_and_sectors(monkeypatch):
    table = pd.DataFrame({"Symbol": [f"T{i}" for i in range(499)] + ["BRK.B"], "GICS Sector": ["Fin"] * 500,
                          "Security": ["x"] * 500})
    monkeypatch.setattr(uv, "_read_html_tables", lambda url: [table])
    u = uv.get_us_universe("S&P 500")
    assert "BRK-B" in u.tickers and u.sectors["BRK-B"] == "Fin" and u.benchmark == "^GSPC"


def test_currency_universe_orientation():
    u = uv.resolve_universe(uv.CURRENCY)
    assert "USDJPY=X" in u.invert and "EURUSD=X" not in u.invert
    assert all("USD" in t for t in u.tickers)          # no crosses
    assert u.names["USDJPY=X"] == "JPY" and u.unit == "Assets"


def test_commodity_universe_groups():
    u = uv.resolve_universe(uv.COMMODITIES)
    assert u.sectors["GC=F"] == "Precious Metals" and len(set(u.sectors.values())) == 6
