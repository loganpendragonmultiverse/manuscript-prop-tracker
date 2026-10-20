from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ACTIONS = {"introduced", "moved", "transferred", "lost", "destroyed", "resolved"}
TERMINAL_ACTIONS = {"destroyed", "resolved"}


def load_tracker(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("tracker must be a version 1 object")
    if not isinstance(data.get("manuscript"), str) or not data["manuscript"].strip():
        raise ValueError("tracker requires a manuscript name")
    milestones = data.get("milestones")
    if (
        not isinstance(milestones, list)
        or not milestones
        or any(not isinstance(item, str) or not item.strip() for item in milestones)
    ):
        raise TypeError("milestones must be a non-empty list of names")
    if len(milestones) != len(set(milestones)):
        raise ValueError("milestone names must be unique")
    props = data.get("props")
    if not isinstance(props, list):
        raise TypeError("props must be a list")
    prop_ids: set[str] = set()
    positions = {milestone: index for index, milestone in enumerate(milestones)}
    for prop in props:
        if (
            not isinstance(prop, dict)
            or not isinstance(prop.get("id"), str)
            or not isinstance(prop.get("name"), str)
            or not prop["id"].strip()
            or not prop["name"].strip()
        ):
            raise TypeError("each prop requires non-empty string id and name")
        if prop["id"] in prop_ids:
            raise ValueError(f"duplicate prop id: {prop['id']}")
        prop_ids.add(prop["id"])
        events = prop.get("events")
        if not isinstance(events, list):
            raise TypeError(f"prop {prop['id']} events must be a list")
        previous = -1
        for event in events:
            if (
                not isinstance(event, dict)
                or not isinstance(event.get("action"), str)
                or event["action"] not in ACTIONS
            ):
                raise ValueError(f"prop {prop['id']} has an invalid event")
            milestone = event.get("milestone")
            if not isinstance(milestone, str) or milestone not in positions:
                raise ValueError(f"prop {prop['id']} references an unknown milestone")
            position = positions[milestone]
            if position < previous:
                raise ValueError(f"prop {prop['id']} events are out of milestone order")
            previous = position
            for field in ("owner", "from_owner", "location", "note"):
                if field in event and not isinstance(event[field], str):
                    raise TypeError(f"prop {prop['id']} event field {field} must be text")
            if event["action"] == "transferred" and not event.get("owner", "").strip():
                raise ValueError(f"prop {prop['id']} transfer requires an owner")
    return data


def evaluate(
    data: dict[str, Any], through: str | None = None, *, compare_from: str | None = None
) -> dict[str, Any]:
    milestones = data["milestones"]
    if through is not None and through not in milestones:
        raise ValueError(f"unknown milestone: {through}")
    limit = milestones.index(through) if through is not None else len(milestones) - 1
    if compare_from is not None:
        if through is None:
            raise ValueError("comparison requires an explicit through milestone")
        if compare_from not in milestones:
            raise ValueError(f"unknown comparison milestone: {compare_from}")
        if milestones.index(compare_from) > limit:
            raise ValueError("comparison start must not follow through milestone")
    results = []
    total_issues = 0
    for prop in data["props"]:
        owner: str | None = None
        location: str | None = None
        status = "not introduced"
        introduced = False
        terminal = False
        issues = []
        included = 0
        for event in prop["events"]:
            if milestones.index(event["milestone"]) > limit:
                continue
            included += 1
            action = event["action"]
            if terminal:
                issues.append(f"{event['milestone']}: {action} occurs after {status}")
            if not introduced and action != "introduced":
                issues.append(f"{event['milestone']}: {action} occurs before introduction")
            if action == "introduced":
                if introduced:
                    issues.append(f"{event['milestone']}: introduced more than once")
                introduced = True
                status = "active"
            elif action == "transferred":
                expected = event.get("from_owner")
                if expected and expected != owner:
                    issues.append(
                        f"{event['milestone']}: transfer expects {expected}, current owner is "
                        f"{owner or 'unassigned'}"
                    )
                owner = event["owner"]
                status = "active"
            elif action == "moved":
                status = "active"
            elif action == "lost":
                status = "lost"
                owner = None
            elif action in TERMINAL_ACTIONS:
                status = action
                terminal = True
            if "owner" in event and action != "lost":
                owner = event["owner"]
            if "location" in event:
                location = event["location"]
        if not included:
            continue
        total_issues += len(issues)
        results.append(
            {
                "id": prop["id"],
                "name": prop["name"],
                "events_in_scope": included,
                "status": status,
                "owner": owner,
                "location": location,
                "issues": issues,
            }
        )
    report = {
        "version": 1,
        "manuscript": data["manuscript"],
        "through": milestones[limit],
        "issue_count": total_issues,
        "props": results,
    }
    if compare_from is not None:
        before = evaluate(data, compare_from)
        prior = {prop["id"]: prop for prop in before["props"]}
        # Do not identify props whose entire history lies beyond the end boundary.
        visible = [prop for prop in results if prop["events_in_scope"]]
        report["props"] = visible
        changes = []
        for prop in visible:
            initial = prior.get(
                prop["id"], {"owner": None, "location": None, "status": "not introduced"}
            )
            fields = ("owner", "location", "status")
            changes.append(
                {
                    "id": prop["id"],
                    "name": prop["name"],
                    "before": {key: initial[key] for key in fields},
                    "after": {key: prop[key] for key in fields},
                    "changed_fields": [key for key in fields if initial[key] != prop[key]],
                    "issues": prop["issues"],
                }
            )
        report["comparison"] = {"from": compare_from, "through": through, "props": changes}
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['manuscript']} Prop Continuity",
        "",
        f"Through **{report['through']}** · Continuity issues: **{report['issue_count']}**",
        "",
    ]
    for prop in report["props"]:
        lines.extend(
            [
                f"## {prop['name']}",
                "",
                f"- Status: {prop['status']}",
                f"- Owner: {prop['owner'] or 'Unassigned'}",
                f"- Location: {prop['location'] or 'Unspecified'}",
                f"- Events in scope: {prop['events_in_scope']}",
            ]
        )
        if prop["issues"]:
            lines.extend(["- Issues:", *[f"  - {issue}" for issue in prop["issues"]]])
        else:
            lines.append("- Issues: none")
        lines.append("")
    if "comparison" in report:
        payload = json.dumps(report["comparison"], indent=2, ensure_ascii=False)
        fence = "~" * (
            max((len(run) for run in __import__("re").findall(r"~+", payload)), default=2) + 1
        )
        lines.extend(["## Milestone comparison", "", f"{fence}json", payload, fence])
    return "\n".join(lines).rstrip() + "\n"
