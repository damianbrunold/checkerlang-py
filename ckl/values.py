import datetime
import functools
import math
import re

from ckl.errors import CklRuntimeError


class Args:
    def __init__(self, pos):
        self.argNames = []
        self.args = dict()
        self.restArgName = None
        self.pos = pos

    def addArg(self, name, value):
        self.argNames.append(name)
        self.args[name] = value
        return self

    def addArgs(self, names):
        for name in names:
            if not name.endswith("..."):
                self.argNames.append(name)
            else:
                self.restArgName = name
        return self

    def __repr__(self):
        return ", ".join(
            [name + "=" + value for name, value in self.args.items()]
        )

    def toStringAbbrev(self):
        result = []
        for name, value in self.args.items:
            value = str(value)
            if len(value) > 50:
                value = value[0:50] + "... " + value[len(value) - 5:]
            result.append(name + "=" + value)
        return ", ".join(result)

    def setArgs(self, names, values):
        rest = ValueList()
        for i in range(len(values)):
            if names[i]:
                if names[i] not in self.argNames:
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        "Argument " + names[i] + " is unknown",
                        self.pos,
                    )
                self.args[names[i]] = values[i]

        inKeywords = False
        for i in range(len(values)):
            if not names[i]:
                if inKeywords:
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        "Positional arguments need to be placed "
                        "before named arguments",
                        self.pos,
                    )
                argName = self.getNextPositionalArgName()
                if not argName:
                    if not self.restArgName:
                        raise CklRuntimeError(
                            ValueString("ERROR"),
                            "Too many arguments",
                            self.pos,
                        )
                    rest.addItem(values[i])
                elif argName not in self.args:
                    self.args[argName] = values[i]
                else:
                    rest.addItem(values[i])
            else:
                inKeywords = True
                if names[i] not in self.argNames:
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        "Argument " + names[i] + " is unknown",
                        self.pos,
                    )
                self.args[names[i]] = values[i]
        if self.restArgName:
            self.args[self.restArgName] = rest

    def getNextPositionalArgName(self):
        for argname in self.argNames:
            if argname not in self.args:
                return argname

    def hasArg(self, name):
        return name in self.args

    def get(self, name):
        if not self.hasArg(name):
            raise CklRuntimeError(
                ValueString("ERROR"), "Missing argument " + name, self.pos
            )
        return self.args[name]

    def isNull(self, name):
        if not self.hasArg(name):
            return False
        return self.get(name).isNull()

    def getString(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return ValueString(defaultValue)
        value = self.get(name)
        if not value.isString():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "String required but got " + value.type(),
                self.pos,
            )
        return value

    def getBoolean(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return ValueBoolean.fromval(defaultValue)
        value = self.get(name)
        if not value.isBoolean():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Boolean required but got " + value.type(),
                self.pos,
            )
        return value

    def getInt(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return ValueInt(defaultValue)
        value = self.get(name)
        if not value.isInt():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Int required but got " + value.type(),
                self.pos,
            )
        return value

    def getDecimal(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return ValueDecimal(defaultValue)
        value = self.get(name)
        if not value.isDecimal():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Decimal required but got " + value.type(),
                self.pos,
            )
        return value

    def getNumerical(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return ValueDecimal(defaultValue)
        value = self.get(name)
        if not value.isNumerical():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Numerical required but got " + value.type(),
                self.pos,
            )
        return value

    def getList(self, name):
        value = self.get(name)
        if not value.isList():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "List required but got " + value.type(),
                self.pos,
            )
        return value

    def getMap(self, name):
        value = self.get(name)
        if not value.isMap():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Map required but got " + value.type(),
                self.pos,
            )
        return value

    def getInput(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return defaultValue
        value = self.get(name)
        if not value.isInput():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Input required but got " + value.type(),
                self.pos,
            )
        return value

    def getOutput(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return defaultValue
        value = self.get(name)
        if not value.isOutput():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Output required but got " + value.type(),
                self.pos,
            )
        return value

    def getFunc(self, name):
        value = self.get(name)
        if not value.isFunc():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Func required but got " + value.type(),
                self.pos,
            )
        return value

    def getDate(self, name):
        value = self.get(name)
        if not value.isDate():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Date required but got " + value.type(),
                self.pos,
            )
        return value

    def getAsBoolean(self, name):
        value = self.get(name)
        try:
            return value.asBoolean()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsNode(self, name):
        value = self.get(name)
        try:
            return value.asNode()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsDate(self, name):
        value = self.get(name)
        try:
            return value.asDate()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsString(self, name):
        value = self.get(name)
        try:
            return value.asString()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsPattern(self, name, defaultValue=None):
        if not self.hasArg(name) and defaultValue is not None:
            return defaultValue
        value = self.get(name)
        try:
            return value.asPattern()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsList(self, name):
        value = self.get(name)
        try:
            return value.asList()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsSet(self, name):
        value = self.get(name)
        try:
            return value.asSet()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsObject(self, name):
        value = self.get(name)
        try:
            return value.asObject()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsMap(self, name):
        value = self.get(name)
        try:
            return value.asMap()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsInt(self, name):
        value = self.get(name)
        try:
            return value.asInt()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise

    def getAsDecimal(self, name):
        value = self.get(name)
        try:
            return value.asDecimal()
        except CklRuntimeError as e:
            e.pos = self.pos
            raise


