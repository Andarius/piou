window.BENCHMARK_DATA = {
  "lastUpdate": 1771875922875,
  "repoUrl": "https://github.com/Andarius/piou",
  "entries": {
    "Import Performance": [
      {
        "commit": {
          "author": {
            "email": "julien.brayere@obitrain.com",
            "name": "Julien Brayere",
            "username": "Andarius"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "1b7d96c5cd64fcd3367565cf3385c80d9cbfa0e0",
          "message": "fix: issue with set_options_processor (#42)\n\n* feat: extract options in `set_options_processor`, document async commands\n\n- Move `extract_function_info` from `@processor()` into `set_options_processor()` so both paths auto-register `Option()` definitions as group-level options\n- Add async commands section to README\n- Add processor example to `examples/simple.py`\n\n* fix: main-only CLI global options parsing, add regression tests\n\n- Fix `parse_input_args` early return bypassing global option separation for main-only CLIs\n- Parametrize `test_run_command` to cover both `set_options_processor` and `@processor()` paths\n- Add `test_main_only_with_global_options` for main-only CLI with global options\n\n* docs: document `set_options_processor()` in features",
          "timestamp": "2026-02-23T20:44:43+01:00",
          "tree_id": "ba970507b02962a1c26f9446a608a10c7071488c",
          "url": "https://github.com/Andarius/piou/commit/1b7d96c5cd64fcd3367565cf3385c80d9cbfa0e0"
        },
        "date": 1771875921705,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "piou (core)",
            "value": 80.23,
            "unit": "ms",
            "range": 1.51
          },
          {
            "name": "piou (rich)",
            "value": 153.49,
            "unit": "ms",
            "range": 10.53
          },
          {
            "name": "piou.tui",
            "value": 274.21,
            "unit": "ms",
            "range": 1.99
          }
        ]
      }
    ]
  }
}