"""Engine CLI smoke tests."""

import json

from app.engine.__main__ import main


def test_trace_fixture_human_output(capsys):
    code = main(["trace-fixture"])
    out = capsys.readouterr().out
    assert code == 0
    assert "status:      done" in out
    assert "result_hash: aegis.engine.v1:" in out
    assert "taint=" in out


def test_trace_fixture_json_output_is_canonical(capsys):
    code = main(["trace-fixture", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["start_address"]
    assert payload["status"] == "done"
    assert payload["result"]["graph_edges"]


def test_unknown_subcommand_exits_nonzero(capsys):
    try:
        main(["nope"])
    except SystemExit as exc:  # argparse exits on bad subcommand
        assert exc.code != 0
    else:  # pragma: no cover - defensive
        raise AssertionError("expected SystemExit")
