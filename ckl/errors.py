class CklSyntaxError(Exception):
    def __init__(self, msg, pos=None):
        self.msg = msg
        self.pos = pos

    def __str__(self):
        if self.pos:
            return f"SYNTAX-ERROR: {self.msg} ({self.pos})"
        else:
            return f"SYNTAX-ERROR: {self.msg}"


class CklRuntimeError(Exception):
    def __init__(self, value, msg, pos=None):
        self.value = value
        self.msg = msg
        self.pos = pos
        self.stacktrace = []

    def __str__(self):
        if self.pos:
            return f"{self.value}: {self.msg} ({self.pos})"
        else:
            return f"{self.value}: {self.msg}"
