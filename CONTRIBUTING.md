# Contributing

## Issues

Include the `piou` version, Python version, a minimal CLI that reproduces the problem and the exact command line.

Open an issue to discuss before starting a new feature or a public API change; PRs for those without prior
discussion may be closed.

## Setup

Fork the repo, clone your fork and create a branch. Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --all-groups
uv run prek install --hook-type pre-commit --hook-type commit-msg   # ruff, uv lock, conventional commit messages
```

## Checks

CI runs these on Python 3.10 to 3.15; run them before opening a PR:

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
./bin/run-examples.sh
```

TUI tests use [pytest-textual-snapshot](https://github.com/Textualize/pytest-textual-snapshot): after an intended UI
change, update the snapshots with `uv run pytest tests/tui --snapshot-update` and review the SVG diffs.

## Guidelines

- Keep the core light: `rich` is the only required runtime dependency, `textual` stays behind the `tui` extra. Import
  time is benchmarked in CI (`./bin/bench-imports.sh`), so keep optional imports lazy.
- New behavior comes with tests; parametrize them with `pytest.param(..., id="...")`.
- Update `docs/` and `README.md` for user-facing changes. Preview docs with `uv run --group docs mkdocs serve`.

## Pull requests

- Title in [Conventional Commits](https://www.conventionalcommits.org/) form (`feat:`, `fix:`, `docs:`, ...); PRs
  are squash-merged and the title decides the next version bump and changelog entry.
- Keep the description short: what changed and why.

## Use of AI

AI tools are welcome; `AGENTS.md` gives them the repo's commands and rules. You remain responsible for your change:
you must understand it and explain it in your own words, in the PR body and in review replies. PRs opened
autonomously by an agent will be closed.

## Releases

Releases are automatic: every green CI run on `master` runs `cz bump` (version and `CHANGELOG.md` from the commit
messages), tags, creates the GitHub release and publishes to PyPI. Don't bump the version by hand.
