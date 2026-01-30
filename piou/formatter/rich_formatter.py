from dataclasses import dataclass, field
from difflib import get_close_matches

from rich.console import Console, RenderableType
from rich.padding import Padding
from rich.table import Table

from .base import Formatter, Titles
from .utils import get_program_name, fmt_help as _fmt_help_base
from ..command import Command, CommandOption, ParentArgs, CommandGroup


def pad(s: RenderableType, padding_left: int = 1):
    """Pad the given renderable with a specified left padding."""
    return Padding(s, (0, padding_left))


def fmt_option(option: CommandOption, show_full: bool = False, color: str = "white") -> str:
    """Format a command option for display with Rich markup."""
    if option.is_positional_arg:
        return f"[{color}]<{option.name}>[/{color}]"
    elif show_full:
        first_arg, *other_args = option.keyword_args
        required = f"[{color}]*[/{color}]" if option.is_required else ""
        if other_args:
            other_args = ", ".join(other_args)
            return f"[{color}]{first_arg}[/{color}] ({other_args}){required}"
        else:
            return f"[{color}]{first_arg}[/{color}]{required}"
    else:
        return "[" + sorted(option.keyword_args)[-1] + "]"


def fmt_cmd_options(options: list[CommandOption]) -> str:
    """Format command options for display in the usage section."""
    return (
        " ".join([fmt_option(x) for x in options]) if options else ""  # '[<arg1>] ... [<argN>]'
    )


def fmt_help(
    option: CommandOption,
    show_default: bool,
    *,
    markdown_open: str | None = "[bold]",
    markdown_close: str | None = "[/bold]",
):
    """Format the help text for a command option with Rich markup."""
    return _fmt_help_base(option, show_default, markdown_open=markdown_open, markdown_close=markdown_close)


def get_usage(
    global_options: list[CommandOption],
    command: str | None = None,
    command_options: list[CommandOption] | None = None,
    parent_args: ParentArgs | None = None,
):
    """Generate the usage string for a command or command group."""
    parent_args = parent_args or []
    _global_options = " ".join(["[" + sorted(x.keyword_args)[-1] + "]" for x in global_options])
    _command = None
    if command != "__main__":
        _command = f"[underline]{command}[/underline]" if command else "<command>"

    cmds = [get_program_name()] + [x.cmd for x in parent_args]
    cmds = " ".join(f"[underline]{x}[/underline]" for x in cmds)

    usage = cmds

    if _global_options:
        usage = f"{usage} {_global_options}"
    usage = f"{usage} {_command}" if _command is not None else usage
    if command_options:
        usage = f"{usage} {fmt_cmd_options(command_options)}"

    return usage


@dataclass(frozen=True)
class RichTitles(Titles):
    """Titles for the rich formatter."""

    GLOBAL_OPTIONS = f"[bold]{Titles.GLOBAL_OPTIONS}[/bold]"
    AVAILABLE_CMDS = f"[bold]{Titles.AVAILABLE_CMDS}[/bold]"
    COMMANDS = f"[bold]{Titles.COMMANDS}[/bold]"
    USAGE = f"[bold]{Titles.USAGE}[/bold]"
    DESCRIPTION = f"[bold]{Titles.DESCRIPTION}[/bold]"
    ARGUMENTS = f"[bold]{Titles.ARGUMENTS}[/bold]"
    OPTIONS = f"[bold]{Titles.OPTIONS}[/bold]"


MIN_MARKDOWN_SIZE: int = 75


