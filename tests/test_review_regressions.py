import copy
import json

import pytest
from test_core_cli import tracker

from manuscript_prop_tracker.cli import main
from manuscript_prop_tracker.core import evaluate, load_tracker, render_markdown


def test_every_bounded_report_hides_future_only_prop_identities():
    data = tracker()
    data["props"].append(
        {
            "id": "SECRET_ID",
            "name": "SECRET_NAME",
            "events": [{"milestone": "Chapter 3", "action": "introduced", "note": "SECRET_NOTE"}],
        }
    )
    data["props"].append({"id": "unused", "name": "unused", "events": []})
    original = copy.deepcopy(data)
    report = evaluate(data, "Chapter 2")
    assert len(report["props"]) == 1
    assert "SECRET" not in json.dumps(report) + render_markdown(report)
    assert data == original
    later = evaluate(data, "Chapter 3", compare_from="Chapter 2")["comparison"]["props"][-1]
    assert later["id"] == "SECRET_ID"
    assert later["before"] == {"owner": None, "location": None, "status": "not introduced"}
    assert later["changed_fields"] == ["status"]


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda data: data.update(version=True), "version 1"),
        (lambda data: data["props"][0].update(id=" "), "non-empty"),
        (lambda data: data["props"][0].update(name=" "), "non-empty"),
        (lambda data: data["props"][0]["events"][0].update(action=[]), "invalid event"),
        (lambda data: data["props"][0]["events"][0].update(milestone=[]), "unknown milestone"),
        (lambda data: data["props"][0]["events"][1].update(owner=" "), "requires an owner"),
    ],
)
def test_actionable_invalid_structured_input(tmp_path, change, message):
    data = tracker()
    change(data)
    path = tmp_path / "props.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((TypeError, ValueError), match=message):
        load_tracker(path)


def test_invalid_encoding_and_output_parent_are_cli_errors(tmp_path, capsys):
    source = tmp_path / "props.json"
    source.write_bytes(b"\xff")
    assert main([str(source)]) == 2
    assert "error:" in capsys.readouterr().err
    source.write_text(json.dumps(tracker()), encoding="utf-8")
    parent = tmp_path / "file"
    parent.write_text("keep", encoding="utf-8")
    assert main([str(source), "--output", str(parent / "report.md")]) == 2
    assert "error:" in capsys.readouterr().err
    assert parent.read_text() == "keep"


def test_output_created_by_another_writer_is_preserved(tmp_path, monkeypatch, capsys):
    source = tmp_path / "props.json"
    source.write_text(json.dumps(tracker()), encoding="utf-8")
    output = tmp_path / "report.md"
    original_open = type(output).open
    inserted = False

    def concurrent_open(path, mode="r", *args, **kwargs):
        nonlocal inserted
        if path == output and not inserted:
            inserted = True
            with original_open(path, "w", encoding="utf-8") as stream:
                stream.write("another writer")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(type(output), "open", concurrent_open)
    assert main([str(source), "--output", str(output)]) == 2
    assert output.read_text() == "another writer"
    assert "already exists" in capsys.readouterr().err


def test_unbounded_report_preserves_planned_props_without_events():
    data = tracker()
    data["props"].append({"id": "planned", "name": "Planned object", "events": []})
    report = evaluate(data)
    assert report["props"][-1]["id"] == "planned"
    assert report["props"][-1]["status"] == "not introduced"
    assert report["props"][-1]["events_in_scope"] == 0


def test_output_link_is_refused_before_opening(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(tracker()), encoding="utf-8")
    output = tmp_path / "report.md"
    real_is_symlink = type(output).is_symlink
    monkeypatch.setattr(
        type(output), "is_symlink", lambda path: path == output or real_is_symlink(path)
    )
    assert main([str(source), "--output", str(output)]) == 2
    assert not output.exists()
    assert "already exists" in capsys.readouterr().err
