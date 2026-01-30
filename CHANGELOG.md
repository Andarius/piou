# Changelog

 ## 0.28.0 (2026-01-30)

### Features & Improvements

  - add interactive TUI mode powered by [Textual](https://textual.textualize.io/) (#31)
    - enable via `Cli(tui=True)`, `PIOU_TUI=1` environment variable or `--tui`
    - command suggestions with inline completion
    - persistent command history
    - `TuiContext` for commands to interact with the TUI (notifications, widgets)
    - customizable styling via CSS
    - requires `piou[tui]` extra

> [!WARNING]
> The TUI module is in **beta**. APIs may change in future releases.

## 0.27.0 (2026-01-22)

### Features & Improvements

  - add `Secret` and `Password` types for masking sensitive values in help output (#30)
  - add `MaybePath` type that skips file existence checking (#30)

## 0.26.0 (2026-01-22)

### Features & Improvements

  - add async choices support for dynamic option values (#29)

## 0.25.2 (2026-01-21)

### Fix

  - fix rich formatter nested command groups display (#28)

## 0.25.1 (2026-01-20)

### Fix

  - fix regex pattern display in help output

## 0.25.0 (2026-01-19)

### Features & Improvements

  - add regex pattern support in choices via `Regex()` helper (#27)

## 0.24.0 (2026-01-03)

### Features & Improvements

  - add base `Formatter` class for plain text output without Rich styling (#26)
  - add `PIOU_FORMATTER` environment variable to switch between raw and rich formatters

## 0.23.0 (2025-12-28)

### Features & Improvements

  - add "Did you mean?" suggestions when a command is mistyped (#24)
