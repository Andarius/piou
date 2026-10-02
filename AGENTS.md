# AGENTS.md

Piou: Python CLI toolkit with a FastAPI-like developer experience (typed options, nested command groups, derived
options, async commands, Rich help, optional Textual TUI, shell completion).

Setup, workflow, PR and release conventions: see `CONTRIBUTING.md`.

## Layout

- `piou/cli.py`: `Cli`, the entry point. `run()` reads `sys.argv`, routes to the TUI or shell completion, then
  `run_with_args()` turns piou exceptions into formatted errors and exit codes.
- `piou/command.py`: `Command` and `CommandGroup` (nested groups, `__main__` default command, processors).
  Parsing flow: `CommandGroup.run_with_args()` → `parse_input_args()` (command name, global options, command
  options) → `convert_args_to_dict()` → processors → command function.
- `piou/utils.py`: `Option`, `Derived`, `CommandOption`, `validate_value()` (str, int, float, Path, date, datetime,
  UUID, dict, list, Literal, Enum, secrets).
- `piou/help_json.py`: `--help-json` schema of groups/commands/options/choices.
- `piou/completion.py`: dynamic shell completion (`_PIOU_COMPLETE=<shell>`, `--completions <shell>`).
- `piou/formatter/`: pluggable help/error output, `RichFormatter` by default.
- `piou/tui/`: Textual TUI (`Cli(tui=True)` or `PIOU_TUI=1`), needs the `tui` extra.

## Stack

- Python >=3.10 (CI: 3.10 to 3.15), uv, ruff, pyright (includes `tests/` and `examples/`), pytest, commitizen.
- Runtime dependency: `rich` only; `textual` (and `watchfiles`) are optional extras. Never add a runtime dependency.
- Import time is benchmarked in CI (`./bin/bench-imports.sh`); keep `rich`/`textual` imports lazy and keep the
  `__lazy_modules__` declarations (effective on 3.15+).

## Verify

```bash
uv sync --all-extras --all-groups
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest                    # TUI snapshots: add --snapshot-update only for intended UI changes
./bin/run-examples.sh
```

## Rules linters don't catch

- Supported floor is 3.10: no `type` statements, PEP 695 generics or 3.11+ stdlib APIs without a fallback.
- Prose docstrings without `Args:`/`Returns:` sections.
- Tests: `pytest.param(..., id="...")` for every parametrized case; combine `nullcontext` and `pytest.raises` in the
  same test when covering success and failure. `sys_exit_counter` (`tests/conftest.py`) mocks `sys.exit`.
- Code paths for `--help-json` and shell completion must not run command bodies, processors or callable `choices`,
  and completion must print nothing on stdout but candidates.
- `Cli.add_sub_parser()` / `CommandGroup.add_sub_parser()` are deprecated; use `add_command_group()`.
- User-facing changes update `docs/` and `README.md`. Don't bump the version: releases are automatic from `master`.
