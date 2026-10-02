window.BENCHMARK_DATA = {
  "lastUpdate": 1790975214410,
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
          "id": "70b74ef39d569dda27220155ae4445dbd94d5f44",
          "message": "feat: dynamic shell completion for bash, zsh and fish (#55)\n\n* feat: dynamic shell completion for bash, zsh and fish\n\n`prog --completions <shell>` prints a script that calls back into the CLI with _PIOU_COMPLETE=<shell> to list commands, options and choices. Callable choices are resolved only with Cli(complete_dynamic_choices=True) or PIOU_COMPLETE_DYNAMIC=1.\n\n* docs: add CONTRIBUTING.md and track AGENTS.md\n\n* fix(completion): accept a program name and skip unrepresentable candidates\n\n`--completions <shell> [prog]` registers the script for wrappers, aliases and `python -m`, where argv[0] is not the command name. Values containing newlines or tabs are skipped and tabs in descriptions flattened, since they break the one-candidate-per-line format.",
          "timestamp": "2026-10-02T23:06:23+02:00",
          "tree_id": "c6746882e7d1ceb8bd37e5baa1c7ab0270da0171",
          "url": "https://github.com/Andarius/piou/commit/70b74ef39d569dda27220155ae4445dbd94d5f44"
        },
        "date": 1790975213637,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "piou (core)",
            "value": 81.71,
            "unit": "ms",
            "range": 2.48
          },
          {
            "name": "piou (rich)",
            "value": 128.08,
            "unit": "ms",
            "range": 1.49
          },
          {
            "name": "piou.tui",
            "value": 270.03,
            "unit": "ms",
            "range": 2.72
          }
        ]
      }
    ]
  }
}