class StringInput:
    def __init__(self, s):
        self.input = s
        self.pos = 0

    def process(self, callback):
        line = self.readLine()
        count = 0
        while line:
            callback(line)
            count += 1
            line = self.readLine()
        return count

    def read(self):
        if self.pos >= self.input.length:
            return None
        result = self.input[self.pos:self.pos+1]
        self.pos += 1
        return result

    def readAll(self):
        if self.pos >= self.input.length:
            return None
        result = self.input[self.pos:]
        self.pos = self.input.length
        return result

    def readLine(self):
        if self.pos >= self.input.length:
            return None
        if self.input.find("\n", self.pos) != -1:
            result = self.input[self.pos:self.input.find("\n", self.pos)]
            self.pos = self.input.find("\n", self.pos) + 1
            return result
        else:
            result = self.input[self.pos:]
            self.pos = self.input.length
            return result

    def close(self):
        pass


class StringOutput:
    def __init__(
        self,
    ):
        self.output = ""

    def write(self, s):
        self.output += s

    def writeLine(self, s):
        self.output += s
        self.output += "\n"

    def flush(self):
        pass

    def close(self):
        pass


class ConsoleOutput:
    def __init__(
        self,
    ):
        self.buffer = ""

    def write(self, s):
        self.buffer += s
        while self.buffer.find("\n") != -1:
            print(self.buffer[0, self.buffer.find("\n")], end="")
            self.buffer = self.buffer[self.buffer.find("\n")+1:]

    def writeLine(self, s):
        self.buffer += s
        self.buffer += "\n"
        print(self.buffer, end="")
        self.buffer = ""

    def flush(self):
        if self.buffer != "":
            print(self.buffer, end="")
        self.buffer = ""

    def close(self):
        pass


class FileInput:
    def __init__(self, filename, encoding):
        self.encoding = encoding.toLowerCase()
        if self.encoding == "utf-8":
            self.encoding = "utf8"
        # TODO rewrite to use open stream instead of reading all in at start.
        with open(filename, encoding=self.encoding) as infile:
            self.buffer = StringInput(infile.read())

    def process(self, callback):
        return self.buffer.process(callback)

    def read(self):
        return self.buffer.read()

    def readAll(self):
        return self.buffer.readAll()

    def readLine(self):
        return self.buffer.readLine()

    def close(self):
        return self.buffer.close()


class FileOutput:
    def __init__(self, filename, encoding, append):
        self.encoding = encoding.toLowerCase()
        if self.encoding == "utf-8":
            self.encoding = "utf8"
        flags = "w"
        if append:
            flags = "a"
        self.fd = open(filename, flags, encoding=self.encoding)

    def write(self, s):
        self.fd.write(s)

    def writeLine(self, s):
        self.fd.write(s + "\n")

    def flush(self):
        self.fd.flush()

    def close(self):
        self.fd.close()
        self.fd = None


