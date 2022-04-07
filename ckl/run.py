import os
import sys

from ckl.values import (
        ValueList, 
        ValueString, 
        NULL
)
from ckl.errors import (
        CklSyntaxError,
        CklRuntimeError
)
from ckl.interpreter import Interpreter

secure = False
legacy = False
scriptname = NULL
scriptargs = []
modulepath = ValueList()

if len(sys.argv) <= 1:
    print("Syntax: ckl-run [--secure] [--legacy] [-I<moduledir>] "
          "scriptname [scriptargs...]", file=sys.stderr)
    sys.exit(1)

in_options = True
for arg in sys.argv[1:]:
    if in_options:
        if arg == "--secure":
            secure = True
        elif arg == "--legacy":
            legacy = True
        elif arg.startswith("-I"):
            modulepath.addItem(ValueString(arg[2:]))
        elif arg.startswith("--"):
            print(f"Unknown option {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            in_options = False
            scriptname = arg
    else:
        scriptargs.append(arg)

if scriptname == NULL:
    print("Syntax: ckl-run [--secure] [--legacy] [-I<moduledir>] "
          "scriptname [scriptargs...]", file=sys.stderr)
    sys.exit(1)

interpreter = Interpreter(secure, legacy)

if not os.path.exists(scriptname):
    print(f"File not found '{scriptname}'", file=sys.stderr)
    sys.exit(1)

args = ValueList()
for scriptarg in scriptargs:
    args.addItem(ValueString(scriptarg))

interpreter.environment.put("args", args)
interpreter.environment.put("scriptname", ValueString(scriptname))
interpreter.environment.put("checkerlang_module_path", modulepath)

with open(scriptname, encoding="utf-8") as infile:
    script = infile.read()

try:
    result = interpreter.interpret(script, scriptname)
    if result != NULL:
        print(str(result))
except CklRuntimeError as e:
    print(str(e.value.asString().value) + ": " + e.msg + " (Line " + str(e.pos) + ")")
    if e.stacktrace:
        for st in e.stacktrace:
            print(str(st))
except CklSyntaxError as e:
    print(e.msg + ((" (Line " + str(e.pos) + ")") if e.pos else ""))
