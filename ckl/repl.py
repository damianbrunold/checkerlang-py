from ckl.errors import CklSyntaxError, CklRuntimeError
from ckl.values import NULL

import ckl.interpreter
import ckl.parser

def main():
    # TODO secure, legacy flags
    interpreter = ckl.interpreter.Interpreter(False, False)
    # TODO module path
    # TODO process files
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

if __name__ == "__main__":
    main()

