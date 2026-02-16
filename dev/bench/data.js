window.BENCHMARK_DATA = {
  "lastUpdate": 1771274878639,
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
          "id": "c0789830dfd761ab050066cf12bb52f0970cd5e5",
          "message": "feat: tui autoscroll (#41)\n\n* feat: add StreamingMessage widget and TUI autoscroll\n\n- Add `StreamingMessage(Static)` widget in `piou/tui/widgets.py` that\n  accumulates text via `append()` and respects `_auto_scroll`\n- Replace `Vertical` with `_MessageScroll(VerticalScroll)` subclass that\n  syncs `_auto_scroll` on any scroll change (mouse wheel, keyboard,\n  programmatic) via `watch_scroll_y`\n- Add `Shift+Up/Down` bindings for manual message scrolling\n- Update `/generate` example to use `StreamingMessage` with async streaming\n- Export `StreamingMessage` from `piou.tui`\n\n* feat: add StreamingMessage widget module\n\n* fix: autoscroll race condition and cleanup\n\n- Re-check `_auto_scroll` at execution time in `_scroll_to_bottom()`\n  so deferred callbacks respect scroll changes between queue and run\n- Remove redundant `was_at_bottom` check in `_add_message()`, already\n  handled by `_MessageScroll.watch_scroll_y`\n- Replace `type: ignore` with `isinstance` check in\n  `StreamingMessage.append()`",
          "timestamp": "2026-02-16T21:47:28+01:00",
          "tree_id": "7a5c49d9386a7213ddb22c059185ca1aec1eff14",
          "url": "https://github.com/Andarius/piou/commit/c0789830dfd761ab050066cf12bb52f0970cd5e5"
        },
        "date": 1771274878230,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "piou (core)",
            "value": 88.92,
            "unit": "ms",
            "range": 1.27
          },
          {
            "name": "piou (rich)",
            "value": 166.33,
            "unit": "ms",
            "range": 4.34
          },
          {
            "name": "piou.tui",
            "value": 303.13,
            "unit": "ms",
            "range": 4.61
          }
        ]
      }
    ]
  }
}