@dataclass
class RichFormatter(Formatter):
    _console: Console = field(init=False, repr=False, default_factory=lambda: Console(markup=True, highlight=False))
    cmd_color: str = "cyan"
    option_color: str = "cyan"
    default_color: str = "white"
    show_default: bool = True
    """Use Markdown object for the description, otherwise use
    default str
    """
    use_markdown: bool = True
    """See https://pygments.org/styles/ for a list of styles """
    # Only usable if use_markdown is True
    code_theme: str = "solarized-dark"

    def _color_cmd(self, cmd: str):
        return f"[{self.cmd_color}]{cmd}[/{self.cmd_color}]"

    def _print_description(self, item: CommandGroup | Command):
        description = item.description or item.help
        if description:
            self._console.print()
            self._console.print(RichTitles.DESCRIPTION)
            if self.use_markdown:
                # Lazy import: rich.markdown pulls in pygments (~23ms startup cost)
                from rich.markdown import Markdown

                _max_width = max(len(x) for x in description.split("\n"))
                self._console.print(
                    pad(
                        Markdown(
                            "  \n".join(description.split("\n")),
                            code_theme=self.code_theme,
                        )
                    ),
                    width=max(_max_width, MIN_MARKDOWN_SIZE),
                )
            else:
                self._console.print(pad(description))

    def _fmt_help(self, option: CommandOption):
        return fmt_help(
            option,
            self.show_default,
            markdown_open=f"[{self.default_color}][bold]",
            markdown_close=f"[/{self.default_color}][/bold]",
        )

    def _print_options(self, options: list[CommandOption]):
        self.print_rows(
            [
                (
                    fmt_option(opt, show_full=True, color=self.option_color),
                    self._fmt_help(opt),
                )
                for opt in options
            ]
        )

    def print_rows(self, rows: list[tuple[str, str | None]]):  # pyright: ignore[reportIncompatibleMethodOverride]
        table = Table(show_header=False, box=None, padding=(0, self.col_space))
        table.add_column(width=self.col_size)
        table.add_column()
        for row in rows:
            table.add_row(*row)
        self._console.print(table)

    def print_cli_help(self, group: CommandGroup):
        self._console.print(RichTitles.USAGE)
        self._console.print(pad(get_usage(group.options)))
        self._console.print()

        if group.options:
            self._console.print(RichTitles.GLOBAL_OPTIONS)
            self._print_options(group.options)
            self._console.print()

        self._console.print(RichTitles.AVAILABLE_CMDS)
        self.print_rows(
            [(f" {self._color_cmd(_command.name or '')}", _command.help) for _command in group.commands.values()]
        )
        self._print_description(group)

    def print_cmd_help(
        self,
        command: Command,
        options: list[CommandOption],
        parent_args: ParentArgs | None = None,
    ):
        usage = get_usage(
            global_options=options,
            command=command.name,
            command_options=command.options_sorted,
            parent_args=parent_args,
        )
        self._console.print(RichTitles.USAGE)
        self._console.print(pad(usage))
        self._console.print()

        if command.positional_args:
            self._console.print(RichTitles.ARGUMENTS)
            self.print_rows(
                [
                    (
                        fmt_option(option, color=self.option_color),
                        self._fmt_help(option),
                    )
                    for option in command.positional_args
                ]
            )
        if command.keyword_args:
            self._console.print("\n" + RichTitles.OPTIONS)
            self._print_options(command.keyword_args)

        global_options = options + [
            parent_option for parent_arg in (parent_args or []) for parent_option in parent_arg.options
        ]
        if global_options:
            self._console.print("\n" + RichTitles.GLOBAL_OPTIONS)
            self._print_options(global_options)

        self._print_description(command)

    def print_cmd_group_help(self, group: CommandGroup, parent_args: ParentArgs):
        parent_commands = [get_program_name()] + [x.cmd for x in parent_args]
        commands_str = []
        for i, (cmd_name, cmd) in enumerate(group.commands.items()):
            _cmds = []
            for cmd_lvl, x in enumerate(parent_commands + [cmd_name]):
                _cmds.append(f"[underline]{x}[/underline]")
                if group.options and cmd_lvl == len(parent_commands) - 1:
                    _cmds.append(fmt_cmd_options(group.options))
            _cmds_str = " ".join(_cmds)
            _line = f"{'' if i == 0 else 'or: ':>5}{_cmds_str} {fmt_cmd_options(cmd.options_sorted)}".rstrip()
            commands_str.append(_line)
        commands_str = "\n".join(commands_str)

        self._console.print(RichTitles.USAGE)
        self._console.print(commands_str)

        self._console.print()

        self._console.print(RichTitles.COMMANDS)
        for cmd_name, cmd in group.commands.items():
            self._console.print(pad(f"[underline]{cmd_name}[/underline]", padding_left=2))
            if cmd.help:
                self._console.print(pad(cmd.help, padding_left=4))
                self._console.print()
            if cmd.options:
                self.print_rows(
                    [
                        (
                            fmt_option(opt, show_full=True, color=self.option_color),
                            self._fmt_help(opt),
                        )
                        for opt in cmd.options_sorted
                    ]
                )
                self._console.print()

        if group.options:
            self._console.print(RichTitles.OPTIONS)
            self._print_options(group.options)
            self._console.print()

        global_options = [parent_option for parent_arg in (parent_args or []) for parent_option in parent_arg.options]
        if global_options:
            self._console.print(RichTitles.GLOBAL_OPTIONS)
            self._print_options(global_options)

        self._print_description(group)

    def print_error(self, message: str):
        self._console.print(f"[red]{message}[/red]")

    def print_invalid_command(self, available_commands: list[str], input_command: str | None = None) -> None:
        msg = "Unknown command"
        if input_command:
            msg = f"Unknown command [bold]{input_command!r}[/bold]"
            suggestions = get_close_matches(input_command, available_commands, n=1, cutoff=0.6)
            if suggestions:
                msg += f". Did you mean [bold]{suggestions[0]!r}[/bold]?"
        _available_cmds = ", ".join(available_commands)
        self.print_error(f'{msg}. Possible commands are "[bold]{_available_cmds}[/bold]"')

    def print_keyword_param_error(self, cmd: str, param: str) -> None:
        self.print_error(f"Could not find keyword parameter [bold]{param!r}[/bold] for command [bold]{cmd!r}[/bold]")

    def print_param_error(self, key: str, cmd: str) -> None:
        self.print_error(f"Could not find value for [bold]{key!r}[/bold] in [bold]{cmd}[/bold]")

    def print_count_error(self, expected_count: int, count: int, cmd: str):
        self.print_error(
            f"Expected {expected_count} positional arguments but got {count} for command [bold]{cmd}[/bold]"
        )

    def print_invalid_value_error(
        self, value: str, literal_choices: list[str], regex_patterns: list[str] | None = None
    ):
        sep = "\n - "
        parts = []
        if literal_choices:
            parts.append(f"Possible values are:{sep}{sep.join(literal_choices)}")
        if regex_patterns:
            parts.append(f"Or matching patterns:{sep}{sep.join(f'/{p}/' for p in regex_patterns)}")
        if parts:
            msg = f"Invalid value [bold]{value}[/bold] found.\n" + "\n".join(parts)
        else:
            msg = f"Invalid value [bold]{value}[/bold] found."
        self.print_error(msg)

    def print_exception(self, exc: BaseException, *, hide_internals: bool = True) -> None:
        """Print an exception traceback with Rich formatting.

        The hide_internals parameter controls whether piou internal frames are
        hidden from the traceback.
        """
        # Lazy imports: saves ~11ms startup cost
        from rich.traceback import Traceback

        suppress: list = []
        if hide_internals:
            import piou

            suppress = [piou]
        tb = Traceback.from_exception(
            type(exc),
            exc,
            exc.__traceback__,
            suppress=suppress,
            show_locals=False,
        )
        self._console.print(tb)
