from __future__ import annotations

import re
import sys
from contextlib import redirect_stdout
from collections.abc import Sequence

from .command import Command, CommandGroup, build_flag_maps
from .help_json import _get_choices
from .utils import CommandOption, _is_list_type

SHELLS = ("bash", "fish", "zsh")
COMPLETE_ENV = "_PIOU_COMPLETE"

_SCRIPTS = {
    "bash": """\
_{fn}() {{
    local line
    COMPREPLY=()
    while IFS= read -r line; do
        COMPREPLY+=("$line")
    done < <({env}=bash "${{COMP_WORDS[0]}}" "${{COMP_WORDS[@]:1:COMP_CWORD}}" 2>/dev/null)
}}
complete -o default -F _{fn} {prog}
""",
    "zsh": """\
#compdef {prog}
_{fn}() {{
    local -a candidates
    candidates=(${{(f)"$({env}=zsh "${{words[1]}}" "${{(@)words[2,CURRENT]}}" 2>/dev/null)"}})
    if (( ${{#candidates}} )); then
        _describe 'values' candidates
    else
        _files
    fi
}}
compdef _{fn} {prog}
""",
    "fish": """\
function __{fn}_complete
    set -l tokens (commandline -opc)
    set -l cur (commandline -ct)
    set -l prog $tokens[1]
    set -e tokens[1]
    {env}=fish $prog $tokens "$cur" 2>/dev/null
end
complete -c {prog} -f -a '(__{fn}_complete)'
""",
}


def completion_script(shell: str, prog: str) -> str:
    """Shell code that registers dynamic completion of `prog` for `shell`."""
    if shell not in SHELLS:
        raise ValueError(f"Unsupported shell {shell!r}, pick one of: {', '.join(SHELLS)}")
    if not re.fullmatch(r"[\w.-]+", prog):
        raise ValueError(f"Invalid program name {prog!r}")
    return _SCRIPTS[shell].format(prog=prog, fn=re.sub(r"\W", "_", prog), env=COMPLETE_ENV)


def get_candidates(group: CommandGroup, words: Sequence[str], resolve_choices: bool = False) -> list[tuple[str, str]]:
    """(value, help) candidates for the last of `words` (the word under the cursor, possibly empty).

    Callable `choices` are only called when `resolve_choices` is set.
    """
    *done, cur = words or [""]
    options: list[CommandOption] = list(group.options)
    command: Command | None = None
    pending: CommandOption | None = None
    pending_values = 0
    positionals = 0
    for word in done:
        if pending is not None and not _is_list_type(pending.data_type):
            pending = None
            continue
        if pending is not None:
            # list options take values until a flag or a subcommand
            if not word.startswith("-") and (command is not None or word not in group.commands):
                pending_values += 1
                continue
            pending = None
        active = command or group._commands.get("__main__")
        if word.startswith("-"):
            # global flags win over command flags, as in parse_input_args
            flag_map, bool_flags, _ = build_flag_maps([*(active.options if active else []), *options])
            if word in flag_map and word not in bool_flags:
                pending, pending_values = flag_map[word], 0
            continue
        if command is not None:
            positionals += 1
            continue
        sub = group.commands.get(word)
        if isinstance(sub, CommandGroup):
            group = sub
            options += sub.options
        elif sub is not None:
            command = sub
        elif active is None:
            return []
        else:
            command, positionals = active, 1

    if pending is not None and not pending_values:
        return _choice_candidates(pending, cur, resolve_choices)
    values = _choice_candidates(pending, cur, resolve_choices) if pending is not None else []
    active = command or group._commands.get("__main__")
    if cur.startswith("-"):
        return [
            (flag, opt.help or "")
            for opt in [*(active.options if active else []), *options]
            for flag in (*opt.keyword_args, *([opt.negative_flag] if opt.negative_flag else []))
            if flag.startswith(cur)
        ]
    if active is not None and positionals < len(active.positional_args):
        values += _choice_candidates(active.positional_args[positionals], cur, resolve_choices)
    if command is None:
        return values + [(name, sub.help or "") for name, sub in group.commands.items() if name.startswith(cur)]
    return values


def _choice_candidates(opt: CommandOption, cur: str, resolve: bool) -> list[tuple[str, str]]:
    if opt.hide_choices:
        return []
    try:
        # stdout is reserved for candidates
        with redirect_stdout(sys.stderr):
            choices = _get_choices(opt, resolve)
    except Exception:
        return []
    if not choices or isinstance(choices, str):
        return []
    match = (lambda s: s.startswith(cur)) if opt.case_sensitive else (lambda s: s.lower().startswith(cur.lower()))
    return [(str(c), "") for c in choices if not isinstance(c, re.Pattern) and match(str(c))]


def print_candidates(group: CommandGroup, shell: str, words: Sequence[str], resolve_choices: bool = False) -> None:
    """Print one candidate per line in the format `shell` expects."""
    if shell not in SHELLS:
        return
    for value, text in get_candidates(group, words, resolve_choices):
        # one line per candidate, tab separates fish descriptions: such values can't be represented
        if any(c in value for c in "\n\r\t"):
            continue
        text = text.splitlines()[0].replace("\t", " ") if text else ""
        if shell == "zsh":
            value = value.replace("\\", "\\\\").replace(":", r"\:")
            print(f"{value}:{text}" if text else value)
        elif shell == "fish":
            print(f"{value}\t{text}" if text else value)
        else:
            print(value)
