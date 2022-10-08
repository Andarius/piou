from typing import Optional, Any


class CommandException(Exception):
    def __init__(self, msg: str, cmd: Optional[str] = None):
        super().__init__(msg)
        self.cmd = cmd


class DuplicatedCommandError(Exception):
    def __init__(self, msg: str, cmd: str):
        super().__init__(msg)
        self.cmd = cmd


class PosParamsCountError(CommandException):
    """
    Raised when a positional argument is not passed
    """

    def __init__(self, msg: str, expected_count: int, count: int,
                 cmd: Optional[str] = None):
        super().__init__(msg, cmd)
        self.expected_count = expected_count
        self.count = count


class KeywordParamMissingError(CommandException):
    """
    Raised when a required keyword argument is not passed
    """

    def __init__(self, msg: str, param: str, cmd: Optional[str] = None):
        super().__init__(msg, cmd)
        self.param = param


class KeywordParamNotFoundError(CommandException):
    """
    Raised when passing a keyword argument not expected
    by the command
    """

    def __init__(self, msg: str, param: str, cmd: Optional[str] = None):
        super().__init__(msg, cmd)
        self.param = param


class CommandNotFoundError(Exception):
    def __init__(self, valid_commands: list[str],
                 input_args: Optional[tuple[Any, ...]] = None):
        _available_cmds = ', '.join(valid_commands)
        super().__init__(f'Unknown command given. Possible commands are {_available_cmds!r}')
        self.valid_commands = sorted(valid_commands)
        self.input_args = input_args


class InvalidChoiceError(Exception):
    def __init__(self, value: str, choices: list[str]):
        self.value = value
        self.choices = choices
