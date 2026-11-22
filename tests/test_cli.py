import datetime
import json

import cli
from breadth import build_analysis
from synthetic import make_market


def fake_run(uni, data):
    return lambda kind, index, s, e, y: build_analysis(uni, data, s, e)


def test_cli_json_and_csv(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "run", fake_run(*make_market()))
    out_csv = tmp_path / "daily.csv"
    rc = cli.main(["--universe", "US Indexes", "--index", "S&P 500", "--asof", "2026-11-20",
                   "--csv", str(out_csv), "--json"])
    assert rc == 0 and out_csv.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["asof"] == "2026-11-20" and payload["zone"] in {"OVERSOLD", "NEUTRAL", "OVERBOUGHT"}
    assert isinstance(payload["latest"]["Advances"], int) and payload["reading"] and payload["watch"]
    assert "**" not in json.dumps(payload)


def test_cli_text(monkeypatch, capsys):
    monkeypatch.setattr(cli, "run", fake_run(*make_market()))
    assert cli.main(["--asof", str(datetime.date(2026, 11, 20))]) == 0
    text = capsys.readouterr().out
    assert "breadth is" in text and "as of 20 Nov 2026" in text and "What would change it" in text
    assert "**" not in text
