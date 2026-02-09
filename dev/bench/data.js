window.BENCHMARK_DATA = {
  "lastUpdate": 1770637969605,
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
          "id": "cbb6a8e60f28b4cdad22657398d1ffc869fdbcd0",
          "message": "feat: overload add_command_group, deprecate add_sub_parser (#40)\n\n* feat: overload add_command_group to accept str or CommandGroup, deprecate add_sub_parser\n\nUnifies group creation into add_command_group (now returns the group),\nadds CommandGroup.main() shortcut, and deprecates both Cli.add_sub_parser\nand CommandGroup.add_sub_parser with DeprecationWarning.\n\n* feat: overload add_command_group, deprecate add_sub_parser\n\n- Unify group creation into `add_command_group` (now accepts `str` or `CommandGroup`, always returns the group)\n- Add `CommandGroup.main()` shortcut decorator\n- Deprecate `Cli.add_sub_parser` and `CommandGroup.add_sub_parser` with `DeprecationWarning`\n- Migrate all existing usages from `add_sub_parser` to `add_command_group`\n\n* fix: review fixes for add_command_group and boolean flag parsing\n\n- Raise `TypeError` when kwargs are passed with a `CommandGroup` object in `Cli.add_command_group()`\n- Update docs to use `add_command_group()` instead of deprecated `add_sub_parser()`\n- Improve `CommandGroup.add_sub_parser()` deprecation message to mention `Cli.add_command_group()`\n- Add `is_main`+`cmd` validation guard in `CommandGroup.command()`\n- Support arbitrary `--flag/--other-flag` syntax, not just `--flag/--no-flag`",
          "timestamp": "2026-02-09T12:52:15+01:00",
          "tree_id": "b1aea3619f4469b914591035834f0e1f6d169cc1",
          "url": "https://github.com/Andarius/piou/commit/cbb6a8e60f28b4cdad22657398d1ffc869fdbcd0"
        },
        "date": 1770637969191,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "piou (core)",
            "value": 95.24,
            "unit": "ms",
            "range": 1.94
          },
          {
            "name": "piou (rich)",
            "value": 171.42,
            "unit": "ms",
            "range": 1.73
          },
          {
            "name": "piou.tui",
            "value": 319.69,
            "unit": "ms",
            "range": 5.93
          }
        ]
      }
    ]
  }
}