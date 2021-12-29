class DuplicatedCommandError(Exception):
    def __init__(self, msg: str, cmd: str):
        super().__init__(msg)
        self.cmd = cmd


class PosParamsCountError(Exception):
    def __init__(self, msg: str, expected_count: int, count: int,
                 cmd: str = None):
        super().__init__(msg)
        self.expected_count = expected_count
        self.count = count
        self.cmd = cmd


class ParamNotFoundError(Exception):
    def __init__(self, msg: str, key: str, cmd: str = None):
        super().__init__(msg)
        self.key = key
        self.cmd = cmd


class KeywordParamNotFoundError(Exception):
    def __init__(self, msg: str, param: str, cmd: str = None):
        super().__init__(msg)
        self.param = param
        self.cmd = cmd


class CommandNotFoundError(Exception):
    def __init__(self, cmd: str):
        self.cmd = cmd
