window.BENCHMARK_DATA = {
  "lastUpdate": 1787062089165,
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
          "id": "9114452b6463e3c7acf20bd84cc1e37c127deb95",
          "message": "feat: Python 3.15 support with lazy rich imports (#54)\n\n* feat: Python 3.15 support with lazy rich imports\n\n- add 3.15 to the CI matrix (allow-prereleases until final) and trove classifiers\n- bump watchfiles to 1.2.0 for cp315 wheels\n- lazy rich imports via PEP 810 __lazy_modules__ (no-op on <3.15) and defer\n  Console creation with cached_property so rich only loads on help/error output\n\n* ci: benchmark import time on 3.15 as a separate series\n\n* feat: lazy textual imports in piou.tui on 3.15+\n\nImporting TuiContext (e.g. for typing commands) no longer loads textual\nuntil a TUI class is actually accessed.",
          "timestamp": "2026-08-18T16:07:29+02:00",
          "tree_id": "e3e90f33d9f7e71d1f8053cb6b82f868549ebd69",
          "url": "https://github.com/Andarius/piou/commit/9114452b6463e3c7acf20bd84cc1e37c127deb95"
        },
        "date": 1787062087998,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "piou (core)",
            "value": 87.82,
            "unit": "ms",
            "range": 1.02
          },
          {
            "name": "piou (rich)",
            "value": 133.95,
            "unit": "ms",
            "range": 2.24
          },
          {
            "name": "piou.tui",
            "value": 285.71,
            "unit": "ms",
            "range": 11.16
          }
        ]
      }
    ]
  }
}