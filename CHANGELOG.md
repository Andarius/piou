# Changelog

## 0.28.4 (2026-01-30)

### Fix

- clean deps (#34)

## 0.28.3 (2026-01-30)

### Fix

- adding support for a cstum 'status-above' content (#33)

## 0.28.2 (2026-01-30)

### Fix

- adding kwargs to run for tui params (#32)

## 0.28.1 (2026-01-30)

### Fix

- passing css to tui run (#31)

## 0.28.0 (2026-01-30)

### Feat

- tui support (#25)

## 0.27.0 (2026-01-22)

### Feat

- secrets (#30)

## 0.26.0 (2026-01-22)

### Feat

- adding async choices support (#29)

## 0.25.2 (2026-01-14)

### Fix

- rich formatter nested (#28)

## 0.25.1 (2026-01-06)

### Fix

- regex display in help

## 0.25.0 (2026-01-06)

### Feat

- add regex choices support (#27)

## 0.24.0 (2026-01-03)

### Feat

- add raw formatter (#26)

## 0.23.0 (2025-12-28)

### Feat

- add closest match (#24)

## 0.22.1 (2025-12-19)

### Fix

- remove legacy scripts config

## 0.22.0 (2025-12-19)

### Feat

- improvements (#21)

## 0.21.0 (2025-11-09)

### Feat

- bumping min version (#20)

## 0.20.1 (2025-11-09)

### Fix

- properly cancel async tasks + adding support for python 3.14 (#19)

## 0.20.0 (2025-07-13)

### Fix

- program_name base path and supported python versions

## 0.19.0 (2025-07-13)

### Feat

- show module name instead of main (#18)
- show library name instead of __main__.py during module execution
- show library name instead of __main__.py during module execution

### Fix

- program_name base path and supported python versions

## 0.18.0 (2025-07-12)

### Feat

- global args improvement and documentation (#17)

## 0.17.0 (2025-07-11)

### Feat

- migrate to uv (#16)

## 0.16.2 (2025-04-17)

### Fix

- lock / ci (#15)
- bump rich

## 0.16.1 (2025-04-16)

### Fix

- conflicts on param names for multiple derive (#14)
- typing example
- typing example

## 0.16.0 (2025-03-26)

### Feat

- adding main command support (#13)

## 0.15.0 (2025-03-11)

### Feat

- adding support for callable choices (#10)

## 0.14.2 (2023-12-15)

## 0.14.1 (2023-12-15)

### Fix

- updating classifiers
- bump version

## 0.14.0 (2023-10-18)

### Feat

- adding CommandError to display a message in case of an exception

## 0.13.4 (2023-07-09)

## 0.13.3 (2023-07-09)

### Fix

- failed to pass json as string
- rich version

## 0.13.2 (2023-07-09)

### Fix

- test

## 0.13.1 (2022-12-21)

## 0.13.0 (2022-12-14)

### Fix

- missing typing-extensions library
- fix poetry lock

## 0.12.16 (2022-11-27)

### Feat

- adding support for LiteralString
- adding support for LiteralString

## 0.12.15 (2022-11-23)

### Fix

- fix deprecation warning no current event loop

## 0.12.14 (2022-10-19)

### Feat

- better exit code

### Fix

- command is now running on same loop as async derived arguments
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- fix ci deployment
- bump version
- bump version
- bump version
- bump version
- bump version
- bump version
- removing loop

## 0.12.1 (2022-10-08)

### Feat

- adding 'choices' option

## 0.12.0 (2022-10-08)

## 0.11.1 (2022-09-27)

### Fix

- fix return type of Derived option

## 0.11.0 (2022-09-02)

### Feat

- adding support for dynamic derived functions

## 0.10.5 (2022-08-03)

## 0.10.4 (2022-08-02)

## 0.10.3 (2022-07-29)

## 0.10.2 (2022-07-27)

## 0.10.1 (2022-07-25)

### Fix

- issue when parsing optional field

## 0.10.0 (2022-06-06)

### Feat

- adding Password type

## 0.9.8 (2022-05-17)

### Fix

- fix positional argument with quotation mark

## 0.9.7 (2022-04-23)

### Fix

- fix event loop

## 0.9.6 (2022-04-23)

### Feat

- adding support for chained derived
- adding support for chained derived

## 0.9.5 (2022-04-19)

### Fix

- fixing typing issues with pyright

## 0.9.4 (2022-01-24)

### Fix

- derived option processor name

## 0.9.3 (2022-01-23)

## 0.9.2 (2022-01-20)

## 0.9.1 (2022-01-20)

## 0.9.0 (2022-01-19)

### Feat

- adding case sensitivity for Literal

## 0.8.2 (2022-01-19)

### Fix

- sub_cmd_run now called correcly

## 0.8.1 (2022-01-15)

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

  - add `Formatter` base class for plain text output (#26)
  - add `PIOU_FORMATTER` environment variable to switch formatters

## 0.23.0 (2025-12-28)

### Features & Improvements

  - add "Did you mean?" suggestions when a command is mistyped (#24)
