import copy
import json

import pytest
from test_core_cli import tracker

from manuscript_prop_tracker.cli import main
from manuscript_prop_tracker.core import evaluate, render_markdown


def test_transfer_move_resolution_and_unchanged():
    data = tracker()
    data["props"][0]["events"][1]["location"] = "Dock"
    data["props"].append(
        {
            "id": "fixed",
            "name": "Stone",
            "events": [{"milestone": "Chapter 1", "action": "introduced", "location": "Garden"}],
        }
    )
    original = copy.deepcopy(data)
    report = evaluate(data, "Chapter 2", compare_from="Chapter 1")
    props = report["comparison"]["props"]
    assert props[0]["changed_fields"] == ["owner", "location"]
    assert props[0]["before"] == {"owner": "Mara", "location": "Workshop", "status": "active"}
    assert props[0]["after"]["owner"] == "Ilan"
    assert props[1]["changed_fields"] == []
    assert (
        evaluate(data, "Chapter 3", compare_from="Chapter 2")["comparison"]["props"][0]["after"][
            "status"
        ]
        == "resolved"
    )
    assert "Milestone comparison" in render_markdown(report)
    assert data == original
    assert "comparison" not in evaluate(data)


def test_no_future_evidence_or_prop_names_and_warnings_stay():
    data = tracker()
    data["props"].append(
        {
            "id": "secret",
            "name": "Future reveal",
            "events": [{"milestone": "Chapter 3", "action": "introduced", "note": "SECRET"}],
        }
    )
    data["props"][0]["events"][1]["from_owner"] = "Wrong"
    data["props"][0]["events"][2]["note"] = "SECRET"
    report = evaluate(data, "Chapter 2", compare_from="Chapter 1")
    assert "SECRET" not in json.dumps(report)
    assert "Future reveal" not in json.dumps(report)
    assert report["issue_count"] == 1
    assert "transfer expects Wrong" in report["comparison"]["props"][0]["issues"][0]
    data["props"][0]["events"].append({"milestone": "Chapter 3", "action": "moved"})
    assert (
        "after resolved"
        in evaluate(data, "Chapter 3", compare_from="Chapter 2")["props"][0]["issues"][-1]
    )


@pytest.mark.parametrize(
    "start,end",
    [("bad", "Chapter 2"), ("Chapter 3", "Chapter 1"), ("Chapter 1", None), ("Chapter 1", "bad")],
)
def test_invalid_boundaries(start, end):
    with pytest.raises(ValueError):
        evaluate(tracker(), end, compare_from=start)


def test_equal_boundaries_and_cli(tmp_path, capsys):
    data = tracker()
    assert (
        evaluate(data, "Chapter 1", compare_from="Chapter 1")["comparison"]["props"][0][
            "changed_fields"
        ]
        == []
    )
    path = tmp_path / "props.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    original = path.read_bytes()
    assert (
        main(
            [str(path), "--compare-from", "Chapter 1", "--through", "Chapter 2", "--format", "json"]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["comparison"]["from"] == "Chapter 1"
    assert main([str(path), "--compare-from", "Chapter 1"]) == 2
    assert path.read_bytes() == original
