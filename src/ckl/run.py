import argparse
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


def main():
    parser = argparse.ArgumentParser(description="CKL run command")
    parser.add_argument("-s", "--secure", action="store_true")
    parser.add_argument("-l", "--legacy", action="store_true")
    parser.add_argument("-m", "--modulepath", nargs="?")
    parser.add_argument("script")
    parser.add_argument("args", nargs="*")
    args = parser.parse_args(sys.argv[1:])

    modulepath = ValueList()
    if args.modulepath:
        modulepath.addItem(ValueString(args.modulepath))

    interpreter = Interpreter(args.secure, args.legacy)

    if not os.path.exists(args.script):
        print(f"File not found '{args.script}'", file=sys.stderr)
        sys.exit(1)

    scriptargs = ValueList()
    for scriptarg in args.args:
        scriptargs.addItem(ValueString(scriptarg))

    interpreter.environment.put("args", scriptargs)
    interpreter.environment.put("scriptname", ValueString(args.script))
    interpreter.environment.put("checkerlang_module_path", modulepath)

    with open(args.script, encoding="utf-8") as infile:
        script = infile.read()

    try:
        result = interpreter.interpret(script, args.script)
        if result != NULL:
            print(str(result))
    except CklRuntimeError as e:
        print(str(e.value.asString().value)
              + ": " + str(e.msg)
              + " (Line " + str(e.pos) + ")")
        if e.stacktrace:
            for st in e.stacktrace:
                print(str(st))
    except CklSyntaxError as e:
        print(e.msg + ((" (Line " + str(e.pos) + ")") if e.pos else ""))


if __name__ == "__main__":
    main()
