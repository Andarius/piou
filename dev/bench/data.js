window.BENCHMARK_DATA = {
  "lastUpdate": 1792482384161,
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
          "id": "d5ab1de86a6d915628fcf342eea5e118703c6f1b",
          "message": "ci: release through release/<version> PRs (#64)\n\n* ci: release through release/<version> PRs like padwan-llm\n\n* ci: padwan-style import benchmark, normalised to interpreter startup and gated by label on PRs\n\n* docs: wrap long AGENTS.md lines",
          "timestamp": "2026-10-20T09:45:35+02:00",
          "tree_id": "83a03ad8a23d49228f7ad14c29a71111ae21b876",
          "url": "https://github.com/Andarius/piou/commit/d5ab1de86a6d915628fcf342eea5e118703c6f1b"
        },
        "date": 1792482383701,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "3.13 · piou (core)",
            "value": 144.49,
            "unit": "ms",
            "range": 2.72
          },
          {
            "name": "3.13 · piou (rich)",
            "value": 192.89,
            "unit": "ms",
            "range": 3.43
          },
          {
            "name": "3.13 · piou.tui",
            "value": 453.66,
            "unit": "ms",
            "range": 5.08
          },
          {
            "name": "3.15 · piou (core)",
            "value": 144.26,
            "unit": "ms",
            "range": 3.64
          },
          {
            "name": "3.15 · piou (rich)",
            "value": 145.76,
            "unit": "ms",
            "range": 3.81
          },
          {
            "name": "3.15 · piou.tui",
            "value": 146.3,
            "unit": "ms",
            "range": 2.57
          }
        ]
      }
    ]
  }
}