window.BENCHMARK_DATA = {
  "lastUpdate": 1784269157540,
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
          "id": "3e3a3779783968063817aae4e0d65349e3c69814",
          "message": "fix: don't consume the next arg as value for boolean global options placed after the command (#52)\n\n'cmd --verbose positional' ate the positional as the flag's value,\nfailing with PosParamsCountError. Reuse global_bool_option_names in the\nafter-command loop like the __main__ branch already does.",
          "timestamp": "2026-07-17T08:18:45+02:00",
          "tree_id": "5f3e4b1289b6d01757ce8b618351ca6270cd6788",
          "url": "https://github.com/Andarius/piou/commit/3e3a3779783968063817aae4e0d65349e3c69814"
        },
        "date": 1784269157168,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "piou (core)",
            "value": 93.14,
            "unit": "ms",
            "range": 2.58
          },
          {
            "name": "piou (rich)",
            "value": 151.48,
            "unit": "ms",
            "range": 3.64
          },
          {
            "name": "piou.tui",
            "value": 303.13,
            "unit": "ms",
            "range": 6.68
          }
        ]
      }
    ]
  }
}