import json

import pytest

from manuscript_prop_tracker.cli import main
from manuscript_prop_tracker.core import evaluate, load_tracker, render_markdown


def tracker():
    return {
        "version": 1,
        "manuscript": "The Glass Harbor",
        "milestones": ["Chapter 1", "Chapter 2", "Chapter 3"],
        "props": [
            {
                "id": "key",
                "name": "Brass key",
                "events": [
                    {
                        "milestone": "Chapter 1",
                        "action": "introduced",
                        "owner": "Mara",
                        "location": "Workshop",
                    },
                    {
                        "milestone": "Chapter 2",
                        "action": "transferred",
                        "from_owner": "Mara",
                        "owner": "Ilan",
                    },
                    {"milestone": "Chapter 3", "action": "resolved"},
                ],
            }
        ],
    }


def test_evaluate_state_and_boundary():
    report = evaluate(tracker(), "Chapter 2")
    assert report["issue_count"] == 0
    assert report["props"][0]["owner"] == "Ilan"
    assert report["props"][0]["status"] == "active"
    assert "Issues: none" in render_markdown(report)
    assert evaluate(tracker())["props"][0]["status"] == "resolved"


def test_continuity_issues():
    data = tracker()
    data["props"][0]["events"] = [
        {"milestone": "Chapter 1", "action": "moved", "location": "Dock"},
        {"milestone": "Chapter 2", "action": "introduced", "owner": "Mara"},
        {"milestone": "Chapter 2", "action": "introduced", "owner": "Mara"},
        {"milestone": "Chapter 2", "action": "destroyed"},
        {"milestone": "Chapter 3", "action": "transferred", "from_owner": "Noa", "owner": "Ilan"},
    ]
    report = evaluate(data)
    assert report["issue_count"] == 4
    assert "before introduction" in report["props"][0]["issues"][0]
    assert "after destroyed" in report["props"][0]["issues"][2]
    assert "current owner is Mara" in report["props"][0]["issues"][3]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data.update(version=2), "version 1"),
        (lambda data: data.update(manuscript=""), "manuscript name"),
        (lambda data: data.update(milestones=[]), "non-empty"),
        (lambda data: data["milestones"].append("Chapter 1"), "unique"),
        (lambda data: data["props"].append(data["props"][0].copy()), "duplicate prop"),
        (lambda data: data["props"][0].update(events="bad"), "events must"),
        (lambda data: data["props"][0]["events"][0].update(action="vanished"), "invalid event"),
        (
            lambda data: data["props"][0]["events"][0].update(milestone="Epilogue"),
            "unknown milestone",
        ),
        (lambda data: data["props"][0]["events"].reverse(), "out of milestone order"),
    ],
)
def test_validation(tmp_path, change, message):
    data = tracker()
    change(data)
    path = tmp_path / "props.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((TypeError, ValueError), match=message):
        load_tracker(path)


def test_transfer_requires_owner_and_unknown_boundary(tmp_path):
    data = tracker()
    data["props"][0]["events"][1].pop("owner")
    path = tmp_path / "props.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="requires an owner"):
        load_tracker(path)
    with pytest.raises(ValueError, match="unknown milestone"):
        evaluate(tracker(), "Epilogue")


def test_cli_json_and_safe_output(tmp_path, capsys):
    path = tmp_path / "props.json"
    path.write_text(json.dumps(tracker()), encoding="utf-8")
    assert main([str(path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["issue_count"] == 0
    output = tmp_path / "report.md"
    assert main([str(path), "--through", "Chapter 1", "--output", str(output)]) == 0
    assert "Through **Chapter 1**" in output.read_text(encoding="utf-8")
    assert main([str(path), "--output", str(output)]) == 2
