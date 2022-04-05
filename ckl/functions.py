import datetime
import json
import pkgutil
import platform
import math
import os
import random
import re
import shutil
import subprocess

from ckl.errors import CklRuntimeError
from ckl.parser import parse_script
from ckl.date import to_oa_date, to_date
from ckl.values import (
    Args,
    StringInput,
    FileInput,
    FileOutput,
    StringOutput,
    Value,
    ValueBoolean,
    ValueControlBreak,
    ValueControlContinue,
    ValueControlReturn,
    ValueDate,
    ValueDecimal,
    ValueFunc,
    ValueInput,
    ValueInt,
    ValueList,
    ValueMap,
    ValueNode,
    ValueObject,
    ValueOutput,
    ValuePattern,
    ValueSet,
    ValueString,
    TRUE,
    FALSE,
    NULL,
)


def get_none_environment():
    return Environment()


def get_base_environment(secure=True, legacy=True):
    result = get_none_environment()
    result.put("checkerlang_secure_mode", ValueBoolean.fromval(secure))
    bind_native(result, "bind_native")
    result.put("NULL", NULL)
    if legacy:
        script = pkgutil.get_data(__name__, "modules/legacy.ckl").decode("utf-8")
        parse_script(script, ":legacy").evaluate(result)
    else:
        script = pkgutil.get_data(__name__, "modules/base.ckl").decode("utf-8")
        parse_script(script, ":base").evaluate(result)
    return result


def add(env, func, alias=None):
    if alias is not None:
        env.put(alias, func)
    env.put(func.name, func)


class Environment:
    def __init__(self, parent=None):
        self.map = dict()
        self.parent = parent
        if self.parent is None:
            self.modules = dict()
            self.modulestack = []

    def withParent(self, parent):
        self.parent = parent
        return self

    def getBase(self):
        current = self
        while current.parent:
            current = current.parent
        return current

    def getSymbols(self):
        result = set()
        if self.parent:
            for symbol in self.parent.getSymbols():
                result.add(symbol)
        for symbol in self.map:
            result.add(symbol)
        return sorted(result)

    def getLocalSymbols(self):
        return self.map.keys()

    def getModules(self):
        return self.getBase().modules

    def pushModuleStack(self, moduleidentifier, pos):
        base = self.getBase()
        if moduleidentifier in base.modulestack:
            raise CklRuntimeError(
                ValueString("ERROR"),
                f"Found circular module dependency ({moduleidentifier})",
                pos,
            )
        base.modulestack.append(moduleidentifier)

    def popModuleStack(self):
        self.getBase().modulestack.pop()

    def put(self, name, value):
        self.map[name] = value

    def set(self, name, value):
        if name in self.map:
            self.map[name] = value
        elif self.parent:
            self.parent.set(name, value)
        else:
            raise CklRuntimeError(
                ValueString("ERROR"), f"{name} is not defined"
            )

    def remove(self, name):
        del self.map[name]

    def newEnv(self):
        return Environment(self)

    def isDefined(self, symbol):
        if symbol in self.map:
            return True
        if self.parent:
            return self.parent.isDefined(symbol)
        return False

    def get(self, symbol, pos=None):
        if symbol in self.map:
            value = self.map[symbol]
            if value is None:
                return NULL
            if isinstance(value, Value):
                return value
            elif isinstance(value, int):
                return ValueInt(value)
            elif isinstance(value, float):
                return ValueDecimal(value)
            elif isinstance(value, bool):
                return ValueBoolean.fromval(value)
            elif isinstance(value, datetime):
                return ValueDate(value)
            else:
                return ValueString(str(value))
        if self.parent:
            return self.parent.get(symbol, pos)
        raise CklRuntimeError(
            ValueString("ERROR"), f"Symbol '{symbol}' not defined", pos
        )


def bind_native(environment, native, alias=None):
    if native == "acos":
        bind_native_fun(environment, FuncAcos(), alias)
    elif native == "add":
        bind_native_fun(environment, FuncAdd(), alias)
    elif native == "append":
        bind_native_fun(environment, FuncAppend(), alias)
    elif native == "asin":
        bind_native_fun(environment, FuncAsin(), alias)
    elif native == "atan":
        bind_native_fun(environment, FuncAtan(), alias)
    elif native == "atan2":
        bind_native_fun(environment, FuncAtan2(), alias)
    elif native == "bind_native":
        bind_native_fun(environment, FuncBindNative(), alias)
    elif native == "bit_and":
        bind_native_fun(environment, FuncBitAnd(), alias)
    elif native == "bit_or":
        bind_native_fun(environment, FuncBitOr(), alias)
    elif native == "bit_not":
        bind_native_fun(environment, FuncBitNot(), alias)
    elif native == "bit_xor":
        bind_native_fun(environment, FuncBitXor(), alias)
    elif native == "bit_rotate_left":
        bind_native_fun(environment, FuncBitRotateLeft(), alias)
    elif native == "bit_rotate_right":
        bind_native_fun(environment, FuncBitRotateRight(), alias)
    elif native == "bit_shift_left":
        bind_native_fun(environment, FuncBitShiftLeft(), alias)
    elif native == "bit_shift_right":
        bind_native_fun(environment, FuncBitShiftRight(), alias)
    elif native == "body":
        bind_native_fun(environment, FuncBody(), alias)
    elif native == "boolean":
        bind_native_fun(environment, FuncBoolean(), alias)
    elif native == "ceiling":
        bind_native_fun(environment, FuncCeiling(), alias)
    elif native == "chr":
        bind_native_fun(environment, FuncChr(), alias)
    elif native == "close":
        bind_native_fun(environment, FuncClose(), alias)
    elif native == "compare":
        bind_native_fun(environment, FuncCompare(), alias)
    elif native == "contains":
        bind_native_fun(environment, FuncContains(), alias)
    elif native == "cos":
        bind_native_fun(environment, FuncCos(), alias)
    elif native == "date":
        bind_native_fun(environment, FuncDate(), alias)
    elif native == "decimal":
        bind_native_fun(environment, FuncDecimal(), alias)
    elif native == "delete_at":
        bind_native_fun(environment, FuncDeleteAt(), alias)
    elif native == "div":
        bind_native_fun(environment, FuncDiv(), alias)
    elif native == "ends_with":
        bind_native_fun(environment, FuncEndsWith(), alias)
    elif native == "equals":
        bind_native_fun(environment, FuncEquals(), alias)
    elif native == "escape_pattern":
        bind_native_fun(environment, FuncEscapePattern(), alias)
    elif native == "eval":
        bind_native_fun(environment, FuncEval(), alias)
    elif native == "execute":
        bind_native_fun(environment, FuncExecute(), alias)
    elif native == "exp":
        bind_native_fun(environment, FuncExp(), alias)
    elif native == "file_input":
        bind_native_fun(environment, FuncFileInput())
    elif native == "file_copy":
        bind_native_fun(environment, FuncFileCopy(), alias)
    elif native == "file_delete":
        bind_native_fun(environment, FuncFileDelete())
    elif native == "file_exists":
        bind_native_fun(environment, FuncFileExists())
    elif native == "file_info":
        bind_native_fun(environment, FuncFileInfo())
    elif native == "file_move":
        bind_native_fun(environment, FuncFileMove(), alias)
    elif native == "file_output":
        bind_native_fun(environment, FuncFileOutput())
    elif native == "find":
        bind_native_fun(environment, FuncFind(), alias)
    elif native == "find_last":
        bind_native_fun(environment, FuncFindLast(), alias)
    elif native == "floor":
        bind_native_fun(environment, FuncFloor(), alias)
    elif native == "format_date":
        bind_native_fun(environment, FuncFormatDate(), alias)
    elif native == "get_env":
        bind_native_fun(environment, FuncGetEnv(), alias)
    elif native == "get_output_string":
        bind_native_fun(environment, FuncGetOutputString(), alias)
    elif native == "greater":
        bind_native_fun(environment, FuncGreater(), alias)
    elif native == "greater_equals":
        bind_native_fun(environment, FuncGreaterEquals(), alias)
    elif native == "identity":
        bind_native_fun(environment, FuncIdentity(), alias)
    elif native == "if_empty":
        bind_native_fun(environment, FuncIfEmpty(), alias)
    elif native == "if_null":
        bind_native_fun(environment, FuncIfNull(), alias)
    elif native == "if_null_or_empty":
        bind_native_fun(environment, FuncIfNullOrEmpty(), alias)
    elif native == "info":
        bind_native_fun(environment, FuncInfo(), alias)
    elif native == "insert_at":
        bind_native_fun(environment, FuncInsertAt(), alias)
    elif native == "int":
        bind_native_fun(environment, FuncInt(), alias)
    elif native == "is_empty":
        bind_native_fun(environment, FuncIsEmpty(), alias)
    elif native == "is_not_empty":
        bind_native_fun(environment, FuncIsNotEmpty(), alias)
    elif native == "is_not_null":
        bind_native_fun(environment, FuncIsNotNull(), alias)
    elif native == "is_null":
        bind_native_fun(environment, FuncIsNull(), alias)
    elif native == "length":
        bind_native_fun(environment, FuncLength(), alias)
    elif native == "less":
        bind_native_fun(environment, FuncLess(), alias)
    elif native == "less_equals":
        bind_native_fun(environment, FuncLessEquals(), alias)
    elif native == "list":
        bind_native_fun(environment, FuncList(), alias)
    elif native == "list_dir":
        bind_native_fun(environment, FuncListDir())
    elif native == "log":
        bind_native_fun(environment, FuncLog(), alias)
    elif native == "lower":
        bind_native_fun(environment, FuncLower(), alias)
    elif native == "ls":
        bind_native_fun(environment, FuncLs(), alias)
    elif native == "make_dir":
        bind_native_fun(environment, FuncMakeDir())
    elif native == "map":
        bind_native_fun(environment, FuncMap(), alias)
    elif native == "matches":
        bind_native_fun(environment, FuncMatches(), alias)
    elif native == "mod":
        bind_native_fun(environment, FuncMod(), alias)
    elif native == "mul":
        bind_native_fun(environment, FuncMul(), alias)
    elif native == "not_equals":
        bind_native_fun(environment, FuncNotEquals(), alias)
    elif native == "object":
        bind_native_fun(environment, FuncObject(), alias)
    elif native == "ord":
        bind_native_fun(environment, FuncOrd(), alias)
    elif native == "parse":
        bind_native_fun(environment, FuncParse(), alias)
    elif native == "parse_date":
        bind_native_fun(environment, FuncParseDate(), alias)
    elif native == "parse_json":
        bind_native_fun(environment, FuncParseJson(), alias)
    elif native == "pattern":
        bind_native_fun(environment, FuncPattern(), alias)
    elif native == "pow":
        bind_native_fun(environment, FuncPow(), alias)
    elif native == "print":
        bind_native_fun(environment, FuncPrint(), alias)
    elif native == "println":
        bind_native_fun(environment, FuncPrintln(), alias)
    elif native == "process_lines":
        bind_native_fun(environment, FuncProcessLines(), alias)
    elif native == "put":
        bind_native_fun(environment, FuncPut(), alias)
    elif native == "random":
        bind_native_fun(environment, FuncRandom(), alias)
    elif native == "range":
        bind_native_fun(environment, FuncRange(), alias)
    elif native == "read":
        bind_native_fun(environment, FuncRead(), alias)
    elif native == "read_all":
        bind_native_fun(environment, FuncReadall(), alias)
    elif native == "readln":
        bind_native_fun(environment, FuncReadln(), alias)
    elif native == "remove":
        bind_native_fun(environment, FuncRemove(), alias)
    elif native == "round":
        bind_native_fun(environment, FuncRound(), alias)
    elif native == "s":
        bind_native_fun(environment, FuncS(), alias)
    elif native == "set":
        bind_native_fun(environment, FuncSet(), alias)
    elif native == "set_seed":
        bind_native_fun(environment, FuncSetSeed(), alias)
    elif native == "sin":
        bind_native_fun(environment, FuncSin(), alias)
    elif native == "sorted":
        bind_native_fun(environment, FuncSorted(), alias)
    elif native == "split":
        bind_native_fun(environment, FuncSplit(), alias)
    elif native == "split2":
        bind_native_fun(environment, FuncSplit2(), alias)
    elif native == "sqrt":
        bind_native_fun(environment, FuncSqrt(), alias)
    elif native == "str_input":
        bind_native_fun(environment, FuncStrInput(), alias)
    elif native == "starts_with":
        bind_native_fun(environment, FuncStartsWith(), alias)
    elif native == "str_output":
        bind_native_fun(environment, FuncStrOutput(), alias)
    elif native == "string":
        bind_native_fun(environment, FuncString(), alias)
    elif native == "sub":
        bind_native_fun(environment, FuncSub(), alias)
    elif native == "sublist":
        bind_native_fun(environment, FuncSublist(), alias)
    elif native == "substr":
        bind_native_fun(environment, FuncSubstr(), alias)
    elif native == "sum":
        bind_native_fun(environment, FuncSum(), alias)
    elif native == "tan":
        bind_native_fun(environment, FuncTan(), alias)
    elif native == "timestamp":
        bind_native_fun(environment, FuncTimestamp(), alias)
    elif native == "trim":
        bind_native_fun(environment, FuncTrim(), alias)
    elif native == "type":
        bind_native_fun(environment, FuncType(), alias)
    elif native == "upper":
        bind_native_fun(environment, FuncUpper(), alias)
    elif native == "zip":
        bind_native_fun(environment, FuncZip(), alias)
    elif native == "zip_map":
        bind_native_fun(environment, FuncZipMap(), alias)
    elif native == "E":
        environment.put(
            "E",
            ValueDecimal(math.e).withInfo(
                "E\n\nThe mathematical constant E (Eulers number)"
            ),
        )
    elif native == "PI":
        environment.put(
            "PI",
            ValueDecimal(math.pi).withInfo(
                "PI\n\nThe mathematical constant PI"
            ),
        )
    elif native == "PS":
        environment.put(
            "PS",
            ValueString(os.path.sep).withInfo(
                "PS\n\nThe OS path separator (posix: /, windows: \\)."
            ),
        )
    elif native == "LS":
        environment.put(
            "LS",
            ValueString(os.linesep).withInfo(
                "PS\n\nThe OS line separator (posix: \\n, windows: \\r\\n)."
            ),
        )
    elif native == "FS":
        environment.put(
            "FS",
            ValueString(os.path.pathsep).withInfo(
                "FS\n\nThe OS field separator (posix: :, windows: ;)."
            ),
        )
    elif native == "OS_NAME":
        environment.put(
            "OS_NAME",
            ValueString(get_os_name()).withInfo(
                "OS_NAME\n\nThe name of the operating system, "
                "one of Windows, Linux, macOS"
            ),
        )
    elif native == "OS_VERSION":
        environment.put(
            "OS_VERSION",
            ValueString(get_os_version()).withInfo(
                "OS_VERSION\n\nThe version of the operating system."
            ),
        )
    elif native == "OS_ARCH":
        environment.put(
            "OS_ARCH",
            ValueString(get_os_arch()).withInfo(
                "OS_ARCH\n\nThe architecture of the operating system, "
                "one of x86, amd64."
            ),
        )
    else:
        raise CklRuntimeError(
            ValueString("ERROR"), "Unknown native " + native
        )


