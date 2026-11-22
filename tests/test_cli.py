import datetime
import json

import cli
from breadth import build_analysis
from synthetic import make_market


def test_cli_json_and_csv(monkeypatch, tmp_path, capsys):
    uni, data = make_market()
    monkeypatch.setattr(cli, "run", lambda kind, index, s, e, y: build_analysis(uni, data, s, e))
    out_csv = tmp_path / "panel.csv"
    rc = cli.main(["--universe", "US Indexes", "--index", "S&P 500", "--start", "2026-09-01",
                   "--end", "2026-11-20", "--csv", str(out_csv), "--json"])
    assert rc == 0 and out_csv.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["asof"] == "2026-11-20" and payload["snapshot"]["Regime"] in {
        "STRONG", "HEALTHY", "NEUTRAL", "WEAK", "WASHOUT"}
    assert isinstance(payload["snapshot"]["Advances"], int)


def test_cli_text(monkeypatch, capsys):
    uni, data = make_market()
    monkeypatch.setattr(cli, "run", lambda kind, index, s, e, y: build_analysis(uni, data, s, e))
    assert cli.main(["--end", "2026-11-20", "--start", str(datetime.date(2026, 10, 1))]) == 0
    text = capsys.readouterr().out
    assert "breadth as of 20 Nov 2026" in text and "**" not in text
