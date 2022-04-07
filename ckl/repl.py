import os
import sys

from ckl.errors import CklSyntaxError, CklRuntimeError
from ckl.values import ValueString, NULL

import ckl.interpreter
import ckl.parser

def main():
    secure = False
    legacy = False
    for arg in sys.argv:
        if arg == "--secure":
            secure = True
        elif arg == "--legacy":
            legacy = True    
    interpreter = ckl.interpreter.Interpreter(secure, Legacy)

    modulepath = ValueList()
    for arg in sys.argv:
        if arg.startswith("-I"):
            modulepath.addItem(ValueString(arg[2:]))
    interpreter.environment.put("checkerlang_module_path", modulepath)

    for arg in sys.argv:
        if arg in ["--secure", "--legacy"] or arg.startwith("-I"):
            continue
        if os.path.exists(arg):
            with open(arg, encoding="utf-8") as infile:
                script = infile.read()
            interpreter.interpret(script, os.path.basename(arg))

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
                    print(str(e.value.asString().value) + ": " + e.msg + " (Line " + str(e.pos) + ")")
                    if e.stacktrace:
                        for st in e.stacktrace:
                            print(str(st))
                except CklSyntaxError as e:
                    print(e.msg + ((" (Line " + str(e.pos) + ")") if e.pos else ""))

            line = input("> ")
    except EOFError:
        pass

if __name__ == "__main__":
    main()

