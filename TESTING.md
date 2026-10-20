# Testing

Install `.[dev]`, then run `ruff format --check .`, `ruff check .`, `pytest`, and `python -m build`. Retain the existing coverage gate.

Compare explicit inclusive milestone states; preserve warnings and hide future-only props. Test transfers, moves, resolution, unchanged props, invalid boundaries and source immutability.

Install the built wheel into an isolated environment and exercise the documented CLI before release. Protected cross-platform CI and CodeQL remain required.

## 1.1.1 regression acceptance

Exercise malformed structured text, report-write errors, concurrent output creation and source immutability. Verify installed wheel and source-distribution imports, run the full suite with the unchanged 90% branch-coverage gate, and exercise the documented commands outside the source tree.
