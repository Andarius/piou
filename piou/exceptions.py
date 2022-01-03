from typing import Optional


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
    def __init__(self, cmd: str):
        self.cmd = cmd