class Value:
    def __init__(self):
        self.info = ""

    def asString(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to String")

    def asInt(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to int")

    def asDecimal(self):
        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot convert to decimal"
        )

    def asBoolean(self):
        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot convert to boolean"
        )

    def asPattern(self):
        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot convert to pattern"
        )

    def asDate(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to date")

    def asList(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to list")

    def asSet(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to set")

    def asMap(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to map")

    def asFunc(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to func")

    def asInput(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to input")

    def asOutput(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to output")

    def asNull(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to NULL")

    def asNode(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to Node")

    def asObject(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to Object")

    def asBreak(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to break")

    def asContinue(self):
        raise CklRuntimeError(
            ValueString("ERROR"), "Cannot convert to continue"
        )

    def asReturn(self):
        raise CklRuntimeError(ValueString("ERROR"), "Cannot convert to return")

    def isString(self):
        return False

    def isInt(self):
        return False

    def isDecimal(self):
        return False

    def isBoolean(self):
        return False

    def isDate(self):
        return False

    def isPattern(self):
        return False

    def isList(self):
        return False

    def isSet(self):
        return False

    def isMap(self):
        return False

    def isObject(self):
        return False

    def isFunc(self):
        return False

    def isInput(self):
        return False

    def isOutput(self):
        return False

    def isNull(self):
        return False

    def isNode(self):
        return False

    def isBreak(self):
        return False

    def isContinue(self):
        return False

    def isReturn(self):
        return False

    def isCollection(self):
        return self.isList() or self.isSet()

    def isAtomic(self):
        return (
            self.isString()
            or self.isInt()
            or self.isDecimal()
            or self.isBoolean()
            or self.isDate()
            or self.isPattern()
            or self.isNull()
        )

    def isNumerical(self):
        return self.isInt() or self.isDecimal()

    def withInfo(self, info):
        self.info = info
        return self


@functools.total_ordering
class ValueBoolean(Value):
    def __init__(self, value):
        self.value = value

    @classmethod
    def fromval(cls, value):
        return TRUE if value else FALSE

    def isTrue(self):
        return self.value

    def isFalse(self):
        return not self.value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, ValueBoolean):
            return False
        return self.value == other.value

    def __lt__(self, other):
        if not isinstance(other, ValueBoolean):
            return str(self) < str(other)
        return self.value - other.value

    def __repr__(self):
        return "TRUE" if self.value else "FALSE"

    def type(self):
        return "boolean"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return ValueInt(1 if self.value else 0)

    def asDecimal(self):
        return ValueDecimal(1.0 if self.value else 0.0)

    def asBoolean(self):
        return self

    def asPattern(self):
        return self.asString().asPattern()

    def asList(self):
        return ValueList().addItem(self)

    def isBoolean(self):
        return True


TRUE = ValueBoolean(True)
FALSE = ValueBoolean(False)


@functools.total_ordering
class ValueControlBreak(Value):
    def __init__(self, pos):
        self.pos = pos

    def __hash__(self):
        return hash("break")

    def __eq__(self, other):
        return self == other

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return "break"

    def type(self):
        return "break"

    def isBreak(self):
        return True

    def asBreak(self):
        return self


@functools.total_ordering
class ValueControlContinue(Value):
    def __init__(self, pos):
        self.pos = pos

    def __hash__(self):
        return hash("continue")

    def __eq__(self, other):
        return self == other

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return "continue"

    def type(self):
        return "continue"

    def isContinue(self):
        return True

    def asContinue(self):
        return self


@functools.total_ordering
class ValueControlReturn(Value):
    def __init__(self, value, pos):
        self.value = value
        self.pos = pos

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        return self == other

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return f"return {self.value}"

    def type(self):
        return "return"

    def isReturn(self):
        return True

    def asReturn(self):
        return self


@functools.total_ordering
class ValueDate(Value):
    def __init__(self, value=None):
        self.value = value if value else datetime.datetime.now()

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, ValueDate):
            return False
        return self.value == other.value

    def __lt__(self, other):
        if not isinstance(other, ValueDate):
            return str(self) < str(other)
        return self.value < other.value

    def __repr__(self):
        return self.value.strftime("%Y%m%d%H%M%S")

    def type(self):
        return "date"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return ValueInt(math.trunc(self.value.timestamp()))

    def asDecimal(self):
        return ValueDecimal(self.value.timestamp())

    def asDate(self):
        return self

    def asList(self):
        return ValueList().addItem(self)

    def isDate(self):
        return True


@functools.total_ordering
class ValueDecimal(Value):
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not other.isNumerical():
            return False
        return self.value == other.asDecimal().value

    def __lt__(self, other):
        if not other.isNumerical():
            return str(self) < str(other)
        return self.value < other.asDecimal().value

    def __repr__(self):
        result = repr(self.value)
        if "." not in result:
            result += ".0"
        return result

    def type(self):
        return "decimal"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return ValueInt(math.trunc(self.value))

    def asDecimal(self):
        return self

    def asDate(self):
        return ValueDate(datetime.datetime.fromtimestamp(self.value))

    def asList(self):
        return ValueList().addItem(self)

    def isDecimal(self):
        return True


@functools.total_ordering
class ValueFunc(Value):
    def __init__(self, name):
        self.name = name
        self.secure = True

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self == other

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return f"<#{self.name}>"

    def type(self):
        return "func"

    def asString(self):
        return ValueString(str(self))

    def asFunc(self):
        return self

    def isFunc(self):
        return True


@functools.total_ordering
class ValueInput(Value):
    def __init__(self, input_):
        self.input = input_
        self.closed = False

    def __hash__(self):
        return hash("input")

    def __eq__(self, other):
        return self == other

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return "<!input-stream>"

    def process(self, callback):
        return self.input.process(callback)

    def readLine(self):
        return self.input.readLine()

    def read(self):
        return self.input.read()

    def readAll(self):
        return self.input.readAll()

    def close(self):
        if self.closed:
            return
        self.input.close()
        self.closed = True

    def type(self):
        return "input"

    def asString(self):
        return ValueString(str(self))

    def asInput(self):
        return self

    def isInput(self):
        return True


@functools.total_ordering
class ValueInt(Value):
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not other.isNumerical():
            return False
        if isinstance(other, ValueDecimal):
            return self.asDecimal() == other
        return self.value == other.value

    def __lt__(self, other):
        if not other.isNumerical():
            return str(self) < str(other)
        if isinstance(other, ValueDecimal):
            return self.asDecimal() < other
        return self.value < other.value

    def __repr__(self):
        return str(self.value)

    def type(self):
        return "int"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return self

    def asDecimal(self):
        return ValueDecimal(self.value)

    def asBoolean(self):
        return ValueBoolean.fromval(self.value != 0)

    def asDate(self):
        return ValueDate(datetime.datetime.fromtimestamp(self.value))

    def asList(self):
        return ValueList().addItem(self)

    def isInt(self):
        return True


@functools.total_ordering
class ValueList(Value):
    def __init__(self):
        self.value = []

    def __hash__(self):
        return sum(hash(s) for s in self.value)

    def __eq__(self, other):
        if not isinstance(other, ValueList):
            return False
        return self.value == other.value

    def __lt__(self, other):
        if not isinstance(other, ValueList):
            return str(self) < str(other)
        return self.value < other.value

    def __repr__(self):
        return "[" + ", ".join([str(item) for item in self.value]) + "]"

    def addItems(self, list_):
        self.value = self.value + list_
        return self

    def addItem(self, item):
        self.value.append(item)
        return self

    def findItem(self, item):
        for index, value in enumerate(self.value):
            if value == item:
                return index
        return -1

    def removeItem(self, item):
        self.value.remove(item)

    def deleteAt(self, index):
        if index >= len(self.value):
            return NULL
        result = self.value[index]
        del self.value[index]
        return result

    def insertAt(self, index, value):
        idx = index
        if idx < 0:
            idx = len(self.value) + idx
        if idx > len(self.value):
            return self
        if idx == len(self.value):
            self.value.append(value)
        else:
            self.value.insert(idx, value)
        return self

    def type(self):
        return "list"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return ValueInt(len(self.value))

    def asBoolean(self):
        return ValueBoolean.fromval(len(self.value) > 0)

    def asList(self):
        return self

    def asSet(self):
        result = ValueSet()
        for item in self.value:
            result.addItem(item)
        return result

    def asMap(self):
        result = ValueMap()
        for entry in self.value:
            result.addItem(entry.value[0], entry.value[1])
        return result

    def asObject(self):
        result = ValueObject()
        for entry in self.value:
            result.addItem(entry.value[0].asString().value, entry.value[1])
        return result

    def isList(self):
        return True


@functools.total_ordering
class ValueMap(Value):
    def __init__(self):
        self.value = dict()

    def __hash__(self):
        return sum(hash(k) + hash(v) for k, v in self.value.items())

    def __eq__(self, other):
        if not isinstance(other, ValueMap):
            return False
        return self.value == other.value

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return (
            "<<<"
            + ", ".join(
                [
                    f"{key} => {self.value[key]}"
                    for key in self.getSortedKeys()
                ]
            )
            + ">>>"
        )

    def addMap(self, map_):
        for key, value in map_.items():
            self.value[key] = value
        return self

    def addItem(self, key, value):
        self.value[key] = value
        return self

    def hasItem(self, key):
        return key in self.value

    def getItem(self, key):
        return self.value[key]

    def removeItem(self, key):
        del self.value[key]

    def getSortedKeys(self):
        return sorted(self.value.keys())

    def type(self):
        return "map"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return ValueInt(len(self.value))

    def asBoolean(self):
        return ValueBoolean.fromval(len(self.value) > 0)

    def asList(self):
        result = ValueList()
        for value in sorted(self.value.values()):
            result.addItem(value)
        return result

    def asSet(self):
        result = ValueSet()
        for key in self.value.keys():
            result.addItem(key)
        return result

    def asObject(self):
        result = ValueObject()
        for key, value in self.value.items():
            result.addItem(key.asString().value, value)
        return result

    def asMap(self):
        return self

    def isMap(self):
        return True


@functools.total_ordering
class ValueNode(Value):
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return hash("node")

    def __eq__(self, other):
        if not isinstance(other, ValueNode):
            return False
        return str(self.value) == str(other.value)

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return str(self.value)

    def type(self):
        return "node"

    def asNode(self):
        return self

    def asString(self):
        return ValueString(str(self))

    def isNode(self):
        return True


@functools.total_ordering
class ValueNull(Value):
    def __init__(self):
        self.value = None

    def __hash__(self):
        return 0

    def __eq__(self, other):
        return other == NULL

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return "NULL"

    def type(self):
        return "null"

    def asNull(self):
        return self

    def asInt(self):
        return ValueInt(0)

    def asString(self):
        return ValueString("")

    def isNull(self):
        return True


NULL = ValueNull()


@functools.total_ordering
class ValueObject(Value):
    def __init__(self):
        self.value = dict()
        self.isModule = False

    def __hash__(self):
        return sum(hash(k) + hash(v) for k, v in self.value.items())

    def __eq__(self, other):
        if not isinstance(other, ValueObject):
            return False
        return self.value == other.value

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        fn = self.resolveItem("_str_")
        if fn:
            args_ = Args(None)
            args_.addArgs(fn.getArgNames())
            args_.setArgs([None], [self])
            try:
                return fn.execute(args_).value
            except CklRuntimeError as e:
                e.stacktrace.append("_str_")
                raise
        else:
            return (
                "<*"
                + ", ".join(
                    [
                        f"{key}={self.value.get(key)}"
                        for key in self.value.keys()
                        if not key.startswith("_")
                    ]
                )
                + "*>"
            )

    def addItem(self, key, value):
        self.value[key] = value
        return self

    def hasItem(self, key):
        return key in self.value

    def getItem(self, key):
        return self.value.get(key)

    def removeItem(self, key):
        del self.value[key]
        return self.value

    def resolveItem(self, key):
        if self.hasItem(key):
            return self.getItem(key)
        current = self
        while current.hasItem("_proto_"):
            current = current.getItem("_proto_")
            if not current:
                break
            if current.hasItem(key):
                return current.getItem(key)
        return None

    def type(self):
        return "object"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return ValueInt(len(self.value))

    def asBoolean(self):
        return ValueBoolean.fromval(len(self.value) > 0)

    def asList(self):
        result = ValueList()
        for value in self.value.values:
            result.addItem(value)
        return result

    def asSet(self):
        result = ValueSet()
        for key in self.value.keys():
            result.addItem(ValueString(key))
        return result

    def asMap(self):
        result = ValueMap()
        for key, value in self.value.items():
            result.addItem(ValueString(key), value)
        return result

    def asObject(self):
        return self

    def isObject(self):
        return True

    def keys(self):
        return [ValueString(member) for member in self.value.keys()]


@functools.total_ordering
class ValueOutput(Value):
    def __init__(self, output):
        self.output = output
        self.closed = False

    def __hash__(self):
        return hash("output")

    def __eq__(self, other):
        return other == self

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return "<!output-stream>"

    def write(self, s):
        self.output.write(s)

    def writeLine(self, s):
        self.output.write(s)
        self.output.write("\n")
        self.output.flush()

    def close(self):
        if self.closed:
            return
        self.output.close()
        self.closed = True

    def type(self):
        return "output"

    def asOutput(self):
        return self

    def isOutput(self):
        return True

    def getStringOutput(self):
        # This does only really work for string output objects...
        return str(self.output)


@functools.total_ordering
class ValuePattern(Value):
    def __init__(self, value):
        self.value = value
        self.pattern = re.compile(value)

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, ValuePattern):
            return False
        return self.value == other.value

    def __lt__(self, other):
        if not isinstance(other, ValuePattern):
            return str(self) < str(other)
        return self.value < other.value

    def __repr__(self):
        return f"//{self.value}//"

    def type(self):
        return "pattern"

    def asString(self):
        return ValueString(self.value)

    def asPattern(self):
        return self

    def asList(self):
        return ValueList().addItem(self)

    def isPattern(self):
        return True


@functools.total_ordering
class ValueSet(Value):
    def __init__(self):
        self.value = set()

    def __hash__(self):
        return sum(hash(v) for v in self.value)

    def __eq__(self, other):
        if not isinstance(other, ValueSet):
            return False
        return self.value == other.value

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        return (
            "<<"
            + ", ".join([str(item) for item in self.getSortedItems()])
            + ">>"
        )

    def addItem(self, item):
        self.value.add(item)
        return self

    def addItems(self, items):
        self.value = self.value | set(items)
        return self

    def hasItem(self, item):
        return item in self.value

    def removeItem(self, item):
        self.value.remove(item)

    def getSortedItems(self):
        return sorted(self.value)

    def type(self):
        return "set"

    def asString(self):
        return ValueString(str(self))

    def asInt(self):
        return ValueInt(len(self.value))

    def asBoolean(self):
        return ValueBoolean.fromval(len(self.value) > 0)

    def asList(self):
        result = ValueList()
        for value in self.getSortedItems():
            result.addItem(value)
        return result

    def asSet(self):
        return self

    def isSet(self):
        return True


@functools.total_ordering
class ValueString(Value):
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, ValueString):
            return False
        return self.value == other.value

    def __lt__(self, other):
        return str(self) < str(other)

    def __repr__(self):
        result = self.value
        result = result.replace("\\", "\\\\")
        result = result.replace("'", "\\'")
        result = result.replace("\r", "\\r")
        result = result.replace("\n", "\\n")
        result = result.replace("\t", "\\t")
        return f"'{result}'"

    def type(self):
        return "string"

    def matches(self, pattern):
        return re.match(pattern.asPattern.pattern, self.value) is not None

    def asString(self):
        return self

    def asInt(self):
        try:
            return ValueInt(int(self.value))
        except ValueError:
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot convert " + str(self.value) + " to int",
            )

    def asDecimal(self):
        try:
            return ValueDecimal(float(self.value))
        except ValueError:
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot convert " + str(self.value) + " to decimal",
            )

    def asBoolean(self):
        if self.value == "1":
            return TRUE
        if self.value == "0":
            return FALSE
        return ValueBoolean.fromval(self.value.upper() == "TRUE")

    def asDate(self):
        # handle yyyyMMddHHmmss, yyyyMMddHH and yyyyMMdd
        # raise exception if not matching
        if len(self.value) < 8:
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot convert " + str(self.value) + " to date",
            )
        try:
            if len(self.value) == 14:
                return ValueDate(datetime.datetime.strptime("%Y%m%d%H%M%S"))
            elif len(self.value) == 10:
                return ValueDate(datetime.datetime.strptime("%Y%m%d%H"))
            elif len(self.value) == 8:
                return ValueDate(datetime.datetime.strptime("%Y%m%d"))
        except ValueError:
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Cannot convert " + str(self.value) + " to date",
            )

    def asPattern(self):
        return ValuePattern(self.value)

    def asList(self):
        return ValueList().addItem(self)

    def isString(self):
        return True
