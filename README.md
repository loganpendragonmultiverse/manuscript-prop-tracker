# Manuscript Prop Tracker

[![CI](https://github.com/loganpendragonmultiverse/manuscript-prop-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/manuscript-prop-tracker/actions/workflows/ci.yml)

Manuscript Prop Tracker follows important objects through ordered story milestones. It reports each prop's latest owner, location, and status while flagging transfers from the wrong owner, appearances before introduction, and events after an object leaves the story.

## Three-minute start

```bash
python -m pip install .
prop-track examples/props.json
prop-track examples/props.json --through "Chapter 2" --format json
```

The input is structured JSON: milestones define story order, and every prop contains an explicit event history. Reports can stop at a milestone so an author can inspect continuity at a particular point in the draft.

The tool does not parse prose or decide which objects matter. It records only the facts supplied by the writer, and a clean report means those facts are internally consistent—not that the manuscript itself is error-free. Requires Python 3.10 or newer.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).

## Compare two milestones (1.1)

`prop-track examples/props.json --compare-from "Chapter 1" --through "Chapter 2"`
adds before/after owner, location and status plus `changed_fields` for every prop
with an event at or before the end boundary. Unchanged props remain visible. Both
boundaries are inclusive; equal boundaries are allowed and reversed or unknown
boundaries reject. `--through` is required with `--compare-from`.

The normal end-boundary report and its continuity warnings remain available alongside
the comparison. No event notes or future-only prop identities appear in comparisons.
All events at a milestone apply in supplied order; this is a comparison of recorded
states, not inferred transfers or a chronological explanation. Source files stay unchanged.
