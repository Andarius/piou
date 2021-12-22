class ShowHelpError(Exception):
    def __init__(self,
                 command: 'Command' = None,
                 commands: dict[str, 'Command'] = None,
                 options: list['CommandOption'] = None,
                 help: str = None,
                 parent_args: list[tuple[str, list['CommandOption']]] = None
                 ):
        self.command = command
        self.commands = commands
        self.options = options
        self.help = help
        self.parent_args = parent_args


class DuplicatedCommandError(Exception):
    def __init__(self, msg: str, cmd: str):
        super().__init__(msg)
        self.cmd = cmd


class PosParamsCountError(Exception):
    def __init__(self, msg: str, expected_count: int, count: int):
        super().__init__(msg)
        self.expected_count = expected_count
        self.count = count


class ParamNotFoundError(Exception):
    def __init__(self, msg: str, key: str):
        super().__init__(msg)
        self.key = key


class CommandNotFoundError(Exception):
    def __init__(self, cmd: str):
        self.cmd = cmd
