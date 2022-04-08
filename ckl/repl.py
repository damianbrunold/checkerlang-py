import argparse
import os
import sys

from ckl.errors import CklSyntaxError, CklRuntimeError
from ckl.values import ValueString, ValueList, NULL

import ckl.interpreter
import ckl.parser


def main():
    parser = argparse.ArgumentParser(description="CKL repl")
    parser.add_argument("-s", "--secure", action="store_true")
    parser.add_argument("-l", "--legacy", action="store_true")
    parser.add_argument("-m", "--modulepath", nargs="?")
    parser.add_argument("scripts", nargs="*")
    args = parser.parse_args(sys.argv[1:])

    modulepath = ValueList()
    if args.modulepath:
        modulepath.addItem(ValueString(args.modulepath))

    interpreter = ckl.interpreter.Interpreter(args.secure, args.legacy)
    interpreter.environment.put("checkerlang_module_path", modulepath)

    for scriptfile in args.scripts:
        if os.path.exists(scriptfile):
            with open(scriptfile, encoding="utf-8") as infile:
                script = infile.read()
            interpreter.interpret(script, os.path.basename(scriptfile))

    try:
        line = input("> ")
        while line != "exit":
            try:
                ckl.parser.parse_script(line, "{stdin}")
            except CklSyntaxError as e:
                if e.msg.startswith("Unexpected end of input"):
                    line += input("+ ")
                    continue
            except Exception:
                line += input("+ ")
                continue

            if not line == ";":
                try:
                    value = interpreter.interpret(line, "{stdin}")
                    if value.isReturn():
                        value = value.asReturn().value
                    if value != NULL:
                        print(value)
                except CklRuntimeError as e:
                    print(str(e.value.asString().value)
                          + ": " + e.msg
                          + " (Line " + str(e.pos) + ")")
                    if e.stacktrace:
                        for st in e.stacktrace:
                            print(str(st))
                except CklSyntaxError as e:
                    print(e.msg
                          + ((" (Line " + str(e.pos) + ")") if e.pos else ""))

            line = input("> ")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
