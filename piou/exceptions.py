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