def bind_native_fun(environment, func, alias=None):
    if (
        environment.getBase().get("checkerlang_secure_mode").value
        and not func.secure
    ):
        return
    add(environment, func, alias)


def get_os_version():
    return platform.release()


def get_os_name():
    name = platform.system()
    if name == "Linux":
        return "Linux"
    elif name == "Darwin":
        return "Darwin"
    elif name == "Windows":
        return "Windows"
    else:
        return "Unknown"


def get_os_arch():
    arch = platform.machine()
    if arch == "x86_64":
        return "amd64"
    elif arch == "i386":
        return "x86"
    else:
        return "Unknown"


class FuncAcos(ValueFunc):
    def __init__(self):
        super().__init__("acos")
        self.info = "\r\n".join(
            [
                "acos(x)",
                "",
                "Returns the arcus cosinus of x.",
                "",
                ": acos(1) ==> 0.0",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.acos(args.getNumerical("x").value))


class FuncAdd(ValueFunc):
    def __init__(self):
        super().__init__("add")
        self.info = "\r\n".join(
            [
                "add(a, b)",
                "",
                "Returns the sum of a and b. For numerical values this ",
                "uses usual arithmetic. For lists and strings it ",
                "concatenates. For sets it uses union.",
                "",
                ": add(1, 2) ==> 3",
                ": add(date('20100201'), 3) ==> '20100204000000'",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a.isNull() or b.isNull():
            return NULL

        if a.isInt() and b.isInt():
            return ValueInt(a.value + b.value)

        if a.isNumerical() and b.isNumerical():
            return ValueDecimal(a.asDecimal().value + b.asDecimal().value)

        if a.isList():
            if b.isCollection():
                return (
                    ValueList()
                    .addItems(a.asList().value)
                    .addItems(b.asList().value)
                )
            else:
                return ValueList().addItems(a.asList().value).addItem(b)

        if a.isSet():
            if b.isCollection():
                return (
                    ValueSet()
                    .addItems(a.asSet().value.values())
                    .addItems(b.asSet().value.values())
                )
            else:
                return ValueSet().addItems(a.asSet().value.values()).addItem(b)

        if b.isList():
            result = ValueList()
            result.addItem(a)
            result.addItems(b.asList().value)
            return result

        if b.isSet():
            result = ValueSet()
            result.addItem(a)
            result.addItems(b.asSet().value.values())
            return result

        if a.isDate() and b.isNumerical():
            return ValueDate(
                to_date(to_oa_date(a.value) + args.getAsDecimal("b").value)
            )

        if (a.isString() and b.isAtomic()) or (a.isAtomic() and b.isString()):
            return ValueString(a.asString().value + b.asString().value)

        raise CklRuntimeError(
            ValueString("ERROR"),
            "Cannot add " + a.type() + " and " + b.type(),
            pos,
        )


class FuncAppend(ValueFunc):
    def __init__(self):
        super().__init__("append")
        self.info = "\r\n".join(
            [
                "append(lst, element)",
                "",
                "Appends the element to the list lst.",
                "The lst may also be a set.",
                "Returns the changed list or set.",
                "",
                ": append([1, 2], 3) ==> [1, 2, 3]",
                ": append(<<1, 2>>, 3) ==> <<1, 2, 3>>",
            ]
        )

    def getArgNames(self):
        return ["lst", "element"]

    def execute(self, args, environment, pos):
        lst = args.get("lst")
        element = args.get("element")

        if lst.isList():
            lst.addItem(element)
            return lst

        if lst.isSet():
            lst.addItem(element)
            return lst

        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot append to " + lst.type(), pos
        )


class FuncAsin(ValueFunc):
    def __init__(self):
        super().__init__("asin")
        self.info = "\r\n".join(
            [
                "asin(x)",
                "",
                "Returns the arcus sinus of x.",
                "",
                ": asin(0) ==> 0.0",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.asin(args.getNumerical("x").value))


class FuncAtan(ValueFunc):
    def __init__(self):
        super().__init__("atan")
        self.info = "\r\n".join(
            [
                "atan(x)",
                "",
                "Returns the arcus tangens of x.",
                "",
                ": atan(0) ==> 0.0",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.atan(args.getNumerical("x").value))


class FuncAtan2(ValueFunc):
    def __init__(self):
        super().__init__("atan2")
        self.info = "\r\n".join(
            [
                "atan2(y, x)",
                "",
                "Returns the arcus tangens of y / x.",
                "",
                ": atan2(0, 1) ==> 0.0",
            ]
        )

    def getArgNames(self):
        return ["y", "x"]

    def execute(self, args, environment, pos):
        if args.isNull("y"):
            return NULL
        if args.isNull("x"):
            return NULL
        return ValueDecimal(
            math.atan2(
                args.getNumerical("y").value, args.getNumerical("x").value
            )
        )


class FuncBindNative(ValueFunc):
    def __init__(self):
        super().__init__("bind_native")
        self.info = "\r\n".join(
            [
                "bind_native(native)",
                "bind_native(native, alias)",
                "",
                "Binds a native function in the current environment.",
            ]
        )

    def getArgNames(self):
        return ["native", "alias"]

    def execute(self, args, environment, pos):
        native = args.getString("native").value
        alias = None
        if args.hasArg("alias"):
            alias = args.getString("alias").value
        bind_native(environment, native, alias)
        return NULL


class FuncBitAnd(ValueFunc):
    def __init__(self):
        super().__init__("bit_and")
        self.info = "\r\n".join(
            [
                "bit_and(a, b)",
                "",
                "Performs bitwise and for the two 32bit values a and b.",
                ": bit_and(5, 6) ==> 4",
                ": bit_and(4, 4) ==> 4",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        b = args.getInt("b").value
        return ValueInt(a & b)


class FuncBitOr(ValueFunc):
    def __init__(self):
        super().__init__("bit_or")
        self.info = "\r\n".join(
            [
                "bit_or(a, b)",
                "",
                "Performs bitwise or for the two 32bit values a and b.",
                ": bit_or(1, 2) ==> 3",
                ": bit_or(3, 4) ==> 7",
                ": bit_or(4, 4) ==> 4",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        b = args.getInt("b").value
        return ValueInt(a | b)


class FuncBitNot(ValueFunc):
    def __init__(self):
        super().__init__("bit_not")
        self.info = "\r\n".join(
            [
                "bit_not(a)",
                "",
                "Performs bitwise not for the 32bit value a.",
                ": bit_not(1) ==> 4294967294",
                ": bit_not(0) ==> 4294967295",
            ]
        )

    def getArgNames(self):
        return ["a"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        return ValueInt(~a)


class FuncBitXor(ValueFunc):
    def __init__(self):
        super().__init__("bit_xor")
        self.info = "\r\n".join(
            [
                "bit_xor(a, b)",
                "",
                "Performs bitwise xor for the two 32bit values a and b.",
                ": bit_xor(1, 2) ==> 3",
                ": bit_xor(1, 3) ==> 2",
                ": bit_xor(4, 4) ==> 0",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        b = args.getInt("b").value
        return ValueInt(a ^ b)


class FuncBitRotateLeft(ValueFunc):
    def __init__(self):
        super().__init__("bit_rotate_left")
        self.info = "\r\n".join(
            [
                "bit_rotate_left(a, n)",
                "",
                "Performs bitwise rotate of 32bit value a by ",
                "n bits to the left.",
                ": bit_rotate_left(1, 2) ==> 4",
                ": bit_rotate_left(1, 3) ==> 8",
                ": bit_rotate_left(4, 4) ==> 64",
            ]
        )

    def getArgNames(self):
        return ["a", "n"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        n = args.getInt("n").value
        return ValueInt((a << n) | (a >> (32 - n)))


class FuncBitRotateRight(ValueFunc):
    def __init__(self):
        super().__init__("bit_rotate_right")
        self.info = "\r\n".join(
            [
                "bit_rotate_right(a, n)",
                "",
                "Performs bitwise rotate of 32bit value a by ",
                "n bits to the right.",
                ": bit_rotate_right(1, 2) ==> 1073741824",
                ": bit_rotate_right(1, 3) ==> 536870912",
                ": bit_rotate_right(4, 4) ==> 1073741824",
            ]
        )

    def getArgNames(self):
        return ["a", "n"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        n = args.getInt("n").value
        return ValueInt((a >> n) | (a << (32 - n)))


class FuncBitShiftLeft(ValueFunc):
    def __init__(self):
        super().__init__("bit_shift_left")
        self.info = "\r\n".join(
            [
                "bit_shift_left(a, n)",
                "",
                "Performs bitwise shift of 32bit value a by n ",
                "bits to the left.",
                ": bit_shift_left(1, 2) ==> 4",
                ": bit_shift_left(1, 3) ==> 8",
                ": bit_shift_left(1, 4) ==> 16",
            ]
        )

    def getArgNames(self):
        return ["a", "n"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        n = args.getInt("n").value
        return ValueInt(a << n)


class FuncBitShiftRight(ValueFunc):
    def __init__(self):
        super().__init__("bit_shift_right")
        self.info = "\r\n".join(
            [
                "bit_shift_right(a, n)",
                "",
                "Performs bitwise shift of 32bit value a by ",
                "n bits to the right.",
                ": bit_shift_right(4, 1) ==> 2",
                ": bit_shift_right(4, 3) ==> 0",
                ": bit_shift_right(4, 2) ==> 1",
            ]
        )

    def getArgNames(self):
        return ["a", "n"]

    def execute(self, args, environment, pos):
        a = args.getInt("a").value
        n = args.getInt("n").value
        return ValueInt(a >> n)


class FuncBody(ValueFunc):
    def __init__(self):
        super().__init__("body")
        self.info = "\r\n".join(
            [
                "body(f)",
                "",
                "Returns the body of the lambda f.",
                "",
                ": body(fn(x) 2 * x) ==> '(mul 2, x)'",
            ]
        )

    def getArgNames(self):
        return ["f"]

    def execute(self, args, environment, pos):
        f = args.get("f")
        if isinstance(f, FuncLambda):
            return ValueNode(f.body)
        raise CklRuntimeError(
            ValueString("ERROR"),
            "f is not a lambda function",
            pos
        )


class FuncBoolean(ValueFunc):
    def __init__(self):
        super().__init__("boolean")
        self.info = "\r\n".join(
            [
                "boolean(obj)",
                "",
                "Converts the obj to a boolean, if possible.",
                "",
                ": boolean(1) ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return args.getAsBoolean("obj")


class FuncCeiling(ValueFunc):
    def __init__(self):
        super().__init__("ceiling")
        self.info = "\r\n".join(
            [
                "ceiling(x)",
                "",
                "Returns the integral decimal value that is ",
                "equal to or next higher than x.",
                "",
                ": ceiling(1.3) ==> 2.0",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.ceil(args.getNumerical("x").value))


class FuncChr(ValueFunc):
    def __init__(self):
        super().__init__("chr")
        self.info = "\r\n".join(
            [
                "chr(n)",
                "",
                "Returns a single character string for the ",
                "code point integer n.",
                "",
                ": chr(97) ==> 'a'",
                ": chr(32) ==> ' '",
            ]
        )

    def getArgNames(self):
        return ["n"]

    def execute(self, args, environment, pos):
        if args.isNull("n"):
            return NULL
        return ValueString(chr(args.getInt("n").value))


class FuncClose(ValueFunc):
    def __init__(self):
        super().__init__("close")
        self.info = "\r\n".join(
            [
                "close(conn)",
                "",
                "Closes the input or output connection and ",
                "releases system resources.",
            ]
        )

    def getArgNames(self):
        return ["conn"]

    def execute(self, args, environment, pos):
        conn = args.get("conn")
        if conn.isInput() or conn.isOutput():
            try:
                conn.close()
            except Exception:
                raise CklRuntimeError(
                    ValueString("ERROR"), "Could not close connection", pos
                )
            return NULL
        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot close " + conn.type(), pos
        )


class FuncCompare(ValueFunc):
    def __init__(self):
        super().__init__("compare")
        self.info = "\r\n".join(
            [
                "compare(a, b)",
                "",
                "Returns an int less than 0 if a is less than b,",
                "0 if a is equal to b, and an int greater than 0",
                "if a is greater than b.",
                "",
                ": compare(1, 2) < 0 ==> TRUE",
                ": compare(3, 1) > 0 ==> TRUE",
                ": compare(1, 1) == 0 ==> TRUE",
                ": compare('1', 2) < 0 ==> TRUE",
                ": compare('2', 1) < 0 ==> TRUE",
                ": compare(100, '100') > 0 ==> TRUE",
                ": compare(NULL, 1) > 0 ==> TRUE",
                ": compare(NULL, NULL) == 0 ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a < b:
            return ValueInt(-1)
        elif a > b:
            return ValueInt(1)
        else:
            return ValueInt(0)


class FuncContains(ValueFunc):
    def __init__(self):
        super().__init__("contains")
        self.info = "\r\n".join(
            [
                "contains(obj, part)",
                "",
                "Returns TRUE if the string obj contains part.",
                "If obj is a list, set or map, TRUE is returned,",
                "if part is contained.",
                "",
                ": contains('abcdef', 'abc') ==> TRUE",
                ": contains('abcdef', 'cde') ==> TRUE",
                ": contains('abcdef', 'def') ==> TRUE",
                ": contains('abcdef', 'efg') ==> FALSE",
                ": contains(NULL, 'abc') ==> FALSE",
                ": contains([1, 2, 3], 2) ==> TRUE",
                ": <<1, 2, 3>> !> contains(3) ==> TRUE",
                ": <<<a => 1, b => 2>>> !> contains('b') ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["obj", "part"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return FALSE
        obj = args.get("obj")
        if obj.isList() or obj.isSet() or obj.isMap() or obj.isObject():
            return ValueBoolean.fromval(args.get("part") in obj.value)
        return ValueBoolean.fromval(
            str(obj).find(args.getString("part").value) != -1
        )


class FuncCos(ValueFunc):
    def __init__(self):
        super().__init__("cos")
        self.info = "\r\n".join(
            [
                "cos(x)",
                "",
                "Returns the cosinus of x.",
                "",
                ": cos(PI) ==> -1.0",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.cos(args.getNumerical("x").value))


class FuncDate(ValueFunc):
    def __init__(self):
        super().__init__("date")
        self.info = "\r\n".join(
            [
                "date(obj)",
                "",
                "Converts the obj to a date, if possible.",
                "If obj is a string, the format yyyyMMdd is assumed.",
                "If self fails, the fallback yyyyMMddHH is tried.",
                "If self fails, the fallback yyyyMMddHHmmss is tried.",
                "",
                "See parse_date for handling other formats.",
                "",
                ": string(date('20170102')) ==> '20170102000000'",
                ": string(date('2017010212')) ==> '20170102120000'",
                ": string(date('20170102123456')) ==> '20170102123456'",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        if not args.hasArg("obj"):
            return ValueDate(datetime.datetime.now())
        return args.getAsDate("obj")


class FuncDecimal(ValueFunc):
    def __init__(self):
        super().__init__("decimal")
        self.info = "\r\n".join(
            [
                "decimal(obj)",
                "",
                "Converts the obj to a decimal, if possible.",
                "",
                ": decimal('1.2') ==> 1.2",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return args.getAsDecimal("obj")


class FuncDeleteAt(ValueFunc):
    def __init__(self):
        super().__init__("delete_at")
        self.info = "\r\n".join(
            [
                "delete_at(lst, index)",
                "",
                "Removes the element at the given index from the list lst.",
                "The list is changed in place. Returns the removed element ",
                "or NULL, if no element was removed",
                "",
                ": delete_at(['a', 'b', 'c', 'd'], 2) ==> 'c'",
                ": delete_at(['a', 'b', 'c', 'd'], -3) ==> 'b'",
                ": def lst=['a','b','c','d']; delete_at(lst, 2); "
                "lst ==> ['a', 'b', 'd']",
                ": delete_at(['a', 'b', 'c', 'd'], 4) ==> NULL",
            ]
        )

    def getArgNames(self):
        return ["lst", "index"]

    def execute(self, args, environment, pos):
        lst = args.get("lst")
        index = args.getInt("index").value

        if lst.isList():
            return lst.deleteAt(index)

        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot delete from " + lst.type(), pos
        )


class FuncDiv(ValueFunc):
    def __init__(self):
        super().__init__("div")
        self.info = "\r\n".join(
            [
                "div(a, b)",
                "",
                "Returns the value of a divided by b. If both values are ",
                "ints, then the result is also an int. Otherwise, it is ",
                "a decimal.",
                "",
                ": div(6, 2) ==> 3",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a.isNull() or b.isNull():
            return NULL

        if a.isInt() and b.isInt():
            divisor = b.value
            if divisor == 0:
                if environment.isDefined("DIV_0_VALUE") and environment.get(
                    "DIV_0_VALUE", pos
                ):
                    return environment.get("DIV_0_VALUE", pos)
                raise CklRuntimeError(
                    ValueString("ERROR"), "divide by zero", pos
                )
            return ValueInt(math.trunc(a.value / divisor))

        if a.isNumerical() and b.isNumerical():
            divisor = b.asDecimal().value
            if divisor == 0.0:
                if environment.isDefined("DIV_0_VALUE") and environment.get(
                    "DIV_0_VALUE", pos
                ):
                    return environment.get("DIV_0_VALUE", pos)
                raise CklRuntimeError(
                    ValueString("ERROR"), "divide by zero", pos
                )
            return ValueDecimal(a.asDecimal().value / divisor)

        raise CklRuntimeError(
            ValueString("ERROR"),
            "Cannot divide " + a.type() + " by " + b.type(),
            pos,
        )


class FuncEndsWith(ValueFunc):
    def __init__(self):
        super().__init__("ends_with")
        self.info = "\r\n".join(
            [
                "ends_with(str, part)",
                "",
                "Returns TRUE if the string str ends with part.",
                "",
                ": ends_with('abcdef', 'def') ==> TRUE",
                ": ends_with('abcdef', 'abc') ==> FALSE",
                ": ends_with(NULL, 'abc') ==> FALSE",
            ]
        )

    def getArgNames(self):
        return ["str", "part"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return FALSE
        return ValueBoolean.fromval(
            args.getString("str").value.endswith(args.getString("part").value)
        )


class FuncEquals(ValueFunc):
    def __init__(self):
        super().__init__("equals")
        self.info = "\r\n".join(
            [
                "equals(a, b)",
                "",
                "Returns TRUE if a is equals to b.",
                "",
                "Integer values are propagated to decimal values, ",
                "if required.",
                "",
                ": equals(1, 2) ==> FALSE",
                ": equals(1, 1) ==> TRUE",
                ": equals(1, 1.0) ==> TRUE",
                ": equals('a', 'b') ==> FALSE",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")
        return ValueBoolean.fromval(a == b)


class FuncEscapePattern(ValueFunc):
    def __init__(self):
        super().__init__("escape_pattern")
        self.info = "\r\n".join(
            [
                "escape_pattern(s)",
                "",
                "Escapes special characters in the string s, so that",
                "the result can be used in pattern matching to match",
                "the literal string.",
                "",
                "Currently, the | and . characters are escaped.",
                "",
                ": escape_pattern('|') ==> '\\\\|'",
                ": escape_pattern('|.|') ==> '\\\\|\\\\.\\\\|'",
            ]
        )

    def getArgNames(self):
        return ["s"]

    def execute(self, args, environment, pos):
        if args.isNull("s"):
            return NULL
        value = args.getString("s").value
        return ValueString(value.replace("|", "\\|").replace(".", "\\."))


class FuncEval(ValueFunc):
    def __init__(self):
        super().__init__("eval")
        self.info = "\r\n".join(
            [
                "eval(s)",
                "",
                "Evaluates the string or node s.",
                "",
                ": eval('1+1') ==> 2",
            ]
        )

    def getArgNames(self):
        return ["s"]

    def execute(self, args, environment, pos):
        if args.get("s").isNode():
            return args.getAsNode("s").value.evaluate(environment)
        s = args.getString("s").value
        try:
            node = parse_script(s, pos.filename)
            return node.evaluate(environment)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot evaluate expression", pos
            )


class FuncExecute(ValueFunc):
    def __init__(self):
        super().__init__("execute")
        self.info = "\r\n".join(
            [
                "execute(program, args, work_dir = NULL, echo = FALSE, "
                "output_file = NULL)",
                "",
                "Executes the program and provides the specified ",
                "arguments in the list args.",
            ]
        )
        self.secure = False

    def getArgNames(self):
        return ["program", "args", "work_dir", "echo", "output_file"]

    def execute(self, args, environment, pos):
        program = args.getString("program").value
        arglist = []
        if not args.get("args").isList():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Expected argument list but got " + args.get("args").type(),
                pos,
            )
        for arg in args.get("args").value:
            arglist.append(arg.asString().value)

        work_dir = None
        if args.hasArg("work_dir"):
            work_dir = args.getString("work_dir").value

        echo = False
        if args.hasArg("echo"):
            echo = args.getBoolean("echo").value

        output_file = None
        if args.hasArg("output_file"):
            output_file = args.getString("output_file").value

        if echo:
            print(" ".join([program] + arglist))

        if output_file is not None:
            # TODO directly pipe output to dest file
            p = subprocess.run(
                [program] + arglist,
                cwd=(work_dir if work_dir else None),
                capture_output=True,
                encoding="utf-8",
            )
            with open(output_file, "w", encoding="utf-8") as outfile:
                outfile.write(p.stdout)
            return ValueInt(p.returncode)
        else:
            p = subprocess.run(
                [program] + arglist, cwd=(work_dir if work_dir else None)
            )
            return ValueInt(p.returncode)


class FuncExp(ValueFunc):
    def __init__(self):
        super().__init__("exp")
        self.info = "\r\n".join(
            ["exp(x)", "", "Returns the power e ^ x.", "", ": exp(0) ==> 1"]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.exp(args.getNumerical("x").value))


class FuncFileInput(ValueFunc):
    def __init__(self):
        super().__init__("file_input")
        self.info = "\r\n".join(
            [
                "file_input(filename, encoding = 'UTF-8')",
                "",
                "Returns an input object, that reads the characters ",
                "from the given file.",
            ]
        )
        self.secure = False

    def getArgNames(self):
        return ["filename", "encoding"]

    def execute(self, args, environment, pos):
        filename = args.getString("filename").value
        encoding = "utf-8"
        if args.hasArg("encoding"):
            encoding = args.getString("encoding").value
        try:
            return ValueInput(FileInput(filename, encoding))
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot open file " + filename, pos
            )


class FuncFileCopy(ValueFunc):
    def __init__(self):
        super().__init__("file_copy")
        self.info = "\r\n".join(
            ["file_copy(src, dest)", "", "Copies the specified file."]
        )
        self.secure = False

    def getArgNames(self):
        return ["src", "dest"]

    def execute(self, args, environment, pos):
        src = args.getString("src").value
        dest = args.getString("dest").value
        shutil.copy2(src, dest)
        return NULL


class FuncFileDelete(ValueFunc):
    def __init__(self):
        super().__init__("file_delete")
        self.info = "\r\n".join(
            ["file_delete(filename)", "", "Deletes the specified file."]
        )
        self.secure = False

    def getArgNames(self):
        return ["filename"]

    def execute(self, args, environment, pos):
        filename = args.getString("filename").value
        try:
            if os.path.isdir(filename):
                os.rmdir(filename)
            else:
                os.remove(filename)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot delete file " + filename, pos
            )
        return NULL


class FuncFileExists(ValueFunc):
    def __init__(self):
        super().__init__("file_exists")
        self.info = "\r\n".join(
            [
                "file_exists(filename)",
                "",
                "Returns TRUE if the specified file exists.",
            ]
        )
        self.secure = False

    def getArgNames(self):
        return ["filename"]

    def execute(self, args, environment, pos):
        filename = args.getString("filename").value
        return ValueBoolean.fromval(os.path.exists(filename))


class FuncFileInfo(ValueFunc):
    def __init__(self):
        super().__init__("file_info")
        self.info = "\r\n".join(
            [
                "file_info(filename)",
                "",
                "Returns information about the specified file (e.g. ",
                "modification date, size).",
            ]
        )
        self.secure = False

    def getArgNames(self):
        return ["filename"]

    def execute(self, args, environment, pos):
        filename = args.getString("filename").value
        result = ValueObject()
        try:
            stats = os.lstat(filename)
            result.addItem("size", ValueInt(stats.st_size))
            result.addItem(
                "is_dir", ValueBoolean.fromval(os.path.isdir(filename))
            )
            result.addItem(
                "modified",
                ValueDate(datetime.datetime.fromtimestamp(stats.st_mtime)),
            )
            result.addItem(
                "created",
                ValueDate(datetime.datetime.fromtimestamp(stats.st_ctime)),
            )
            return result
        except Exception:
            return NULL


class FuncFileMove(ValueFunc):
    def __init__(self):
        super().__init__("file_move")
        self.info = "\r\n".join(
            ["file_move(src, dest)", "", "Moves the specified file."]
        )
        self.secure = False

    def getArgNames(self):
        return ["src", "dest"]

    def execute(self, args, environment, pos):
        src = args.getString("src").value
        dest = args.getString("dest").value
        os.rename(src, dest)
        return NULL


class FuncFileOutput(ValueFunc):
    def __init__(self):
        super().__init__("file_output")
        self.info = "\r\n".join(
            [
                "file_output(filename, encoding = 'UTF-8', append = FALSE)",
                "",
                "Returns an output object, that writes to the given file. If",
                "the file exists it is overwritten.",
            ]
        )
        self.secure = False

    def getArgNames(self):
        return ["filename", "encoding", "append"]

    def execute(self, args, environment, pos):
        filename = args.getString("filename").value
        encoding = "utf-8"
        if args.hasArg("encoding"):
            encoding = args.getString("encoding").value
        append = False
        if args.hasArg("append"):
            append = args.getAsBoolean("append").value
        try:
            return ValueOutput(FileOutput(filename, encoding, append))
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot open file " + filename, pos
            )


class FuncFind(ValueFunc):
    def __init__(self):
        super().__init__("find")
        self.info = "\r\n".join(
            [
                "find(obj, part, key = identity, start = 0)",
                "",
                "Returns the index of the first occurence of part in obj.",
                "If part is not contained in obj, then -1 is returned. ",
                "Start specifies the search start index. It defaults to 0.",
                "Obj can be a string or a list. In case of a string, part ",
                "can be any substring, in case of a list, a single element.",
                "In case of lists, the elements can be accessed using the",
                "key function.",
                "",
                ": find('abcdefg', 'cde') ==> 2",
                ": find('abc|def|ghi', '|', start = 4) ==> 7",
                ": find('abcxyabc', 'abc', start = 5) ==> 5",
                ": find([1, 2, 3, 4], 3) ==> 2",
                ": find(['abc', 'def'], 'e', key = fn(x) x[1]) ==> 1",
            ]
        )

    def getArgNames(self):
        return ["obj", "part", "key", "start"]

    def execute(self, args, environment, pos):
        if args.isNull("obj"):
            return NULL
        obj = args.get("obj")
        start = args.getInt("start", 0).value
        key = args.getFunc("key") if args.hasArg("key") else None
        if obj.isString():
            part = args.getString("part").value
            start = args.getInt("start", 0).value
            return ValueInt(obj.value.find(part, start))
        elif obj.isList():
            env = environment
            if key:
                env = environment.newEnv()
            item = args.get("part")
            lst = obj.value
            for idx in range(len(lst)):
                elem = lst[idx]
                if key:
                    elem = key.execute(
                        Args(pos).addArg(key.getArgNames()[0], elem), env, pos
                    )
                if elem == item:
                    return ValueInt(idx)
            return ValueInt(-1)
        raise CklRuntimeError(
            ValueString("ERROR"),
            "Find only works with strings and lists",
            pos
        )


class FuncFindLast(ValueFunc):
    def __init__(self):
        super().__init__("find_last")
        self.info = "\r\n".join(
            [
                "find_last(obj, part, key = identity, start = length(obj)-1)",
                "",
                "Returns the index of the last  occurence of part in obj.",
                "If part is not contained in obj, then -1 is returned. ",
                "Start specifies the search start index. It defaults to ",
                "length(obj) - 1.",
                "Obj can be a string or a list. In case of a string, part ",
                "can be any substring, in case of a list, a single element.",
                "In case of lists, the elements can be accessed using the",
                "key function.",
                "",
                ": find_last('abcdefgcdexy', 'cde') ==> 7",
                ": find_last('abc|def|ghi|jkl', '|', start = 10) ==> 7",
                ": find_last('abcxyabc', 'abc', start = 4) ==> 0",
                ": find_last([1, 2, 3, 4, 3], 3) ==> 4",
                ": find_last(['abc', 'def'], 'e', key = fn(x) x[1]) ==> 1",
            ]
        )

    def getArgNames(self):
        return ["obj", "part", "key", "start"]

    def execute(self, args, environment, pos):
        if args.isNull("obj"):
            return NULL
        obj = args.get("obj")
        key = args.getFunc("key") if args.hasArg("key") else None
        if obj.isString():
            s = obj.value
            part = args.getString("part").value
            start = args.getInt("start", len(s) - 1).value
            return ValueInt(obj.value.rfind(part, 0, start))
        elif obj.isList():
            env = environment
            if key:
                env = environment.newEnv()
            item = args.get("part")
            lst = obj.value
            start = args.getInt("start", len(lst) - 1).value
            for idx in range(start, -1, -1):
                elem = lst[idx]
                if key:
                    elem = key.execute(
                        Args(pos).addArg(key.getArgNames()[0], elem), env, pos
                    )
                if elem == item:
                    return ValueInt(idx)
            return ValueInt(-1)
        raise CklRuntimeError(
            ValueString("ERROR"),
            "Find_last only works with strings and lists",
            pos,
        )


class FuncFloor(ValueFunc):
    def __init__(self):
        super().__init__("floor")
        self.info = "\r\n".join(
            [
                "floor(x)",
                "",
                "Returns the integral decimal value that is equal to or ",
                "next lower than x.",
                "",
                ": floor(1.3) ==> 1.0",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.floor(args.getNumerical("x").value))


class FuncFormatDate(ValueFunc):
    def __init__(self):
        super().__init__("format_date")
        self.info = "\r\n".join(
            [
                "format_date(date, fmt = 'yyyy-MM-dd HH:mm:ss')",
                "",
                "Formats the date value according to fmt and returns ",
                "a string value.",
                "",
                ": format_date(date('20170102')) ==> '2017-01-02 00:00:00'",
                ": format_date(NULL) ==> NULL",
                ": format_date(date('2017010212'), fmt = 'HH') ==> '12'",
            ]
        )

    def getArgNames(self):
        return ["date", "fmt"]

    def execute(self, args, environment, pos):
        if args.isNull("date"):
            return NULL
        date = args.getDate("date").value
        fmt = args.getString("fmt", "yyyy-MM-dd HH:mm:ss").value
        if fmt.find("yyyy") != -1:
            fmt = fmt.replace("yyyy", self.fill(date.year, 4))
        if fmt.find("yy") != -1:
            fmt = fmt.replace("yy", self.fill(date.year % 100, 2))
        if fmt.find("MM") != -1:
            fmt = fmt.replace("MM", self.fill(date.month, 2))
        if fmt.find("dd") != -1:
            fmt = fmt.replace("dd", self.fill(date.day, 2))
        if fmt.find("HH") != -1:
            fmt = fmt.replace("HH", self.fill(date.hour, 2))
        if fmt.find("mm") != -1:
            fmt = fmt.replace("mm", self.fill(date.minute, 2))
        if fmt.find("ss") != -1:
            fmt = fmt.replace("ss", self.fill(date.second, 2))
        return ValueString(fmt)

    def fill(self, val, length=2):
        result = str(val)
        while len(result) < length:
            result = "0" + result
        return result


class FuncGetEnv(ValueFunc):
    def __init__(self):
        super().__init__("get_env")
        self.info = "\r\n".join(
            [
                "get_env(var)",
                "",
                "Returns the value of the environment variable var.",
            ]
        )

    def getArgNames(self):
        return ["var"]

    def execute(self, args, environment, pos):
        return ValueString(os.environ.get(args.getString("var").value, ""))


class FuncGetOutputString(ValueFunc):
    def __init__(self):
        super().__init__("get_output_string")
        self.info = "\r\n".join(
            [
                "get_output_string(output)",
                "",
                "Returns the value of a string output object.",
                "",
                ": do def o = str_output(); print('abc', out = o); "
                "get_output_string(o); end ==> 'abc'",
            ]
        )

    def getArgNames(self):
        return ["output"]

    def execute(self, args, environment, pos):
        output = args.getOutput("output")
        return ValueString(output.output.output)


class FuncGreater(ValueFunc):
    def __init__(self):
        super().__init__("greater")
        self.info = "\r\n".join(
            [
                "greater(a, b)",
                "",
                "Returns TRUE if a is greater than b.",
                "",
                ": greater(1, 2) ==> FALSE",
                ": greater(1, 1) ==> FALSE",
                ": greater(2, 1) ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")
        return ValueBoolean.fromval(a > b)


class FuncGreaterEquals(ValueFunc):
    def __init__(self):
        super().__init__("greater_equals")
        self.info = "\r\n".join(
            [
                "greater_equals(a, b)",
                "",
                "Returns TRUE if a is greater than or equals to b.",
                "",
                ": greater_equals(1, 2) ==> FALSE",
                ": greater_equals(1, 1) ==> TRUE",
                ": greater_equals(2, 1) ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")
        return ValueBoolean.fromval(a >= b)


class FuncIdentity(ValueFunc):
    def __init__(self):
        super().__init__("identity")
        self.info = "\r\n".join(
            [
                "identity(obj)",
                "",
                "Returns obj.",
                "",
                ": identity(1) ==> 1",
                ": identity('a') ==> 'a'",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return args.get("obj")


class FuncIfEmpty(ValueFunc):
    def __init__(self):
        super().__init__("if_empty")
        self.info = "\r\n".join(
            [
                "if_empty(a, b)",
                "",
                "Returns b if a is an empty string otherwise returns a.",
                "",
                ": if_empty(1, 2) ==> 1",
                ": if_empty('', 2) ==> 2",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        if a.isString() and len(a.value) == 0:
            return args.get("b")
        return a


class FuncIfNull(ValueFunc):
    def __init__(self):
        super().__init__("if_null")
        self.info = "\r\n".join(
            [
                "if_null(a, b)",
                "",
                "Returns b if a is NULL otherwise returns a.",
                "",
                ": if_null(1, 2) ==> 1",
                ": if_null(NULL, 2) ==> 2",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        if a.isNull():
            return args.get("b")
        return a


class FuncIfNullOrEmpty(ValueFunc):
    def __init__(self):
        super().__init__("if_null_or_empty")
        self.info = "\r\n".join(
            [
                "if_null_or_empty(a, b)",
                "",
                "Returns b if a is None or an empty string otherwise ",
                "returns a.",
                "",
                ": if_null_or_empty(1, 2) ==> 1",
                ": if_null_or_empty(NULL, 2) ==> 2",
                ": if_null_or_empty('', 2) ==> 2",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        if a.isNull():
            return args.get("b")
        if a.isString() and len(a.value) == 0:
            return args.get("b")
        return a


class FuncInfo(ValueFunc):
    def __init__(self):
        super().__init__("info")
        self.info = "\r\n".join(
            ["info(obj)", "", "Returns the info associated with an object."]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return ValueString(args.get("obj").info)


class FuncInsertAt(ValueFunc):
    def __init__(self):
        super().__init__("insert_at")
        self.info = "\r\n".join(
            [
                "insert_at(lst, index, value)",
                "",
                "Inserts the element at the given index of the list lst.",
                "The list is changed in place. Returns the changed list.",
                "If index is out of bounds, the list is not changed at all.",
                "",
                ": insert_at([1, 2, 3], 0, 9) ==> [9, 1, 2, 3]",
                ": insert_at([1, 2, 3], 2, 9) ==> [1, 2, 9, 3]",
                ": insert_at([1, 2, 3], 3, 9) ==> [1, 2, 3, 9]",
                ": insert_at([1, 2, 3], -1, 9) ==> [1, 2, 3, 9]",
                ": insert_at([1, 2, 3], -2, 9) ==> [1, 2, 9, 3]",
                ": insert_at([1, 2, 3], 4, 9) ==> [1, 2, 3]",
            ]
        )

    def getArgNames(self):
        return ["lst", "index", "value"]

    def execute(self, args, environment, pos):
        lst = args.get("lst")

        if not lst.isList():
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot insert into " + lst.type(), pos
            )

        index = args.getInt("index").value
        if index < 0:
            index = len(lst.value) + index + 1

        value = args.get("value")

        return lst.insertAt(index, value)


class FuncInt(ValueFunc):
    def __init__(self):
        super().__init__("int")
        self.info = "\r\n".join(
            [
                "int(obj)",
                "",
                "Converts the obj to an int, if possible.",
                "",
                ": int('1') ==> 1",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return args.getAsInt("obj")


class FuncIsEmpty(ValueFunc):
    def __init__(self):
        super().__init__("is_empty")
        self.info = "\r\n".join(
            [
                "is_empty(obj)",
                "",
                "Returns TRUE, if the obj is empty.",
                "Lists, sets and maps are empty, if they do not contain ",
                "elements. Strings are empty, if the contain no characters.",
                "NULL is always empty.",
                "",
                ": is_empty(NULL) ==> TRUE",
                ": is_empty(1) ==> FALSE",
                ": is_empty([]) ==> TRUE",
                ": is_empty(<<>>) ==> TRUE",
                ": is_empty(set([1, 2])) ==> FALSE",
                ": is_empty('') ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        obj = args.get("obj")
        if obj.isNull():
            return TRUE
        if obj.isNumerical():
            return FALSE
        if obj.isString():
            return ValueBoolean.fromval(obj.value == "")
        if obj.isList():
            return ValueBoolean.fromval(len(obj) == 0)
        if obj.isSet():
            return ValueBoolean.fromval(len(obj) == 0)
        if obj.isMap():
            return ValueBoolean.fromval(len(obj) == 0)
        if obj.isObject():
            return ValueBoolean.fromval(len(obj) == 0)
        return FALSE


class FuncIsNotEmpty(ValueFunc):
    def __init__(self):
        super().__init__("is_not_empty")
        self.info = "\r\n".join(
            [
                "is_not_empty(obj)",
                "",
                "Returns TRUE, if the obj is not empty.",
                "Lists, sets and maps are empty, if they do not contain",
                "elements. Strings are empty, if the contain no characters.",
                "NULL is always empty.",
                "",
                ": is_not_empty([]) ==> FALSE",
                ": is_not_empty(set([1, 2])) ==> TRUE",
                ": is_not_empty('a') ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        obj = args.get("obj")
        if obj.isNull():
            return FALSE
        if obj.isNumerical():
            return TRUE
        if obj.isString():
            return ValueBoolean.fromval(obj.value != "")
        if obj.isList():
            return ValueBoolean.fromval(len(obj) > 0)
        if obj.isSet():
            return ValueBoolean.fromval(len(obj) > 0)
        if obj.isMap():
            return ValueBoolean.fromval(len(obj) > 0)
        if obj.isObject():
            return ValueBoolean.fromval(len(obj) > 0)
        return TRUE


class FuncIsNotNull(ValueFunc):
    def __init__(self):
        super().__init__("is_not_None")
        self.info = "\r\n".join(
            [
                "is_not_None(obj)",
                "",
                "Returns TRUE, if the obj is not NULL.",
                "",
                ": is_not_None('') ==> TRUE",
                ": is_not_None(1) ==> TRUE",
                ": is_not_None(NULL) ==> FALSE",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return ValueBoolean.fromval(not args.get("obj").isNull())


class FuncIsNull(ValueFunc):
    def __init__(self):
        super().__init__("is_None")
        self.info = "\r\n".join(
            [
                "is_None(obj)",
                "",
                "Returns TRUE, if the obj is NULL.",
                "",
                ": is_None('') ==> FALSE",
                ": is_None(1) ==> FALSE",
                ": is_None(NULL) ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return ValueBoolean.fromval(args.get("obj").isNull())


class FuncLambda(ValueFunc):
    def __init__(self, lexicalEnv):
        super().__init__("lambda")
        self.lexicalEnv = lexicalEnv
        self.argNames = []
        self.defValues = []
        self.body = None

    def getArgNames(self):
        return self.argNames

    def setName(self, name):
        self.name = name

    def addArg(self, name, defaultValue=None):
        self.argNames.append(name)
        self.defValues.append(defaultValue)

    def setBody(self, body):
        self.body = body

    def execute(self, args, environment, pos):
        env = self.lexicalEnv.newEnv()
        for i in range(len(self.argNames)):
            if args.hasArg(self.argNames[i]):
                env.put(self.argNames[i], args.get(self.argNames[i]))
            elif self.defValues[i] is not None:
                env.put(self.argNames[i], self.defValues[i].evaluate(env))
            else:
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    "Missing argument " + self.argNames[i],
                    pos,
                )
        result = self.body.evaluate(env)
        if isinstance(result, ValueControlReturn):
            return result.value
        elif isinstance(result, ValueControlBreak):
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot use break without surrounding loop",
                result.pos,
            )
        elif isinstance(result, ValueControlContinue):
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot use continue without surrounding loop",
                result.pos,
            )
        return result


class FuncLength(ValueFunc):
    def __init__(self):
        super().__init__("length")
        self.info = "\r\n".join(
            [
                "length(obj)",
                "",
                "Returns the length of obj. This only works for strings,",
                "lists, sets and maps.",
                "",
                ": length('123') ==> 3",
                ": length([1, 2, 3]) ==> 3",
                ": length(<<1, 2, 3>>) ==> 3",
                ": <<<'a' => 1, 'b' => 2, 'c' =>3>>> !> length() ==> 3",
                ": length(object()) ==> 0",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        arg = args.get("obj")
        if arg.isString():
            return ValueInt(len(arg.value))
        if arg.isList():
            return ValueInt(len(arg.value))
        if arg.isSet():
            return ValueInt(len(arg.value))
        if arg.isMap():
            return ValueInt(len(arg.value))
        if arg.isObject():
            return ValueInt(len(arg.value))
        raise CklRuntimeError("Cannot determine length of " + arg.type(), pos)


class FuncLess(ValueFunc):
    def __init__(self):
        super().__init__("less")
        self.info = "\r\n".join(
            [
                "less(obj)",
                "",
                "Returns TRUE if a is less than b.",
                "",
                ": less(1, 2) ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")
        return ValueBoolean.fromval(a < b)


class FuncLessEquals(ValueFunc):
    def __init__(self):
        super().__init__("less_equals")
        self.info = "\r\n".join(
            [
                "less_equals(a, b)",
                "",
                "Returns TRUE if a is less than or equals to b.",
                "",
                ": less_equals(1, 2) ==> TRUE",
                ": less_equals(2, 1) ==> FALSE",
                ": less_equals(1, 1) ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")
        return ValueBoolean.fromval(a <= b)


class FuncList(ValueFunc):
    def __init__(self):
        super().__init__("list")
        self.info = "\r\n".join(
            [
                "list(obj)",
                "",
                "Converts the obj to a list.",
                "",
                ": list(1) ==> [1]",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        if not args.hasArg("obj"):
            return ValueList()
        return args.getAsList("obj")


class FuncListDir(ValueFunc):
    def __init__(self):
        super().__init__("list_dir")
        self.info = "\r\n".join(
            [
                "list_dir(dir, recursive = FALSE, include_path = FALSE, "
                "include_dirs = FALSE)",
                "",
                "Enumerates the files and directories in the specified ",
                "directory and returns a list of filename or paths.",
            ]
        )
        self.secure = False

    def getArgNames(self):
        return ["dir", "recursive", "include_path", "include_dirs"]

    def execute(self, args, environment, pos):
        directory = args.getString("dir").value
        recursive = False
        if args.hasArg("recursive"):
            recursive = args.getBoolean("recursive").value
        include_path = recursive
        if args.hasArg("include_path"):
            include_path = args.getBoolean("include_path").value
        include_dirs = False
        if args.hasArg("include_dirs"):
            include_dirs = args.getBoolean("include_dirs").value
        result = ValueList()
        self.collectFiles(
            directory, recursive, include_path, include_dirs, result
        )
        return result

    def collectFiles(
        self, dirname, recursive, include_path, include_dirs, result
    ):
        for file in os.listdir(dirname):
            isdir = os.path.isdir(os.path.join(dirname, file))
            if include_dirs or not isdir:
                path = file
                if include_path:
                    path = self.path.join(dirname, path)
                result.addItem(ValueString(path))
            if recursive and isdir:
                self.collectFiles(
                    self.path.join(dirname, file),
                    recursive,
                    include_path,
                    include_dirs,
                    result,
                )


class FuncLog(ValueFunc):
    def __init__(self):
        super().__init__("log")
        self.info = "\r\n".join(
            [
                "log(x)",
                "",
                "Returns the natural logarithm of x.",
                "",
                ": int(log(E)) ==> 1",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.log(args.getNumerical("x").value))


class FuncLower(ValueFunc):
    def __init__(self):
        super().__init__("lower")
        self.info = "\r\n".join(
            [
                "lower(str)",
                "",
                "Converts str to lower case letters.",
                "",
                ": lower('Hello') ==> 'hello'",
            ]
        )

    def getArgNames(self):
        return ["str"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL
        return ValueString(args.getString("str").value.lower())


class FuncLs(ValueFunc):
    def __init__(self):
        super().__init__("ls")
        self.info = "\r\n".join(
            [
                "ls()",
                "ls(module)",
                "",
                "Returns a list of all defined symbols (functions and ",
                "constants) in the current environment or in the specified",
                "module.",
            ]
        )

    def getArgNames(self):
        return ["module"]

    def execute(self, args, environment, pos):
        result = ValueList()
        if args.hasArg("module"):
            moduleArg = args.get("module")
            if moduleArg.isString():
                module = environment.get(moduleArg.value, pos).value
            else:
                module = args.get("module").asObject().value
            for symbol in module:
                result.addItem(ValueString(symbol))
        else:
            for symbol in environment.getSymbols():
                result.addItem(ValueString(symbol))
        return result


class FuncMakeDir(ValueFunc):
    def __init__(self):
        super().__init__("make_dir")
        self.info = "\r\n".join(
            ["make_dir(dir, with_parents = FALSE)", "", "Creates a directory."]
        )
        self.secure = False

    def getArgNames(self):
        return ["dir", "with_parents"]

    def execute(self, args, environment, pos):
        dirname = args.getString("dir").value
        with_parents = False
        if args.hasArg("with_parents"):
            with_parents = args.getBoolean("with_parents").value
        try:
            if with_parents:
                os.makedirs(dirname)
            else:
                os.mkdir(dirname)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot create directory " + dirname, pos
            )
        return NULL


class FuncMap(ValueFunc):
    def __init__(self):
        super().__init__("map")
        self.info = "\r\n".join(
            [
                "map(obj)",
                "map()",
                "",
                "Converts the obj to a map, if possible. If obj is omitted,",
                "an empty map is returned.",
                "",
                ": map([[1, 2], [3, 4]]) ==> <<<1 => 2, 3 => 4>>>",
                ": map() ==> <<<>>>",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        if not args.hasArg("obj"):
            return ValueMap()
        return args.getAsMap("obj")


class FuncMatches(ValueFunc):
    def __init__(self):
        super().__init__("matches")
        self.info = "\r\n".join(
            [
                "matches(str, pattern)",
                "",
                "Returns TRUE, if str matches the regular expression pattern.",
                "",
                ": matches('abc12', //[a-c]+[1-9]+//) ==> TRUE",
                ": matches(NULL, //[a-c]+[1-9]+//) ==> FALSE",
            ]
        )

    def getArgNames(self):
        return ["str", "pattern"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return FALSE
        return ValueBoolean.fromval(
            args.getString("str").matches(args.getAsPattern("pattern"))
        )


class FuncMod(ValueFunc):
    def __init__(self):
        super().__init__("mod")
        self.info = "\r\n".join(
            [
                "mod(a, b)",
                "",
                "Returns the modulus of a modulo b.",
                "",
                ": mod(7, 2) ==> 1",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a.isNull() or b.isNull():
            return NULL

        if a.isInt() and b.isInt():
            return ValueInt(a.value % b.value)

        if a.isNumerical() and b.isNumerical():
            return ValueDecimal(a.asDecimal().value % b.asDecimal().value)

        raise CklRuntimeError(
            ValueString("ERROR"),
            "Cannot calculate modulus of " + a.type() + " by " + b.type(),
            pos,
        )


class FuncMul(ValueFunc):
    def __init__(self):
        super().__init__("mul")
        self.info = "\r\n".join(
            [
                "mul(a, b)",
                "",
                "Returns the product of a and b. For numerical values this",
                "uses the usual arithmetic.",
                "If a is a string and b is an int, then the string a is ",
                "repeated b times. If a is a list and b is an int, then ",
                "the list is repeated b times.",
                "",
                ": mul(2, 3) ==> 6",
                ": mul('2', 3) ==> '222'",
                ": mul([1, 2], 3) ==> [1, 2, 1, 2, 1, 2]",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a.isNull() or b.isNull():
            return NULL

        if a.isString() and b.isInt():
            return ValueString(a.value * b.value)

        if a.isList() and b.isInt():
            result = ValueList()
            for i in range(b.value):
                result.addItems(a.value)
            return result

        if a.isInt() and b.isInt():
            return ValueInt(a.value * b.value)

        if a.isNumerical() and b.isNumerical():
            return ValueDecimal(a.asDecimal().value * b.asDecimal().value)

        raise CklRuntimeError(
            ValueString("ERROR"),
            "Cannot multiply " + a.type() + " by " + b.type(),
            pos,
        )


class FuncNotEquals(ValueFunc):
    def __init__(self):
        super().__init__("not_equals")
        self.info = "\r\n".join(
            [
                "not_equals(a, b)",
                "",
                "Returns TRUE if a is not equals to b.",
                "",
                "Integer values are propagated to decimal values,",
                "if required.",
                "",
                ": not_equals(1, 2) ==> TRUE",
                ": not_equals(1, 1) ==> FALSE",
                ": not_equals(1, 1.0) ==> FALSE",
                ": not_equals('a', 'b') ==> TRUE",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")
        return ValueBoolean.fromval(a != b)


class FuncObject(ValueFunc):
    def __init__(self):
        super().__init__("object")
        self.info = "\r\n".join(
            [
                "object()",
                "object(obj)",
                "",
                "Creates an empty object value or converts a list of ",
                "pairs or a map to an object.",
                "",
                ": object() ==> <**>",
                ": object(<<<a => 1>>>) ==> <*a=1*>",
                ": object([['a', 1]]) ==> <*a=1*>",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        if not args.hasArg("obj"):
            return ValueObject()
        return args.getAsObject("obj")


class FuncOrd(ValueFunc):
    def __init__(self):
        super().__init__("ord")
        self.info = "\r\n".join(
            [
                "ord(ch)",
                "",
                "Returns the code point integer of the character ch.",
                "",
                ": ord('a') ==> 97",
                ": ord(' ') ==> 32",
            ]
        )

    def getArgNames(self):
        return ["ch"]

    def execute(self, args, environment, pos):
        if args.isNull("ch"):
            return NULL
        return ValueInt(ord(args.getString("ch").value[0]))


class FuncParse(ValueFunc):
    def __init__(self):
        super().__init__("parse")
        self.info = "\r\n".join(
            [
                "parse(s)",
                "",
                "Parses the string s.",
                "",
                ": parse('2+3') ==> '(add 2, 3)'",
            ]
        )

    def getArgNames(self):
        return ["s"]

    def execute(self, args, environment, pos):
        try:
            return ValueNode(
                parse_script(args.getString("s").value, pos.filename)
            )
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot parse expression " + args.getString("s"),
                pos,
            )


class FuncParseDate(ValueFunc):
    def __init__(self):
        super().__init__("parse_date")
        self.info = "\r\n".join(
            [
                "parse_date(str, fmt = 'yyyyMMdd')",
                "",
                "Parses the string str according to fmt and returns a ",
                "datetime value. If the format does not match or if the",
                "date is invalid, the NULL value is returned.",
                "",
                "It is possible to pass a list of formats to the fmt",
                "parameter. The function sequentially tries to convert ",
                "the str and if it works, returns the value.",
                "",
                ": parse_date('20170102') ==> '20170102000000'",
                ": parse_date('20170102', fmt = 'yyyyMMdd') ==> "
                "'20170102000000'",
                ": parse_date('2017010222', fmt = 'yyyyMMdd') ==> NULL",
                ": parse_date('20170102', fmt = 'yyyyMMddHH') ==> NULL",
                ": parse_date('20170102', fmt = ['yyyyMMdd']) ==> "
                "'20170102000000'",
                ": parse_date('201701022015', fmt = ['yyyyMMddHHmm', "
                "'yyyyMMddHH', 'yyyyMMdd']) ==> '20170102201500'",
                ": parse_date('20170112', fmt = ['yyyyMM', 'yyyy']) ==> NULL",
                ": parse_date('20170144') ==> NULL",
            ]
        )

    def getArgNames(self):
        return ["str", "fmt"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL
        x = args.getString("str")
        fmts = []
        if args.hasArg("fmt"):
            if args.get("fmt").isList():
                for fmt_ in args.get("fmt").value:
                    fmts.append(fmt_.asString().value)
            else:
                fmts.append(args.get("fmt").asString().value)
        else:
            fmts.append("yyyyMMdd")

        for fmt in fmts:
            s = x.value
            vals = dict()
            for part in ["yyyy", "yy", "MM", "dd", "HH", "mm", "ss"]:
                idx = fmt.find(part)
                if idx == -1:
                    continue
                vals[part] = int(s[idx:idx+len(part)])
                s = s[0:idx] + s[idx+len(part):]
                fmt = fmt[0:idx] + fmt[idx+len(part):]
                if s == "":
                    break
            if (
                fmt.find("y") == -1
                and fmt.find("M") == -1
                and fmt.find("d") == -1
                and fmt.find("H") == -1
                and fmt.find("m") == -1
                and fmt.find("s") == -1
                and s == ""
            ):
                date = datetime.datetime.fromtimestamp(0)
                date = date.replace(microsecond=0)
                try:
                    for part in vals:
                        if part == "yyyy":
                            date = date.replace(year=vals[part])
                        elif part == "yy":
                            date = date.replace(year=2000 + vals[part])
                        elif part == "MM":
                            date = date.replace(month=vals[part])
                        elif part == "dd":
                            date = date.replace(day=vals[part])
                        elif part == "HH":
                            date = date.replace(hour=vals[part])
                        elif part == "mm":
                            date = date.replace(minute=vals[part])
                        elif part == "ss":
                            date = date.replace(second=vals[part])
                    valid_date = True
                except Exception:
                    valid_date = False
                if valid_date:
                    return ValueDate(date)
        return NULL


class FuncParseJson(ValueFunc):
    def __init__(self):
        super().__init__("parse_json")
        self.info = "\r\n".join(
            [
                "parse_json(s)",
                "",
                "Parses the JSON string s and returns a map or list.",
                "",
                ": parse_json('{\"a\": 12, \"b\": [1, 2, 3, 4]}') ==> "
                "'<<<\\'a\\' => 12, \\'b\\' => [1, 2, 3, 4]>>>'",
                ": parse_json('[1, 2.5, 3, 4]') ==> '[1, 2.5, 3, 4]'",
            ]
        )

    def getArgNames(self):
        return ["s"]

    def objAsMap(self, obj):
        result = ValueMap()
        for key, value in obj.items():
            result.addItem(self.convertObj(key), self.convertObj(value))
        return result

    def arrayAsList(self, arr):
        result = ValueList()
        for item in arr:
            result.addItem(self.convertObj(item))
        return result

    def convertObj(self, obj):
        if type(obj) == str:
            return ValueString(obj)
        if type(obj) == int:
            return ValueInt(obj)
        if type(obj) == float:
            return ValueDecimal(obj)
        if type(obj) == bool:
            return ValueBoolean.fromval(obj)
        if type(obj) == list:
            return self.arrayAsList(obj)
        return self.objAsMap(obj)

    def execute(self, args, environment, pos):
        try:
            j = json.loads(args.getString("s").value)
            return self.convertObj(j)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot parse string as JSON", pos
            )


class FuncPattern(ValueFunc):
    def __init__(self):
        super().__init__("pattern")
        self.info = "\r\n".join(
            [
                "pattern(obj)",
                "",
                "Converts the obj to a regexp pattern, if possible.",
                "",
                ": pattern('xy[1-9]{3}') ==> //xy[1-9]{3}//",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return args.getAsPattern("obj")


class FuncPow(ValueFunc):
    def __init__(self):
        super().__init__("pow")
        self.info = "\r\n".join(
            [
                "pow(x, y)",
                "",
                "Returns the power x ^ y.",
                "",
                ": pow(2, 3) ==> 8",
                ": pow(2.5, 2) ==> 6.25",
                ": pow(4, 2) ==> 16",
                ": pow(4.0, 2.0) ==> 16.0",
                ": round(pow(2, 1.5), digits = 3) ==> 2.828",
            ]
        )

    def getArgNames(self):
        return ["x", "y"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        if args.isNull("y"):
            return NULL
        if args.get("y").isInt() and args.get("x").isInt():
            x = args.getInt("x").value
            y = args.getInt("y").value
            return ValueInt(int(math.pow(x, y)))
        else:
            x = args.getDecimal("x").value
            y = args.getDecimal("y").value
            return ValueDecimal(math.pow(x, y))


class FuncPrint(ValueFunc):
    def __init__(self):
        super().__init__("print")
        self.info = "\r\n".join(
            [
                "print(obj, out = stdout)",
                "",
                "Prints the obj to the output out. Default output is ",
                "stdout which may be connected to the console (e.g. in",
                "case of REPL) or a file or be silently ignored.",
                "",
                ": print('hello') ==> NULL",
            ]
        )

    def getArgNames(self):
        return ["obj", "out"]

    def execute(self, args, environment, pos):
        obj = args.getAsString("obj")
        output = args.getOutput("out", environment.get("stdout", pos))
        try:
            output.write(obj.value)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot write to output", pos
            )
        return NULL


class FuncPrintln(ValueFunc):
    def __init__(self):
        super().__init__("println")
        self.info = "\r\n".join(
            [
                "println(obj = '', out = stdout)",
                "",
                "Prints the obj to the output out and terminates the ",
                "line. Default output is stdout which may be connected",
                "to the console (e.g. in case of REPL) or a file or be",
                "silently ignored.",
                "",
                ": println('hello') ==> NULL",
            ]
        )

    def getArgNames(self):
        return ["obj", "out"]

    def execute(self, args, environment, pos):
        if args.hasArg("obj"):
            obj = args.getAsString("obj")
        else:
            obj = ValueString("")
        output = args.getOutput("out", environment.get("stdout", pos))
        try:
            output.writeLine(obj.value)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot write to output", pos
            )
        return NULL


class FuncProcessLines(ValueFunc):
    def __init__(self):
        super().__init__("process_lines")
        self.info = "\r\n".join(
            [
                "process_lines(input, callback)",
                "",
                "Reads lines from the input and calls the callback function",
                "once for each line. The line string is the single argument",
                "of the callback function.",
                "",
                "If input is a list, then each list element is converted to",
                "a string and processed as a line",
                "",
                "The function returns the number of processed lines." + "",
                ": def result = []; str_input('one\\ntwo\\nthree') !> "
                "process_lines(fn(line) result !> append(line)); "
                "result ==> ['one', 'two', 'three']",
                ": str_input('one\\ntwo\\nthree') !> "
                "process_lines(fn(line) line) ==> 3",
                ": def result = ''; process_lines(['a', 'b', 'c'], "
                "fn(line) result += line); result ==> 'abc'",
            ]
        )

    def getArgNames(self):
        return ["input", "callback"]

    def execute(self, args, environment, pos):
        inparg = args.get("input")
        callback = args.get("callback").asFunc()
        env = environment.newEnv()
        if inparg.isInput():
            inp = inparg.asInput()

            def cb(line):
                args = Args(pos).addArg(callback.getArgNames()[0], line)
                return callback.execute(args, env, pos)

            return ValueInt(inp.process(cb))
        elif inparg.isList():
            lst = inparg.asList().value
            for element in lst:
                args = Args(pos).addArg(
                    callback.getArgNames()[0], element.asString()
                )
                callback.execute(args, env, pos)
            return ValueInt(len(lst))
        else:
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot process lines from " + inparg.toString(),
                pos,
            )


class FuncPut(ValueFunc):
    def __init__(self):
        super().__init__("put")
        self.info = "\r\n".join(
            [
                "put(m, key, value)",
                "",
                "Puts the value into the map m at the given key.",
                "",
                ": def m = map([[1, 2], [3, 4]]); put(m, 1, 9) ==> "
                "<<<1 => 9, 3 => 4>>>",
            ]
        )

    def getArgNames(self):
        return ["m", "key", "value"]

    def execute(self, args, environment, pos):
        m = args.getMap("m")
        m.addItem(args.get("key"), args.get("value"))
        return m


seed = random.random()


class FuncRandom(ValueFunc):
    def __init__(self):
        super().__init__("random")
        self.info = "\r\n".join(
            [
                "random()",
                "random(a)",
                "random(a, b)",
                "",
                "Returns a random number. If no argument is provided, a",
                "decimal value in the range [0, 1) is returned. If only",
                "a is provided, then an int value in the range [0, a)",
                "is returned. If both a and b are provided, then an int",
                "value in the range [a, b) is returned.",
                "",
                ": set_seed(1); random(5) ==> 1",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        if args.hasArg("a") and not args.hasArg("b"):
            return ValueInt(self.getRandomInt(0, args.getInt("a").value))

        if args.hasArg("a") and args.hasArg("b"):
            return ValueInt(
                self.getRandomInt(
                    args.getInt("a").value, args.getInt("b").value
                )
            )

        return ValueDecimal(self.getRandomDouble())

    def getRandomInt(self, minv, maxv):
        minv = math.ceil(minv)
        maxv = math.floor(maxv)
        return math.floor(self.seededRandom() * (maxv - minv)) + minv

    def getRandomDouble(self):
        return self.seededRandom()

    def seededRandom(self):
        # TODO instead use the standard random.Random instance!
        global seed
        seed = (seed * 9301 + 49297) % 233280
        return seed / 233280


class FuncRange(ValueFunc):
    def __init__(self):
        super().__init__("range")
        self.info = "\r\n".join(
            [
                "range(a)",
                "range(a, b)",
                "range(a, b, step)",
                "",
                "Returns a list containing int values in the range. If",
                "only a is provided, the range is [0, a). If both a and",
                "b are provided, the range is [a, b). If step is given,",
                "then only every step element is included in the list.",
                "",
                ": range(4) ==> [0, 1, 2, 3]",
                ": range(3, 6) ==> [3, 4, 5]",
                ": range(10, step = 3) ==> [0, 3, 6, 9]",
                ": range(10, 0, step = -2) ==> [10, 8, 6, 4, 2]",
            ]
        )

    def getArgNames(self):
        return ["a", "b", "step"]

    def execute(self, args, environment, pos):
        start = 0
        end = 0
        step = 1
        if args.hasArg("a") and not args.hasArg("b"):
            end = args.getInt("a").value
        elif args.hasArg("a") and args.hasArg("b"):
            start = args.getInt("a").value
            end = args.getInt("b").value
        if args.hasArg("step"):
            step = args.getInt("step").value

        result = ValueList()
        i = start
        if step > 0:
            while i < end:
                result.addItem(ValueInt(i))
                i += step
        elif step < 0:
            while i > end:
                result.addItem(ValueInt(i))
                i += step
        return result


class FuncRead(ValueFunc):
    def __init__(self):
        super().__init__("read")
        self.info = "\r\n".join(
            [
                "read(input = stdin)",
                "",
                "Read a character from the input. If end of input is ",
                "reached, an empty string is returned.",
                "",
                ": def s = str_input('hello'); read(s) ==> 'h'",
            ]
        )

    def getArgNames(self):
        return ["input"]

    def execute(self, args, environment, pos):
        inp = args.getInput("input", environment.get("stdin", pos))
        try:
            s = inp.read()
            if s is None:
                return NULL
            return ValueString(s)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot read from input", pos
            )


class FuncReadall(ValueFunc):
    def __init__(self):
        super().__init__("read_all")
        self.info = "\r\n".join(
            [
                "read_all(input = stdin)",
                "",
                "Read the whole input. If end of input is reached,",
                "NULL is returned.",
                "",
                ": def s = str_input('hello'); read_all(s) ==> 'hello'",
            ]
        )

    def getArgNames(self):
        return ["input"]

    def execute(self, args, environment, pos):
        inp = args.getInput("input", environment.get("stdin", pos))
        try:
            s = inp.readAll()
            if s is None:
                return NULL
            return ValueString(s)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot read from input", pos
            )


class FuncReadln(ValueFunc):
    def __init__(self):
        super().__init__("readln")
        self.info = "\r\n".join(
            [
                "readln(input = stdin)",
                "",
                "Read one line from the input. If end of input is reached,",
                "NULL is returned.",
                "",
                ": def s = str_input('hello'); readln(s) ==> 'hello'",
            ]
        )

    def getArgNames(self):
        return ["input"]

    def execute(self, args, environment, pos):
        inp = args.getInput("input", environment.get("stdin", pos))
        try:
            line = inp.readLine()
            if line is None:
                return NULL
            return ValueString(line)
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "Cannot read from input", pos
            )


class FuncRemove(ValueFunc):
    def __init__(self):
        super().__init__("remove")
        self.info = "\r\n".join(
            [
                "remove(lst, element)",
                "",
                "Removes the element from the list lst. The lst may also",
                "be a set or a map.",
                "Returns the changed list, but the list is changed in place.",
                "",
                ": remove([1, 2, 3, 4], 3) ==> [1, 2, 4]",
                ": remove(<<1, 2, 3, 4>>, 3) ==> <<1, 2, 4>>",
                ": remove(<<<a => 1, b => 2, c => 3, d => 4>>>, 'c') ==> "
                "<<<'a' => 1, 'b' => 2, 'd' => 4>>>",
                ": remove(<*a=1, b=2*>, 'b') ==> <*a=1*>",
            ]
        )

    def getArgNames(self):
        return ["lst", "element"]

    def execute(self, args, environment, pos):
        lst = args.get("lst")
        element = args.get("element")

        if lst.isList() or lst.isSet() or lst.isMap():
            lst.removeItem(element)
            return lst
        elif lst.isObject():
            del lst.value[element.value]
            return lst

        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot remove from " + lst.type(), pos
        )


class FuncRound(ValueFunc):
    def __init__(self):
        super().__init__("round")
        self.info = "\r\n".join(
            [
                "round(x, digits = 0)",
                "",
                "Returns the decimal value x rounded to the specified ",
                "number of digits. Default for digits is 0.",
                "",
                ": round(1.345, digits = 1) ==> 1.3",
            ]
        )

    def getArgNames(self):
        return ["x", "digits"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        x = args.getNumerical("x")
        digits = 0
        if args.hasArg("digits"):
            digits = args.getInt("digits").value
        return ValueDecimal(round(x.asDecimal().value, digits))


class FuncRun(ValueFunc):
    def __init__(self, interpreter):
        super().__init__("run")
        self.interpreter = interpreter
        self.info = "\r\n".join(
            ["run(file)", "", "Loads and interprets the file."]
        )
        self.secure = False

    def getArgNames(self):
        return ["file"]

    def execute(self, args, environment, pos):
        file = args.getString("file").value
        path = file
        if not path.startswith("/") and not path.startswith("."):
            path = os.getcwd() + "/" + path
        script = ""
        try:
            with open(path, encoding="utf-8") as infile:
                script = infile.read()
        except Exception:
            raise CklRuntimeError(
                ValueString("ERROR"), "File " + path + " not found", pos
            )
        return self.interpreter.interpret(script, file)


class FuncS(ValueFunc):
    def __init__(self):
        super().__init__("s")
        self.info = "\r\n".join(
            [
                "s(str, start = 0)",
                "",
                "Returns a string, where all placeholders are replaced with",
                "their appropriate values. Placeholder have the form '{var}'",
                "and result in the value of the variable var inserted at ",
                "self location.",
                "",
                "The placeholder can also be expressions and their result ",
                "will be inserted instead of the placeholder.",
                "",
                "There are formatting suffixes to the placeholder, which ",
                "allow some control over the formatting. They formatting ",
                "spec starts after a # character and consists of align/fill,",
                "width and precision fields. For example #06.2 will format",
                "the decimal to a width of six characters and uses two",
                "digits after the decimal point. If the number is less",
                "than six characters wide, then it is prefixed with zeroes",
                "until the width is reached, e.g. '001.23'. Please refer",
                "to the examples below.",
                "",
                ": def name = 'damian'; s('hello {name}') ==> 'hello damian'",
                ": def foo = '{bar}'; def bar = 'baz'; s('{foo}{bar}') ==>"
                " '{bar}baz'",
                ": def a = 'abc'; s('\"{a#-8}\"') ==> '\"abc     \"'",
                ": def a = 'abc'; s('\"{a#8}\"') ==> '\"     abc\"'",
                ": def a = 'abc'; s('a = {a#5}') ==> 'a =   abc'",
                ": def a = 'abc'; s('a = {a#-5}') ==> 'a = abc  '",
                ": def n = 12; s('n = {n#5}') ==> 'n =    12'",
                ": def n = 12; s('n = {n#-5}') ==> 'n = 12   '",
                ": def n = 12; s('n = {n#05}') ==> 'n = 00012'",
                ": def n = 1.2345678; s('n = {n#.2}') ==> 'n = 1.23'",
                ": def n = 1.2345678; s('n = {n#06.2}') ==> 'n = 001.23'",
                ": s('2x3 = {2*3}') ==> '2x3 = 6'",
                ": def n = 123; s('n = {n#x}') ==> 'n = 7b'",
                ": def n = 255; s('n = {n#04x}') ==> 'n = 00ff'",
                ": require Math; s('{Math->PI} is cool') ==> "
                "'3.141592653589793 is cool'",
            ]
        )

    def getArgNames(self):
        return ["str", "start"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL
        s = args.getString("str").value
        start = args.getInt("start", 0).value
        if start < 0:
            start = len(s) + start
        while True:
            idx1 = s.find("{", start)
            if idx1 == -1:
                return ValueString(s)
            idx2 = s.find("}", idx1 + 1)
            if idx2 == -1:
                return ValueString(s)
            variable = s[idx1+1:idx2]
            width = 0
            zeroes = False
            leading = True
            digits = -1
            base = 10
            idx3 = variable.find("#")
            if idx3 != -1:
                spec = variable[idx3+1:]
                variable = variable[0:idx3]
                if spec.startswith("-"):
                    leading = False
                    spec = spec[1:]
                if spec.startswith("0"):
                    zeroes = True
                    leading = False
                    spec = spec[1:]
                if spec.endswith("x"):
                    base = 16
                    spec = spec[0:-1]
                idx4 = spec.find(".")
                if idx4 == -1:
                    digits = -1
                    width = int(spec)
                else:
                    digits = int(spec[idx4+1:])
                    width = int(spec[0:idx4])
            node = parse_script(variable, pos.filename)
            value = node.evaluate(environment).asString().value
            if base != 10:
                value = f"{int(value):x}"
            elif digits != -1:
                value = str(round(float(value), digits))
            while len(value) < width:
                if leading:
                    value = " " + value
                elif zeroes:
                    value = "0" + value
                else:
                    value = value + " "
            s = s[0:idx1] + value + s[idx2+1:]
            start = idx1 + len(value)


class FuncSet(ValueFunc):
    def __init__(self):
        super().__init__("set")
        self.info = "\r\n".join(
            [
                "set(obj)",
                "",
                "Converts the obj to a set, if possible.",
                "",
                ": set([1, 2, 3]) ==> <<1, 2, 3>>",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        if not args.hasArg("obj"):
            return ValueSet()
        return args.getAsSet("obj")


class FuncSetSeed(ValueFunc):
    def __init__(self):
        super().__init__("set_seed")
        self.info = "\r\n".join(
            [
                "set_seed(n)",
                "",
                "Sets the seed of the random number generator to n.",
                "",
                ": set_seed(1) ==> 1",
            ]
        )

    def getArgNames(self):
        return ["n"]

    def execute(self, args, environment, pos):
        global seed
        seed = args.getInt("n").value
        return ValueInt(seed)


class FuncSin(ValueFunc):
    def __init__(self):
        super().__init__("sin")
        self.info = "\r\n".join(
            ["sin(x)", "", "Returns the sinus of x.", "", ": sin(0) ==> 0.0"]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.sin(args.getNumerical("x").value))


class FuncSorted(ValueFunc):
    def __init__(self):
        super().__init__("sorted")
        self.info = "\r\n".join(
            [
                "sorted(lst, cmp=compare, key=identity)",
                "",
                "Returns a sorted copy of the list. This is sorted ",
                "according to the value returned by the key function ",
                "for each element of the list.",
                "The values are compared using the compare function cmp.",
                "",
                ": sorted([3, 2, 1]) ==> [1, 2, 3]",
                ": sorted([6, 2, 5, 3, 1, 4]) ==> [1, 2, 3, 4, 5, 6]",
            ]
        )

    def getArgNames(self):
        return ["lst", "cmp", "key"]

    def execute(self, args, environment, pos):
        env = environment.newEnv()
        lst = args.getAsList("lst")
        cmp = (
            args.getFunc("cmp")
            if args.hasArg("cmp")
            else environment.get("compare", pos)
        )
        key = (
            args.getFunc("key")
            if args.hasArg("key")
            else environment.get("identity", pos)
        )
        result = lst.value[:]
        for i in range(len(result)):
            v = key.execute(
                Args(pos).addArg(key.getArgNames()[0], result[i]), env, pos
            )
            for j in range(i - 1, -1, -1):
                v2 = key.execute(
                    Args(pos).addArg(key.getArgNames()[0], result[j]), env, pos
                )
                cmpargs = (
                    Args(pos)
                    .addArg(cmp.getArgNames()[0], v)
                    .addArg(cmp.getArgNames()[1], v2)
                )
                comparison = cmp.execute(cmpargs, env, pos).value
                if comparison < 0:
                    temp = result[j + 1]
                    result[j + 1] = result[j]
                    result[j] = temp
                else:
                    break
        return ValueList().addItems(result)


class FuncSplit(ValueFunc):
    def __init__(self):
        super().__init__("split")
        self.info = "\r\n".join(
            [
                "split(str, delim = '[ \\t]+')",
                "",
                "Splits the string str into parts and returns a list",
                "of strings. The delim is a regular expression. Default",
                "is spaces or tabs.",
                "",
                ": split('a,b,c', //,//) ==> ['a', 'b', 'c']",
            ]
        )

    def getArgNames(self):
        return ["str", "delim"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL

        value = args.getString("str").value
        delim = args.getAsPattern("delim", ValuePattern("[ \\t]+")).pattern

        return splitValue(value, delim)


def splitValue(value, delim):
    if value == "":
        return ValueList()
    result = ValueList()
    parts = re.split(delim, value)
    for part in parts:
        result.addItem(ValueString(part))
    return result


class FuncSplit2(ValueFunc):
    def __init__(self):
        super().__init__("split2")
        self.info = "\r\n".join(
            [
                "split2(str, sep1, sep2)",
                "",
                "Performs a two-stage split of the string data.",
                "This results in a list of list of strings.",
                "",
                ": split2('a:b:c|d:e:f', escape_pattern('|'), "
                "escape_pattern(':')) ==> [['a', 'b', 'c'], ['d', 'e', 'f']]",
                ": split2('', '\\|', ':') ==> []",
            ]
        )

    def getArgNames(self):
        return ["str", "sep1", "sep2"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL

        value = args.getString("str").value
        sep1 = args.getAsPattern("sep1").pattern
        sep2 = args.getAsPattern("sep2").pattern
        result = splitValue(value, sep1)
        lst = result.value
        for i in range(len(lst)):
            lst[i] = splitValue(lst[i].value, sep2)
        return result


class FuncSqrt(ValueFunc):
    def __init__(self):
        super().__init__("sqrt")
        self.info = "\r\n".join(
            [
                "sqrt(x)",
                "",
                "Returns the square root of num as a decimal value.",
                "",
                ": sqrt(4) ==> 2.0",
            ]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.sqrt(args.getNumerical("x").value))


class FuncStartsWith(ValueFunc):
    def __init__(self):
        super().__init__("starts_with")
        self.info = "\r\n".join(
            [
                "starts_with(str, part)",
                "",
                "Returns TRUE if the string str starts with part.",
                "",
                ": starts_with('abcdef', 'abc') ==> TRUE",
                ": starts_with(NULL, 'abc') ==> FALSE",
            ]
        )

    def getArgNames(self):
        return ["str", "part"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return FALSE
        return ValueBoolean.fromval(
            args.getString("str").value.startswith(
                args.getString("part").value
            )
        )


class FuncString(ValueFunc):
    def __init__(self):
        super().__init__("string")
        self.info = "\r\n".join(
            [
                "string(obj)",
                "",
                "Converts the obj to a string, if possible.",
                "",
                ": string(123) ==> '123'",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return args.getAsString("obj")


class FuncStrInput(ValueFunc):
    def __init__(self):
        super().__init__("str_input")
        self.info = "\r\n".join(
            [
                "str_input(str)",
                "",
                "Returns an input object, that reads the characters ",
                "of the given string str.",
                "",
                ": str_input('abc') ==> <!input-stream>",
            ]
        )

    def getArgNames(self):
        return ["str"]

    def execute(self, args, environment, pos):
        return ValueInput(StringInput(args.getString("str").value))


class FuncStrOutput(ValueFunc):
    def __init__(self):
        super().__init__("str_output")
        self.info = "\r\n".join(
            [
                "str_output()",
                "",
                "Returns an output object. Things written to self ",
                "output object can be retrieved using the function",
                "get_output_string.",
                "",
                ": do def o = str_output(); print('abc', out = o); "
                "get_output_string(o); end ==> 'abc'",
            ]
        )

    def getArgNames(self):
        return []

    def execute(self, args, environment, pos):
        return ValueOutput(StringOutput())


class FuncSub(ValueFunc):
    def __init__(self):
        super().__init__("sub")
        self.info = "\r\n".join(
            [
                "sub(a, b)",
                "",
                "Returns the subtraction of b from a. For numerical values",
                "this uses usual arithmetic. For lists and sets, this ",
                "returns lists and sets minus the element b. If a is a ",
                "datetime value and b is datetime value, then the date ",
                "difference is returned. If a is a datetime value and b ",
                "is a numeric value, then b is interpreted as number ",
                "of days and the corresponding datetime after subtracting",
                "these number of days is returned.",
                "",
                ": sub(1, 2) ==> -1",
                ": sub([1, 2, 3], 2) ==> [1, 3]",
                ": sub(date('20170405'), date('20170402')) ==> 3",
                ": sub(date('20170405'), 3) ==> '20170402000000'",
                ": sub(<<3, 1, 2>>, 2) ==> <<1, 3>>",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a.isList():
            result = ValueList()
            for item in a.value:
                add = True
                for val in args.getAsList("b").value:
                    if item != val:
                        continue
                    add = False
                    break
                if add:
                    result.addItem(item)
            return result

        if a.isSet():
            minus = ValueSet()
            if b.isSet():
                minus = b.asSet()
            elif b.isList():
                for element in b.asList().value:
                    minus.addItem(element)
            else:
                minus.addItem(b)
            result = ValueSet()
            for element in a.asSet().value:
                if not minus.hasItem(element):
                    result.addItem(element)
            return result

        if a.isDate():
            if b.isDate():
                diff = to_oa_date(a.asInt()) - to_oa_date(b.asInt())
                return ValueInt(diff)
            return ValueDate(
                to_date(to_oa_date(a.value) - args.getAsDecimal("b").value)
            )

        if a.isNull() or b.isNull():
            return NULL

        if a.isInt() and b.isInt():
            return ValueInt(a.value - b.value)

        if a.isNumerical() and b.isNumerical():
            return ValueDecimal(a.asDecimal().value - b.asDecimal().value)

        raise CklRuntimeError(
            ValueString("ERROR"),
            "Cannot subtract " + b.type() + " from " + a.type(),
            pos,
        )


class FuncSublist(ValueFunc):
    def __init__(self):
        super().__init__("sublist")
        self.info = "\r\n".join(
            [
                "sublist(lst, startidx)",
                "sublist(lst, startidx, endidx)",
                "",
                "Returns the sublist starting with startidx. If endidx ",
                "is provided, self marks the end of the sublist. Endidx ",
                "is not included.",
                "",
                ": sublist([1, 2, 3, 4], 2) ==> [3, 4]",
            ]
        )

    def getArgNames(self):
        return ["lst", "startidx", "endidx"]

    def execute(self, args, environment, pos):
        if args.isNull("lst"):
            return NULL
        value = args.getList("lst").value
        start = args.getInt("startidx").value
        if start < 0:
            start = len(value) + start
        if start > len(value):
            return ValueList()
        end = args.getInt("endidx", len(value)).value
        if end < 0:
            end = len(value) + end
        if end > len(value):
            end = len(value)
        result = ValueList()
        for i in range(start, end):
            result.addItem(value[i])
        return result


class FuncSubstr(ValueFunc):
    def __init__(self):
        super().__init__("substr")
        self.info = "\r\n".join(
            [
                "substr(str, startidx)",
                "substr(str, startidx, endidx)",
                "",
                "Returns the substring starting with startidx. If endidx",
                "is provided, self marks the end of the substring. Endidx ",
                "is not included.",
                "",
                ": substr('abcd', 2) ==> 'cd'",
            ]
        )

    def getArgNames(self):
        return ["str", "startidx", "endidx"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL
        value = args.getString("str").value
        start = args.getInt("startidx").value
        if start < 0:
            start = len(value) + start
        if start > len(value):
            return ValueString("")
        end = args.getInt("endidx", len(value)).value
        if end < 0:
            end = len(value) + end
        if end > len(value):
            end = len(value)
        return ValueString(value[start:end])


class FuncSum(ValueFunc):
    def __init__(self):
        super().__init__("sum")
        self.info = "\r\n".join(
            [
                "sum(list, ignore = [])",
                "",
                "Returns the sum of a list of numbers. Values contained ",
                "in the optional list ignore are counted as 0.",
                "",
                ": sum([1, 2, 3]) ==> 6",
                ": sum([1, 2.5, 3]) ==> 6.5",
                ": sum([1, 2.5, 1.5, 3]) ==> 8.0",
                ": sum([1.0, 2.0, 3.0]) ==> 6.0",
                ": sum([1.0, 2, -3.0]) ==> 0.0",
                ": sum([1, 2, -3]) ==> 0",
                ": sum([1, '1', 1], ignore = ['1']) ==> 2",
                ": sum(range(101)) ==> 5050",
                ": sum([]) ==> 0",
                ": sum([NULL], ignore = [NULL]) ==> 0",
                ": sum([1, NULL, 3], ignore = [NULL]) ==> 4",
                ": sum([1, NULL, '', 3], ignore = [NULL, '']) ==> 4",
            ]
        )

    def getArgNames(self):
        return ["list", "ignore"]

    def execute(self, args, environment, pos):
        if args.isNull("list"):
            return NULL

        lst = args.getList("list").value

        ignore = []
        if args.hasArg("ignore"):
            ignore = args.getList("ignore").value

        result = 0
        decimalrequired = False

        for value in lst:
            skipvalue = False
            for ignoreval in ignore:
                if ignoreval == value:
                    skipvalue = True
                    break
            if skipvalue:
                continue

            if value.isInt():
                result += value.value
            elif value.isDecimal():
                result += value.value
                decimalrequired = True
            else:
                raise CklRuntimeError(
                    ValueString("ERROR"), "Cannot sum " + value.type(), pos
                )

        if decimalrequired:
            return ValueDecimal(result)
        return ValueInt(result)


class FuncTan(ValueFunc):
    def __init__(self):
        super().__init__("tan")
        self.info = "\r\n".join(
            ["tan(x)", "", "Returns the tangens of x.", "", ": tan(0) ==> 0"]
        )

    def getArgNames(self):
        return ["x"]

    def execute(self, args, environment, pos):
        if args.isNull("x"):
            return NULL
        return ValueDecimal(math.tan(args.getNumerical("x").value))


class FuncTimestamp(ValueFunc):
    def __init__(self):
        super().__init__("timestamp")
        self.info = "\r\n".join(
            ["timestamp(x)", "", "Returns current system timestamp."]
        )

    def getArgNames(self):
        return []

    def execute(self, args, environment, pos):
        return ValueInt(datetime.datetime.now().timestamp())


class FuncTrim(ValueFunc):
    def __init__(self):
        super().__init__("trim")
        self.info = "\r\n".join(
            [
                "trim(str)",
                "",
                "Trims any leading or trailing whitespace from ",
                "the string str.",
                "",
                ": trim(' a  ') ==> 'a'",
            ]
        )

    def getArgNames(self):
        return ["str"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL
        return ValueString(args.getString("str").value.strip())


class FuncType(ValueFunc):
    def __init__(self):
        super().__init__("type")
        self.info = "\r\n".join(
            [
                "type(obj)",
                "",
                "Returns the name of the type of obj as a string.",
                "",
                ": type('Hello') ==> 'string'",
            ]
        )

    def getArgNames(self):
        return ["obj"]

    def execute(self, args, environment, pos):
        return ValueString(args.get("obj").type())


class FuncUpper(ValueFunc):
    def __init__(self):
        super().__init__("upper")
        self.info = "\r\n".join(
            [
                "upper(str)",
                "",
                "Converts str to upper case letters.",
                "",
                ": upper('Hello') ==> 'HELLO'",
            ]
        )

    def getArgNames(self):
        return ["str"]

    def execute(self, args, environment, pos):
        if args.isNull("str"):
            return NULL
        return ValueString(args.getString("str").value.upper())


class FuncZip(ValueFunc):
    def __init__(self):
        super().__init__("zip")
        self.info = "\r\n".join(
            [
                "zip(a, b)",
                "",
                "Returns a list where each element is a list of two items.",
                "The first of the two items is taken from the first list,",
                "the second from the second list. The resulting list has",
                "the same length as the shorter of the two input lists.",
                "",
                ": zip([1, 2, 3], [4, 5, 6, 7]) ==> [[1, 4], [2, 5], [3, 6]]",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a.isNull() or b.isNull():
            return NULL

        if a.isList() and b.isList():
            lista = a.value
            listb = b.value
            result = ValueList()
            for i in range(min(len(lista), len(listb))):
                pair = ValueList()
                pair.addItem(lista[i])
                pair.addItem(listb[i])
                result.addItem(pair)
            return result

        raise CklRuntimeError(
            ValueString("ERROR"),
            "Cannot zip " + a.type() + " and " + b.type(),
            pos,
        )


class FuncZipMap(ValueFunc):
    def __init__(self):
        super().__init__("zip_map")
        self.info = "\r\n".join(
            [
                "zip_map(a, b)",
                "",
                "Returns a map where the key of each entry is taken from a,",
                "and where the value of each entry is taken from b, where",
                "a and b are lists of identical length.",
                "",
                ": zip_map(['a', 'b', 'c'], [1, 2, 3]) ==> "
                "<<<'a' => 1, 'b' => 2, 'c' => 3>>>",
            ]
        )

    def getArgNames(self):
        return ["a", "b"]

    def execute(self, args, environment, pos):
        a = args.get("a")
        b = args.get("b")

        if a.isNull() or b.isNull():
            return NULL

        if a.isList() and b.isList():
            lista = a.value
            listb = b.value
            result = ValueMap()
            for i in range(min(len(lista), len(listb))):
                result.addItem(lista[i], listb[i])
            return result

        raise CklRuntimeError(
            ValueString("ERROR"),
            "Cannot zip_map " + a.type() + " and " + b.type(),
            pos,
        )
