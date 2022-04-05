import os
import sys

from ckl.errors import CklRuntimeError
from ckl.parser import parse_script
from ckl.functions import (
    Environment, 
    get_base_environment, 
    FuncRun,
)
from ckl.values import (
    StringInput,
    StringOutput,
    ConsoleOutput,
    ValueInput,
    ValueOutput,
    ValueString,
)

class Interpreter:
    def __init__(self, secure=True, legacy=False):
        self.base_environment = get_base_environment(secure, legacy)
        self.environment = self.base_environment.newEnv()
        self.base_environment.put("console", ValueOutput(ConsoleOutput()))
        self.base_environment.put("stdout", ValueOutput(sys.stdout))
        self.base_environment.put("stdin", ValueInput(sys.stdin))
        if not secure:
            self.base_environment.put("run", FuncRun(self))

    def setStandardOutput(self, stdout):
        self.base_environment.put("stdout", ValueOutput(stdout))

    def setStandardInput(self, stdin):
        self.base_environment.put("stdin", ValueInput(stdin))

    def loadFile(self, filename, encoding="utf8"):
        enc = encoding.toLowerCase()
        if enc == 'utf-8':
            enc = 'utf8'
        with open(filename, encoding=encoding) as infile:
            contents = infile.read()
        return interpret(contents, os.path.basename(filename))

    def interpret(self, script, filename, environment=None):
        savedParent = None
        if environment is None:
            env = self.environment
        else:
            environment_ = environment
            while environment_ and environment_.getParent():
                environment_ = environment_.getParent()
            if environment_:
                savedParent = environment_.getParent()
                environment_.withParent(self.environment)
            env = environment
        try:
            result = parse_script(script, filename).evaluate(env)
            if result.isReturn():
                return result.value
            elif result.isBreak():
                raise CklRuntimeError(ValueString("ERROR"), "Cannot use break without surrounding loop", result.asBreak().pos)
            elif result.isContinue():
                raise CklRuntimeError(ValueString("ERROR"), "Cannot use continue without surrounding loop", result.asContinue().pos)
            return result
        finally:
            if savedParent:
                environment_ = environment
                while environment_ and environment_.getParent():
                    environment_ = environment_.getParent()
                if environment_:
                    environment_.withParent(savedParent)
