window.BENCHMARK_DATA = {
  "lastUpdate": 1770371609336,
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
          "id": "2c810139e4d63c62bfabf4043b4cfda43b36ec0f",
          "message": "feat: tui queue management, main+commands coexistence, fix split_cmd for single value flags (#38)",
          "timestamp": "2026-02-06T10:52:59+01:00",
          "tree_id": "1fa581f651365b475fdf711aa7aab13886c4f633",
          "url": "https://github.com/Andarius/piou/commit/2c810139e4d63c62bfabf4043b4cfda43b36ec0f"
        },
        "date": 1770371608934,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "piou (core)",
            "value": 90.18,
            "unit": "ms",
            "range": 3.29
          },
          {
            "name": "piou (rich)",
            "value": 163.29,
            "unit": "ms",
            "range": 2.63
          },
          {
            "name": "piou.tui",
            "value": 303.47,
            "unit": "ms",
            "range": 11.84
          }
        ]
      }
    ]
  }
}