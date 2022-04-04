import pkgutil

from ckl.errors import CklRuntimeError, CklSyntaxError
from ckl.values import (
    Args,
    Value,
    ValueBoolean,
    ValueControlBreak,
    ValueControlContinue,
    ValueControlReturn,
    ValueList,
    ValueMap,
    ValueObject,
    ValueSet,
    ValueString,
    TRUE,
    FALSE,
    NULL,
)


def convertEntries(entries):
    result = []
    for key, value in entries.items():
        entry = ValueList()
        entry.addItem(key if isinstance(key, Value) else ValueString(key))
        entry.addItem(value)
        result.append(entry)
    return result


def getCollectionValue(collection, what):
    if collection.isList():
        return collection.value
    elif collection.isSet():
        return collection.value.sortedValues()
    elif collection.isMap() and what == "keys":
        return collection.value.sortedKeys()
    elif collection.isMap() and what == "values":
        return collection.value.sortedValues()
    elif collection.isMap():
        return convertEntries(collection.value.sortedEntries())
    elif collection.isObject() and what == "values":
        return collection.value.values()
    elif collection.isObject() and what == "entries":
        return convertEntries(collection.value.entries())
    elif collection.isObject():
        return collection.keys()
    elif collection.isString():
        return [ch for ch in collection.value]
    else:
        return None


def getFuncallString(fn, args):
    return f"{fn.name}({args.toStringAbbrev()})"


def invoke(fn, names_, args, environment, pos):
    values = []
    names = []
    for i in range(len(args)):
        arg = args[i]
        if isinstance(arg, NodeSpread):
            argvalue = arg.evaluate(environment)
            if argvalue.isMap():
                for key, value in argvalue.value.items():
                    values.append(value)
                    if key.isString():
                        names.append(key.value)
                    else:
                        names.append(None)
            else:
                for value in argvalue.value:
                    values.append(value)
                    names.append(None)
        else:
            values.append(arg.evaluate(environment))
            names.append(names_[i])
    args_ = Args(pos)
    args_.addArgs(fn.getArgNames())
    args_.setArgs(names, values)

    try:
        return fn.execute(args_, environment, pos)
    except CklRuntimeError as e:
        e.stacktrace.append(getFuncallString(fn, args_) + " " + str(pos))
        raise


class NodeAnd:
    def __init__(self, expression, pos):
        self.expressions = [expression] if expression else []
        self.pos = pos

    def addAndClause(self, expression):
        self.expressions.append(expression)
        return self

    def getSimplified(self):
        if len(self.expressions) == 1:
            return self.expressions[0]
        return self

    def evaluate(self, environment):
        for expression in self.expressions:
            value = expression.evaluate(environment)
            if not value.isBoolean():
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    f"Expected boolean but got {value.type()}",
                    self.pos,
                )
            if not value.value:
                return FALSE
        return TRUE

    def __repr__(self):
        return (
            "(" + " and ".join([repr(expr) for expr in self.expressions]) + ")"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for expression in self.expressions:
            expression.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeAssign:
    def __init__(self, identifier, expression, pos):
        if identifier.startswith("checkerlang_"):
            raise CklSyntaxError(
                f"Cannot assign to system variable {identifier}", self.pos
            )
        self.identifier = identifier
        self.expression = expression
        self.pos = pos

    def evaluate(self, environment):
        if not environment.isDefined(self.identifier):
            raise CklRuntimeError(
                ValueString("ERROR"),
                f"Variable {self.identifier} is not defined",
                self.pos,
            )
        environment.set(self.identifier, self.expression.evaluate(environment))
        return environment.get(self.identifier, self.pos)

    def __repr__(self):
        return f"({self.identifier!s} = {self.expression})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeAssignDestructuring:
    def __init__(self, identifiers, expression, pos):
        for identifier in identifiers:
            if identifier.startswith("checkerlang_"):
                raise CklSyntaxError(
                    f"Cannot assign to system variable {identifier}", self.pos
                )
        self.identifiers = identifiers
        self.expression = expression
        self.pos = pos

    def evaluate(self, environment):
        values = self.expression.evaluate(environment)
        if values.isList():
            values = values.value
        elif values.isSet():
            values = values.value.sortedValues()
        else:
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Destructuring assign expects list "
                f"or set but got {values.type()}",
                self.pos,
            )
        result = NULL
        for i in range(len(self.identifiers)):
            identifier = self.identifiers[i]
            value = NULL
            if i < len(values):
                value = values[i]
            if not environment.isDefined(identifier):
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    f"Variable {identifier} is not defined",
                    self.pos,
                )
            environment.set(identifier, value)
            result = value
        return result

    def __repr__(self):
        identifiers = ",".join(str(identifier) for identifier in self.identifiers)
        return f"([{identifiers!s}] = {self.expression})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeBlock:
    def __init__(self, pos, toplevel=False):
        self.expressions = []
        self.catchexprs = []
        self.finallyexprs = []
        self.pos = pos
        self.toplevel = toplevel

    def add(self, expression):
        self.expressions.append(expression)

    def addFinally(self, expression):
        self.finallyexprs.append(expression)

    def hasFinally(self):
        return len(self.finallyexprs) > 0

    def addCatch(self, err, expr):
        self.catchexprs.append([err, expr])

    def hasCatch(self):
        return len(self.catchexprs) > 0

    def evaluate(self, environment):
        result = TRUE
        try:
            for expression in self.expressions:
                result = expression.evaluate(environment)
                if result.isReturn():
                    break
                if result.isBreak():
                    break
                if result.isContinue():
                    break
        except CklRuntimeError as e:
            for err, expr in self.catchexprs:
                if not err or e.value == err.evaluate(environment):
                    return expr.evaluate(environment)
            raise
        finally:
            for expression in self.finallyexprs:
                expression.evaluate(environment)
        return result

    def __repr__(self):
        result = "(block "
        result += ", ".join([repr(e) for e in self.expressions])
        if self.catchexprs:
            result += " ".join(
                [
                    " catch " + repr(err) + " " + repr(expr)
                    for err, expr in self.catchexprs
                ]
            )
        if self.finallyexprs:
            result += " finally "
            result += ", ".join([repr(e) for e in self.finallyexprs])
        return result + ")"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        additionalBoundVarsLocal = additionalBoundVars[:]
        for expression in self.expressions:
            if isinstance(expression, NodeDef):
                if expression.identifier not in additionalBoundVarsLocal:
                    additionalBoundVarsLocal.append(expression.identifier)
            if isinstance(expression, NodeDefDestructuring):
                for identifier in expression.identifiers:
                    if identifier not in additionalBoundVarsLocal:
                        additionalBoundVarsLocal.append(identifier)

        for expression in self.finallyexprs:
            if isinstance(expression, NodeDef):
                if expression.identifier not in additionalBoundVarsLocal:
                    additionalBoundVarsLocal.append(expression.identifier)
            if isinstance(expression, NodeDefDestructuring):
                for identifier in expression.identifiers:
                    if identifier not in additionalBoundVarsLocal:
                        additionalBoundVarsLocal.append(identifier)

        for err, expression in self.catchexprs:
            if isinstance(expression, NodeDef):
                if expression.identifier not in additionalBoundVarsLocal:
                    additionalBoundVarsLocal.append(expression.identifier)
            if isinstance(expression, NodeDefDestructuring):
                for identifier in expression.identifiers:
                    if identifier not in additionalBoundVarsLocal:
                        additionalBoundVarsLocal.append(identifier)

        for expression in self.expressions:
            if isinstance(expression, NodeDef) or isinstance(
                expression, NodeDefDestructuring
            ):
                expression.collectVars(
                    freeVars, boundVars, additionalBoundVarsLocal
                )
            else:
                expression.collectVars(
                    freeVars, boundVars, additionalBoundVars
                )

        for expression in self.finallyexprs:
            if isinstance(expression, NodeDef) or isinstance(
                expression, NodeDefDestructuring
            ):
                expression.collectVars(
                    freeVars, boundVars, additionalBoundVarsLocal
                )
            else:
                expression.collectVars(
                    freeVars, boundVars, additionalBoundVars
                )

        for err, expression in self.catchexprs:
            if isinstance(expression, NodeDef) or isinstance(
                expression, NodeDefDestructuring
            ):
                expression.collectVars(
                    freeVars, boundVars, additionalBoundVarsLocal
                )
            else:
                expression.collectVars(
                    freeVars, boundVars, additionalBoundVars
                )
            err.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeBreak:
    def __init__(self, pos):
        self.pos = pos

    def evaluate(self, environment):
        return ValueControlBreak(self.pos)

    def __repr__(self):
        return "(break)"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        pass


class NodeContinue:
    def __init__(self, pos):
        self.pos = pos

    def evaluate(self, environment):
        return ValueControlContinue(self.pos)

    def __repr__(self):
        return "(continue)"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        pass


class NodeDef:
    def __init__(self, identifier, expression, info, pos):
        self.identifier = identifier
        self.expression = expression
        self.info = info
        self.pos = pos

    def evaluate(self, environment):
        value = self.expression.evaluate(environment)
        value.info = self.info
        environment.put(self.identifier, value)
        import ckl.functions
        if isinstance(value, ckl.functions.FuncLambda):
            value.name = self.identifier
        return value

    def __repr__(self):
        return f"(def {self.identifier} = {self.expression})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.identifier not in boundVars:
            boundVars.append(self.identifier)


class NodeDefDestructuring:
    def __init__(self, identifiers, expression, info, pos):
        self.identifiers = identifiers
        self.expression = expression
        self.info = info
        self.pos = pos

    def evaluate(self, environment):
        value = self.expression.evaluate(environment)
        value.info = self.info
        if not value.isList() and not value.isSet():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Destructuring def expects list or "
                f"set but got {value.type()}",
                self.pos,
            )
        values = None
        if value.isList():
            values = value.value
        if value.isSet():
            values = value.value.sortedValues()
        result = NULL
        for i in range(len(self.identifiers)):
            if i < len(values):
                environment.put(self.identifiers[i], values[i])
                import ckl.functions
                if isinstance(values[i], ckl.functions.FuncLambda):
                    values[i].name = self.identifiers[i]
                result = values[i]
            else:
                environment.put(self.identifiers[i], NULL)
                result = NULL
        return result

    def __repr__(self):
        identifiers = ",".join(str(identifier) for identifier in self.identifiers)
        return f"(def [{identifiers!s}] = {self.expression})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)
        for identifier in self.identifiers:
            if identifier not in boundVars:
                boundVars.append(identifier)


class NodeDeref:
    def __init__(self, expression, index, default_value, pos):
        self.expression = expression
        self.index = index
        self.default_value = default_value
        self.pos = pos

    def evaluate(self, environment):
        idx = self.index.evaluate(environment)
        value = self.expression.evaluate(environment)

        if value == NULL:
            return NULL

        if value.isString():
            if self.default_value:
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    "Default value not allowed in string dereference",
                    self.pos,
                )
            s = value.value
            i = int(idx.value)
            if i < 0:
                i = i + len(s)
            if i < 0 or i >= len(s):
                raise CklRuntimeError(
                    ValueString("ERROR"), f"Index out of bounds {i}", self.pos
                )
            return ValueString(s[i])

        if value.isList():
            if self.default_value:
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    "Default value not allowed in list dereference",
                    self.pos,
                )
            lst = value.value
            i = int(idx.value)
            if i < 0:
                i = i + len(lst)
            if i < 0 or i >= len(lst):
                raise CklRuntimeError(
                    ValueString("ERROR"), f"Index out of bounds {i}", self.pos
                )
            return lst[i]

        if value.isMap():
            if not value.hasItem(idx):
                if not self.default_value:
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        f"Map does not contain key {idx}",
                        self.pos,
                    )
                else:
                    return self.default_value.evaluate(environment)
            return value.getItem(idx)

        if value.isObject():
            member = idx.asString().value
            exists = value.hasItem(member)
            while not exists and value.hasItem("_proto_"):
                value = value.getItem("_proto_")
                exists = value.hasItem(member)
            if not exists:
                if self.default_value:
                    return self.default_value.evaluate(environment)
                else:
                    return NULL
            return value.getItem(member)

        raise CklRuntimeError(
            ValueString("ERROR"), f"Cannot dereference value {value}", self.pos
        )

    def __repr__(self):
        return (
            self.expression
            + "["
            + self.index
            + (", " + self.default_value if self.default_value else "")
            + "]"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)
        self.index.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeDerefAssign:
    def __init__(self, expression, index, value, pos):
        self.expression = expression
        self.value = value
        self.index = index
        self.pos = pos

    def evaluate(self, environment):
        idx = self.index.evaluate(environment)
        container = self.expression.evaluate(environment)
        value = self.value.evaluate(environment)

        if container.isString():
            s = container.value
            i = int(idx.value)
            if i < 0:
                i = i + len(s)
            if i < 0 or i >= len(s):
                raise CklRuntimeError(
                    ValueString("ERROR"), f"Index out of bounds {i}", self.pos
                )
            container.value = s[0:i] + value.value + s[i+1:]
            return container

        if container.isList():
            lst = container.value
            i = int(idx.value)
            if i < 0:
                i = i + len(lst)
            if i < 0 or i >= len(lst):
                raise CklRuntimeError(
                    ValueString("ERROR"), f"Index out of bounds {i}", self.pos
                )
            lst[i] = value
            return container

        if container.isMap():
            container.value[idx] = value
            return container

        if container.isObject():
            container.value[idx.asString().value] = value
            return container

        raise CklRuntimeError(
            ValueString("ERROR"), f"Cannot deref-assign {self.value}", self.pos
        )

    def __repr__(self):
        return f"({self.expression}[{self.index}] = {self.value})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)
        self.index.collectVars(freeVars, boundVars, additionalBoundVars)
        self.value.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeDerefInvoke:
    def __init__(self, objectExpr, member, pos):
        self.objectExpr = objectExpr
        self.member = member
        self.names = []
        self.args = []
        self.pos = pos

    def addArg(self, name, arg):
        self.names.append(name)
        self.args.append(arg)

    def evaluate(self, environment):
        obj_ = self.objectExpr.evaluate(environment)
        if obj_.isObject():
            obj = obj_
            exists = obj.hasItem(self.member)
            while not exists and obj.hasItem("_proto_"):
                obj = obj.getItem("_proto_")
                exists = obj.hasItem(self.member)
            if not exists:
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    f"Member {self.member} not found",
                    self.pos,
                )
            fn = obj.getItem(self.member)
            if not fn.isFunc():
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    f"Member {self.member} is not a function",
                    self.pos,
                )
            if obj_.isModule:
                names = self.names
                args = self.args
            else:
                names = [None] + self.names
                args = [NodeLiteral(obj_, self.pos)] + self.args
            return invoke(fn, names, args, environment, self.pos)

        if obj_.isMap():
            fn = obj_.value[ValueString(self.member)]
            if not fn.isFunc():
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    f"{self.member} is not a function",
                    self.pos,
                )
            return invoke(fn, self.names, self.args, environment, self.pos)

        raise CklRuntimeError(
            ValueString("ERROR"),
            f"Cannot deref-invoke ${obj_.type()}",
            self.pos,
        )

    def __repr__(self):
        result = ", ".join(
            [f"{self.names[i]}={self.args[i]}" for i in range(len(self.args))]
        )
        return f"({self.objectExpr}->{self.member}({result})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.objectExpr.collectVars(freeVars, boundVars, additionalBoundVars)
        for arg in self.args:
            arg.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeError:
    def __init__(self, expression, pos):
        self.expression = expression
        self.pos = pos

    def evaluate(self, environment):
        value = self.expression.evaluate(environment)
        raise CklRuntimeError(value, value, self.pos)

    def __repr__(self):
        return f"(error {self.expression})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeFor:
    def __init__(self, identifiers, expression, block, what, pos):
        self.identifiers = identifiers
        self.expression = expression
        self.block = block
        self.pos = pos
        self.what = what

    def evaluate(self, environment):
        lst = self.expression.evaluate(environment)
        if lst.isInput():
            input_ = lst
            result = TRUE
            line = None
            try:
                line = input_.readLine()
                while line:
                    value = ValueString(line)
                    if len(self.identifiers) == 1:
                        environment.put(self.identifiers[0], value)
                    else:
                        if value.isList():
                            vals = value.value
                        elif value.isSet():
                            vals = value.value.sortedValues()
                        for i in range(len(self.identifiers)):
                            environment.put(self.identifiers[i], vals[i])

                    result = self.block.evaluate(environment)
                    if result.isControlBreak():
                        result = TRUE
                        break
                    elif result.isControlContinue():
                        result = TRUE
                        # continue
                    elif result.isControlReturn():
                        break
                    line = input_.readLine()
                if len(self.identifiers) == 1:
                    environment.remove(self.identifiers[0])
                else:
                    for i in range(len(self.identifiers)):
                        environment.remove(self.identifiers[i])
            except Exception:
                raise CklRuntimeError(
                    ValueString("ERROR"), "Cannot read from input", self.pos
                )
            return result

        if lst.isList():
            values = lst.value
            result = TRUE
            for value in values:
                if len(self.identifiers) == 1:
                    environment.put(self.identifiers[0], value)
                else:
                    if value.isList():
                        vals = value.value
                    elif value.isSet():
                        vals = value.value.sortedValues()
                    for i in range(len(self.identifiers)):
                        environment.put(self.identifiers[i], vals[i])
                result = self.block.evaluate(environment)
                if result.isControlBreak():
                    result = TRUE
                    break
                elif result.isControlContinue():
                    result = TRUE
                    # continue
                elif result.isControlReturn():
                    break
            if len(self.identifiers) == 1:
                environment.remove(self.identifiers[0])
            else:
                for i in range(len(self.identifiers)):
                    environment.remove(self.identifiers[i])
            return result

        if lst.isSet():
            values = lst.value.sortedValues()
            result = TRUE
            for value in values:
                if len(self.identifiers) == 1:
                    environment.put(self.identifiers[0], value)
                else:
                    if value.isList():
                        vals = value.value
                    elif value.isSet():
                        vals = value.value.sortedValues()
                    for i in range(len(self.identifiers)):
                        environment.put(self.identifiers[i], vals[i])
                result = self.block.evaluate(environment)
                if result.isControlBreak():
                    result = TRUE
                    break
                elif result.isControlContinue():
                    result = TRUE
                    # continue
                elif result.isControlReturn():
                    break
            if len(self.identifiers) == 1:
                environment.remove(self.identifiers[0])
            else:
                for i in range(len(self.identifiers)):
                    environment.remove(self.identifiers[i])
            return result

        if lst.isMap():
            values = lst.value.sortedEntries()
            result = TRUE
            for key, value in values:
                val = value
                if self.what == "keys":
                    val = key
                elif self.what == "values":
                    val = value
                elif self.what == "entries":
                    val = ValueList()
                    val.addItem(key)
                    val.addItem(value)
                if len(self.identifiers) == 1:
                    environment.put(self.identifiers[0], val)
                else:
                    if val.isList():
                        vals = val.value
                    elif val.isSet():
                        vals = val.value.sortedValues()
                    for i in range(len(self.identifiers)):
                        environment.put(self.identifiers[i], vals[i])
                result = self.block.evaluate(environment)
                if result.isControlBreak():
                    result = TRUE
                    break
                elif result.isControlContinue():
                    result = TRUE
                    # continue
                elif result.isControlReturn():
                    break
            if len(self.identifiers) == 1:
                environment.remove(self.identifiers[0])
            else:
                for i in range(len(self.identifiers)):
                    environment.remove(self.identifiers[i])
            return result

        if lst.isObject():
            values = lst.value
            result = TRUE
            for key, value in values.items():
                val = value
                if self.what == "keys":
                    val = ValueString(key)
                elif self.what == "values":
                    val = value
                elif self.what == "entries":
                    val = ValueList()
                    val.addItem(ValueString(key))
                    val.addItem(value)
                if len(self.identifiers) == 1:
                    environment.put(self.identifiers[0], val)
                else:
                    if val.isList():
                        vals = val.value
                    elif val.isSet():
                        vals = val.value.sortedValues()
                    for i in range(len(self.identifiers)):
                        environment.put(self.identifiers[i], vals[i])
                result = self.block.evaluate(environment)
                if result.isControlBreak():
                    result = TRUE
                    break
                elif result.isControlContinue():
                    result = TRUE
                    # continue
                elif result.isControlReturn():
                    break
            if len(self.identifiers) == 1:
                environment.remove(self.identifiers[0])
            else:
                for i in range(len(self.identifiers)):
                    environment.remove(self.identifiers[i])
            return result

        if lst.isString():
            s = lst.value
            result = TRUE
            for i in range(len(s)):
                environment.put(self.identifiers[0], ValueString(s[i:i+1]))
                result = self.block.evaluate(environment)
                if result.isControlBreak():
                    result = TRUE
                    break
                elif result.isControlContinue():
                    result = TRUE
                    # continue
                elif result.isControlReturn():
                    break
                environment.remove(self.identifiers[0])
            return result

        raise CklRuntimeError(
            ValueString("ERROR"), f"Cannot iterate over {lst.type()}", self.pos
        )

    def __repr__(self):
        return (
            "(for "
            + (
                self.identifiers[0]
                if len(self.identifiers) == 1
                else "[" + self.identifiers + "]"
            )
            + " in "
            + self.what
            + " "
            + self.expression
            + " do "
            + self.block
            + ")"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)
        boundVarsLocal = [*boundVars, *self.identifiers]
        self.block.collectVars(freeVars, boundVarsLocal, additionalBoundVars)


class NodeFuncall:
    def __init__(self, func, pos):
        self.func = func
        self.names = []
        self.args = []
        self.pos = pos

    def addArg(self, name, arg):
        self.names.append(name)
        self.args.append(arg)

    def evaluate(self, environment):
        fn = self.func.evaluate(environment)
        if not fn.isFunc():
            raise CklRuntimeError(
                ValueString("ERROR"),
                f"Expected def but got {fn.type()}",
                self.pos,
            )
        return invoke(fn, self.names, self.args, environment, self.pos)

    def __repr__(self):
        args = ", ".join([repr(arg) for arg in self.args])
        return f"({self.func} {args})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.func.collectVars(freeVars, boundVars, additionalBoundVars)
        for arg in self.args:
            arg.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeIdentifier:
    def __init__(self, value, pos):
        self.value = value
        self.pos = pos

    def evaluate(self, environment):
        return environment.get(self.value, self.pos)

    def __repr__(self):
        return str(self.value)

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        if (
            self.value not in boundVars
            and self.value not in additionalBoundVars
        ):
            if self.value not in freeVars:
                freeVars.append(self.value)


class NodeIf:
    def __init__(self, pos):
        self.conditions = []
        self.expressions = []
        self.elseExpression = NodeLiteral(TRUE, pos)
        self.pos = pos

    def addIf(self, condition, expression):
        self.conditions.append(condition)
        self.expressions.append(expression)

    def setElse(self, expression):
        self.elseExpression = expression

    def evaluate(self, environment):
        for i in range(len(self.conditions)):
            value = self.conditions[i].evaluate(environment)
            if not value.isBoolean():
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    f"Expected boolean condition value but got {value.type()}",
                    self.pos,
                )
            if value.isTrue():
                return self.expressions[i].evaluate(environment)
        return self.elseExpression.evaluate(environment)

    def __repr__(self):
        return (
            "("
            + " ".join(
                [
                    f"if {self.conditions[i]}: {self.expressions[i]}"
                    for i in range(len(self.conditions))
                ]
            )
            + " else: "
            + repr(self.elseExpression)
            + ")"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for expression in self.conditions:
            expression.collectVars(freeVars, boundVars, additionalBoundVars)

        for expression in self.expressions:
            expression.collectVars(freeVars, boundVars, additionalBoundVars)

        self.elseExpression.collectVars(
            freeVars, boundVars, additionalBoundVars
        )


class NodeIn:
    def __init__(self, expression, lst, pos):
        self.expression = expression
        self.list = lst
        self.pos = pos

    def evaluate(self, environment):
        value = self.expression.evaluate(environment)
        container = self.list.evaluate(environment)
        if container.isList():
            for item in container.value:
                if value == item:
                    return TRUE
        elif container.isSet():
            return ValueBoolean.fromval(container.hasItem(value))
        elif container.isMap():
            return ValueBoolean.fromval(container.hasItem(value))
        elif container.isObject():
            return ValueBoolean.fromval(container.hasItem(value.value))
        elif container.isString():
            return ValueBoolean.fromval(
                container.value.find(value.value) != -1
            )
        return FALSE

    def __repr__(self):
        return f"({self.expression} in {self.list})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)
        self.list.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeLambda:
    def __init__(self, pos):
        self.args = []
        self.defs = []
        self.pos = pos

    def addArg(self, arg, defaultValue=None):
        self.args.append(arg)
        self.defs.append(defaultValue)

    def setBody(self, body):
        if isinstance(body, NodeBlock):
            block = body
            expressions = block.expressions
            if len(expressions) > 0:
                lastexpr = expressions[-1]
                if isinstance(lastexpr, NodeReturn):
                    expressions[-1] = lastexpr.expression
        elif isinstance(body, NodeReturn):
            body = body.expression
        self.body = body

    def evaluate(self, environment):
        import ckl.functions
        result = ckl.functions.FuncLambda(environment)
        for i in range(len(self.args)):
            result.addArg(self.args[i], self.defs[i])
        result.setBody(self.body)
        return result

    def __repr__(self):
        result = "(lambda "
        for i in range(len(self.args)):
            result += str(self.args[i])
            if self.defs[i]:
                result += "=" + repr(self.defs[i])
            result += ", "
        return result + repr(self.body) + ")"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for definition in self.defs:
            if definition:
                definition.collectVars(
                    freeVars, boundVars, additionalBoundVars
                )
        boundVarsLocal = [*boundVars]
        for arg in self.args:
            boundVarsLocal.append(arg)
        self.body.collectVars(freeVars, boundVarsLocal, additionalBoundVars)


class NodeList:
    def __init__(self, pos):
        self.items = []
        self.pos = pos

    def addItem(self, item):
        self.items.append(item)

    def evaluate(self, environment):
        result = ValueList()
        for item in self.items:
            if isinstance(item, NodeSpread):
                lst = item.evaluate(environment)
                for value in lst.value:
                    result.addItem(value)
            else:
                result.addItem(item.evaluate(environment))
        return result

    def __repr__(self):
        return "[" + ", ".join(repr(item) for item in self.items) + "]"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for item in self.items:
            item.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeListComprehension:
    def __init__(self, valueExpr, identifier, listExpr, what, pos):
        self.valueExpr = valueExpr
        self.identifier = identifier
        self.listExpr = listExpr
        self.what = what
        self.conditionExpr = None
        self.pos = pos

    def setCondition(self, conditionExpr):
        self.conditionExpr = conditionExpr

    def evaluate(self, environment):
        result = ValueList()
        localEnv = environment.newEnv()
        lst = self.listExpr.evaluate(environment)
        values = getCollectionValue(lst, self.what)
        for listValue in values:
            localEnv.put(self.identifier, listValue)
            value = self.valueExpr.evaluate(localEnv)
            if self.conditionExpr:
                condition = self.conditionExpr.evaluate(localEnv)
                if not condition.isBoolean():
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        f"Condition must be boolean "
                        f"but got {condition.type()}",
                        self.pos,
                    )
                if condition.value:
                    result.addItem(value)
            else:
                result.addItem(value)
        return result

    def __repr__(self):
        return (
            "["
            + repr(self.valueExpr)
            + " for "
            + repr(self.identifier)
            + " in "
            + ((repr(self.what) + " ") if self.what else "")
            + repr(self.listExpr)
            + (
                (" if " + repr(self.conditionExpr))
                if self.conditionExpr
                else ""
            )
            + "]"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        boundVarsLocal = [*boundVars]
        boundVarsLocal.append(self.identifier)
        self.valueExpr.collectVars(
            freeVars, boundVarsLocal, additionalBoundVars
        )
        self.listExpr.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.conditionExpr:
            self.conditionExpr.collectVars(
                freeVars, boundVarsLocal, additionalBoundVars
            )


class NodeListComprehensionParallel:
    def __init__(
        self,
        valueExpr,
        identifier1,
        listExpr1,
        what1,
        identifier2,
        listExpr2,
        what2,
        pos,
    ):
        self.valueExpr = valueExpr
        self.identifier1 = identifier1
        self.listExpr1 = listExpr1
        self.what1 = what1
        self.identifier2 = identifier2
        self.listExpr2 = listExpr2
        self.what2 = what2
        self.conditionExpr = None
        self.pos = pos

    def setCondition(self, conditionExpr):
        self.conditionExpr = conditionExpr

    def evaluate(self, environment):
        result = ValueList()
        localEnv = environment.newEnv()
        list1 = self.listExpr1.evaluate(environment)
        list2 = self.listExpr2.evaluate(environment)
        values1 = getCollectionValue(list1, self.what1)
        values2 = getCollectionValue(list2, self.what2)
        for i in range(max(len(values1), len(values2))):
            listValue1 = values1[i] if i < len(values1) else None
            listValue2 = values2[i] if i < len(values2) else None
            localEnv.put(self.identifier1, listValue1)
            localEnv.put(self.identifier2, listValue2)
            value = self.valueExpr.evaluate(localEnv)
            if self.conditionExpr:
                condition = self.conditionExpr.evaluate(localEnv)
                if not condition.isBoolean():
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        "Condition must be boolean but "
                        f"got {condition.type()}",
                        self.pos,
                    )
                if condition.value:
                    result.addItem(value)
            else:
                result.addItem(value)
        return result

    def __repr__(self):
        return (
            "["
            + repr(self.valueExpr)
            + " for "
            + repr(self.identifier1)
            + " in "
            + ((repr(self.what1) + " ") if self.what1 else "")
            + repr(self.listExpr1)
            + " also"
            + " for "
            + repr(self.identifier2)
            + " in "
            + ((repr(self.what2) + " ") if self.what2 else "")
            + repr(self.listExpr2)
            + (
                (" if " + repr(self.conditionExpr))
                if self.conditionExpr
                else ""
            )
            + "]"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        boundVarsLocal = [*boundVars]
        boundVarsLocal.append(self.identifier1)
        boundVarsLocal.append(self.identifier2)
        self.valueExpr.collectVars(
            freeVars, boundVarsLocal, additionalBoundVars
        )
        self.listExpr1.collectVars(freeVars, boundVars, additionalBoundVars)
        self.listExpr2.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.conditionExpr:
            self.conditionExpr.collectVars(
                freeVars, boundVarsLocal, additionalBoundVars
            )


class NodeListComprehensionProduct:
    def __init__(
        self,
        valueExpr,
        identifier1,
        listExpr1,
        what1,
        identifier2,
        listExpr2,
        what2,
        pos,
    ):
        self.valueExpr = valueExpr
        self.identifier1 = identifier1
        self.listExpr1 = listExpr1
        self.what1 = what1
        self.identifier2 = identifier2
        self.listExpr2 = listExpr2
        self.what2 = what2
        self.conditionExpr = None
        self.pos = pos

    def setCondition(self, conditionExpr):
        self.conditionExpr = conditionExpr

    def evaluate(self, environment):
        result = ValueList()
        localEnv = environment.newEnv()
        list1 = self.listExpr1.evaluate(environment)
        list2 = self.listExpr2.evaluate(environment)
        values1 = getCollectionValue(list1, self.what1)
        values2 = getCollectionValue(list2, self.what2)
        for listValue1 in values1:
            localEnv.put(self.identifier1, listValue1)
            for listValue2 in values2:
                localEnv.put(self.identifier2, listValue2)
                value = self.valueExpr.evaluate(localEnv)
                if self.conditionExpr:
                    condition = self.conditionExpr.evaluate(localEnv)
                    if not condition.isBoolean():
                        raise CklRuntimeError(
                            ValueString("ERROR"),
                            "Condition must be boolean "
                            f"but got {condition.type()}",
                            self.pos,
                        )
                    if condition.value:
                        result.addItem(value)
                else:
                    result.addItem(value)
        return result

    def __repr__(self):
        return (
            "["
            + repr(self.valueExpr)
            + " for "
            + repr(self.identifier1)
            + " in "
            + ((repr(self.what1) + " ") if self.what1 else "")
            + repr(self.listExpr1)
            + " for "
            + repr(self.identifier2)
            + " in "
            + ((repr(self.what2) + " ") if self.what2 else "")
            + repr(self.listExpr2)
            + (
                (" if " + repr(self.conditionExpr))
                if self.conditionExpr
                else ""
            )
            + "]"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        boundVarsLocal = [*boundVars]
        boundVarsLocal.append(self.identifier1)
        boundVarsLocal.append(self.identifier2)
        self.valueExpr.collectVars(
            freeVars, boundVarsLocal, additionalBoundVars
        )
        self.listExpr1.collectVars(freeVars, boundVars, additionalBoundVars)
        self.listExpr2.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.conditionExpr:
            self.conditionExpr.collectVars(
                freeVars, boundVarsLocal, additionalBoundVars
            )


class NodeLiteral:
    def __init__(self, value, pos):
        self.value = value
        self.pos = pos

    def evaluate(self, environment):
        return self.value

    def __repr__(self):
        return str(self.value)

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        pass


class NodeMap:
    def __init__(self, pos):
        self.keys = []
        self.values = []
        self.pos = pos

    def addKeyValue(self, key, value):
        self.keys.append(key)
        self.values.append(value)

    def evaluate(self, environment):
        result = ValueMap()
        for i in range(len(self.keys)):
            result.addItem(
                self.keys[i].evaluate(environment),
                self.values[i].evaluate(environment),
            )
        return result

    def __repr__(self):
        return (
            "<<<"
            + ", ".join(
                [
                    f"{self.keys[i]} => {self.values[i]}"
                    for i in range(len(self.keys))
                ]
            )
            + ">>>"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for item in self.keys:
            item.collectVars(freeVars, boundVars, additionalBoundVars)
        for item in self.values:
            item.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeMapComprehension:
    def __init__(self, keyExpr, valueExpr, identifier, listExpr, what, pos):
        self.keyExpr = keyExpr
        self.valueExpr = valueExpr
        self.identifier = identifier
        self.listExpr = listExpr
        self.what = what
        self.conditionExpr = None
        self.pos = pos

    def setCondition(self, conditionExpr):
        self.conditionExpr = conditionExpr

    def evaluate(self, environment):
        result = ValueMap()
        localEnv = environment.newEnv()
        lst = self.listExpr.evaluate(environment)
        values = getCollectionValue(lst, self.what)
        for listValue in values:
            localEnv.put(self.identifier, listValue)
            key = self.keyExpr.evaluate(localEnv)
            value = self.valueExpr.evaluate(localEnv)
            if self.conditionExpr:
                condition = self.conditionExpr.evaluate(localEnv)
                if not condition.isBoolean():
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        "Condition must be boolean "
                        f"but got {condition.type()}",
                        self.pos,
                    )
                if condition.value:
                    result.addItem(key, value)
            else:
                result.addItem(key, value)
        return result

    def __repr__(self):
        what = f"{self.what} " if self.what else ""
        cond = f" if {self.conditionExpr}" if self.conditionExpr else ""
        return (
            f"<<<{self.keyExpr} => {self.valueExpr} for {self.identifier} in "
            f"{what}{self.listExpr}{cond}>>>"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        boundVarsLocal = [*boundVars]
        boundVarsLocal.append(self.identifier)
        self.keyExpr.collectVars(freeVars, boundVarsLocal, additionalBoundVars)
        self.valueExpr.collectVars(
            freeVars, boundVarsLocal, additionalBoundVars
        )
        self.listExpr.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.conditionExpr:
            self.conditionExpr.collectVars(
                freeVars, boundVarsLocal, additionalBoundVars
            )


class NodeNot:
    def __init__(self, expression, pos):
        self.expression = expression
        self.pos = pos

    def evaluate(self, environment):
        value = self.expression.evaluate(environment)
        if not value.isBoolean():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Expected boolean but got " + value.type(),
                self.pos,
            )
        return FALSE if value.value else TRUE

    def __repr__(self):
        return f"(not {self.expression})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeNull:
    def __init__(self, pos):
        self.pos = pos

    def evaluate(self, environment):
        return NULL

    def __repr__(self):
        return "NULL"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        pass


class NodeObject:
    def __init__(self, pos):
        self.keys = []
        self.values = []
        self.pos = pos

    def addKeyValue(self, key, value):
        self.keys.append(key)
        self.values.append(value)

    def evaluate(self, environment):
        result = ValueObject()
        for i in range(len(self.keys)):
            result.addItem(self.keys[i], self.values[i].evaluate(environment))
        return result

    def __repr__(self):
        return (
            "<*"
            + ", ".join(
                [
                    f"{self.keys[i]}={self.values[i]}"
                    for i in range(len(self.keys))
                ]
            )
            + "*>"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for item in self.values:
            item.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeOr:
    def __init__(self, pos):
        self.expressions = []
        self.pos = pos

    def addOrClause(self, expression):
        self.expressions.append(expression)
        return self

    def getSimplified(self):
        if len(self.expressions) == 1:
            return self.expressions[0]
        return self

    def evaluate(self, environment):
        for expression in self.expressions:
            value = expression.evaluate(environment)
            if not value.isBoolean():
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    "Expected boolean but got " + value.type(),
                    self.pos,
                )
            if value.value:
                return TRUE
        return FALSE

    def __repr__(self):
        return (
            "(" + " or ".join([repr(expr) for expr in self.expressions]) + ")"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for expression in self.expressions:
            expression.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeRequire:
    def __init__(self, modulespec, name, unqualified, symbols, pos):
        self.modulespec = modulespec
        self.name = name
        self.unqualified = unqualified
        self.symbols = symbols
        self.pos = pos

    def evaluate(self, environment):
        modules = environment.getModules()
        # resolve module file, identifier and name
        modulespec = None
        if isinstance(self.modulespec, NodeIdentifier):
            modulespec = self.modulespec.value

            # If we have an identifier node, then two cases can happen:
            # either the identifier signifies a module, then we want
            # to retain the identifier otherwise, we evaluate the
            # identifier and use the (necessarily) string value
            # thus resulting. This allows things like
            #    for module in sys->checkerlang_modules do
            #        require module unqualified
            #    done
            # while retaining the possibility to use
            #    require math
            # even if the math module is already loaded (and thus
            # "math" is defined in the environment)

            if environment.isDefined(modulespec):
                val = environment.get(modulespec, self.pos)
                if not val.isObject() or not val.isModule:
                    if not val.isString():
                        raise CklRuntimeError(
                            ValueString("ERROR"),
                            "Expected string or identifier "
                            "modulespec but got " + modulespec.type(),
                            self.pos,
                        )
                    modulespec = val.value
        else:
            modulespec = self.modulespec.evaluate(environment)
            if not modulespec.isString():
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    "Expected string or identifier "
                    "modulespec but got " + modulespec.type(),
                    self.pos,
                )
            modulespec = modulespec.value
        modulefile = modulespec
        if not modulefile.endswith(".ckl"):
            modulefile += ".ckl"
        moduleidentifier = None
        modulename = self.name
        parts = modulespec.split("/")
        name = parts[-1]
        if name.endswith(".ckl"):
            name = name[0:-4]
        moduleidentifier = name
        if not modulename:
            modulename = name
        environment.pushModuleStack(moduleidentifier, self.pos)

        # lookup or read module
        moduleEnv = None
        if moduleidentifier in modules:
            moduleEnv = modules[moduleidentifier]
        else:
            moduleEnv = environment.getBase().newEnv()
            # TODO port this, careful with dependencies!
            data = pkgutil.get_data(__name__, "modules/" + modulefile)
            if data:
                modulesrc = data.decode("utf-8")
            else:
                # TODO load module from filesystem (current workdir or modulepath!) if available
                pass
            import ckl.parser
            node = ckl.parser.parse_script(modulesrc, "mod:" + modulefile[0:-4])
            node.evaluate(moduleEnv)
            modules[moduleidentifier] = moduleEnv
        environment.popModuleStack()

        # bind module or contents of module
        if self.unqualified:
            for name in moduleEnv.getLocalSymbols():
                if name.startswith("_"):
                    continue  # skip private module symbols
                environment.put(name, moduleEnv.get(name))
        elif self.symbols:
            for name in moduleEnv.getLocalSymbols():
                if name.startswith("_"):
                    continue  # skip private module symbols
                if name not in self.symbols:
                    continue
                environment.put(self.symbols[name], moduleEnv.get(name))
        else:
            obj = ValueObject()
            obj.isModule = True
            for name in moduleEnv.getLocalSymbols():
                if name.startswith("_"):
                    continue  # skip private module symbols
                val = moduleEnv.get(name)
                if val.isObject() and val.isModule:
                    continue  # do not re-modules!
                obj.addItem(name, val)
            environment.put(modulename, obj)
        return NULL

    def __repr__(self):
        return (
            "(require "
            + repr(self.modulespec)
            + ((" as " + repr(self.name)) if self.name else "")
            + (" unqualified" if self.unqualified else "")
            + ")"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        pass


class NodeReturn:
    def __init__(self, expression, pos):
        self.expression = expression
        self.pos = pos

    def evaluate(self, environment):
        return ValueControlReturn(
            self.expression.evaluate(environment) if self.expression else NULL,
            self.pos,
        )

    def __repr__(self):
        return (
            "(return"
            + ((" " + repr(self.expression)) if self.expression else "")
            + ")"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        if self.expression:
            self.expression.collectVars(
                freeVars, boundVars, additionalBoundVars
            )


class NodeSet:
    def __init__(self, pos):
        self.items = []
        self.pos = pos

    def addItem(self, item):
        self.items.append(item)

    def evaluate(self, environment):
        result = ValueSet()
        for item in self.items:
            result.addItem(item.evaluate(environment))
        return result

    def __repr__(self):
        return "<<" + ", ".join([repr(expr) for expr in self.items]) + ">>"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        for item in self.items:
            item.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeSetComprehension:
    def __init__(self, valueExpr, identifier, listExpr, what, pos):
        self.valueExpr = valueExpr
        self.identifier = identifier
        self.listExpr = listExpr
        self.what = what
        self.conditionExpr = None
        self.pos = pos

    def setCondition(self, conditionExpr):
        self.conditionExpr = conditionExpr

    def evaluate(self, environment):
        result = ValueSet()
        localEnv = environment.newEnv()
        lst = self.listExpr.evaluate(environment)
        values = getCollectionValue(lst, self.what)
        for listValue in values:
            localEnv.put(self.identifier, listValue)
            value = self.valueExpr.evaluate(localEnv)
            if self.conditionExpr:
                condition = self.conditionExpr.evaluate(localEnv)
                if not condition.isBoolean():
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        "Condition must be boolean but got "
                        + condition.type(),
                        self.pos,
                    )
                if condition.value:
                    result.addItem(value)
            else:
                result.addItem(value)
        return result

    def __repr__(self):
        what = f"{self.what} " if self.what else ""
        cond = f" if {self.conditionExpr}" if self.conditionExpr else ""
        return (
            f"<<{self.valueExpr} for {self.identifier} "
            f"in {what}{self.listExpr}{cond}>>"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        boundVarsLocal = [*boundVars]
        boundVarsLocal.append(self.identifier)
        self.valueExpr.collectVars(
            freeVars, boundVarsLocal, additionalBoundVars
        )
        self.listExpr.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.conditionExpr:
            self.conditionExpr.collectVars(
                freeVars, boundVarsLocal, additionalBoundVars
            )


class NodeSetComprehensionParallel:
    def __init__(
        self,
        valueExpr,
        identifier1,
        listExpr1,
        what1,
        identifier2,
        listExpr2,
        what2,
        pos,
    ):
        self.valueExpr = valueExpr
        self.identifier1 = identifier1
        self.listExpr1 = listExpr1
        self.what1 = what1
        self.identifier2 = identifier2
        self.listExpr2 = listExpr2
        self.what2 = what2
        self.conditionExpr = None
        self.pos = pos

    def setCondition(self, conditionExpr):
        self.conditionExpr = conditionExpr

    def evaluate(self, environment):
        result = ValueSet()
        localEnv = environment.newEnv()
        list1 = self.listExpr1.evaluate(environment)
        list2 = self.listExpr2.evaluate(environment)
        values1 = getCollectionValue(list1, self.what1)
        values2 = getCollectionValue(list2, self.what2)
        for i in range(max(len(values1), len(values2))):
            localEnv.put(
                self.identifier1, values1[i] if i < len(values1) else NULL
            )
            localEnv.put(
                self.identifier2, values2[i] if i < len(values2) else NULL
            )
            value = self.valueExpr.evaluate(localEnv)
            if self.conditionExpr:
                condition = self.conditionExpr.evaluate(localEnv)
                if not condition.isBoolean():
                    raise CklRuntimeError(
                        ValueString("ERROR"),
                        "Condition must be boolean but got "
                        + condition.type(),
                        self.pos,
                    )
                if condition.value:
                    result.addItem(value)
            else:
                result.addItem(value)
        return result

    def __repr__(self):
        return (
            "<<"
            + repr(self.valueExpr)
            + " for "
            + repr(self.identifier1)
            + " in "
            + ((repr(self.what1) + " ") if self.what1 else "")
            + repr(self.listExpr1)
            + " also"
            + " for "
            + repr(self.identifier2)
            + " in "
            + ((repr(self.what2) + " ") if self.what2 else "")
            + repr(self.listExpr2)
            + (f" if {self.conditionExpr}" if self.conditionExpr else "")
            + ">>"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        boundVarsLocal = [*boundVars]
        boundVarsLocal.append(self.identifier)
        self.valueExpr.collectVars(
            freeVars, boundVarsLocal, additionalBoundVars
        )
        self.listExpr.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.conditionExpr:
            self.conditionExpr.collectVars(
                freeVars, boundVarsLocal, additionalBoundVars
            )


class NodeSetComprehensionProduct:
    def __init__(
        self,
        valueExpr,
        identifier1,
        listExpr1,
        what1,
        identifier2,
        listExpr2,
        what2,
        pos,
    ):
        self.valueExpr = valueExpr
        self.identifier1 = identifier1
        self.listExpr1 = listExpr1
        self.what1 = what1
        self.identifier2 = identifier2
        self.listExpr2 = listExpr2
        self.what2 = what2
        self.conditionExpr = None
        self.pos = pos

    def setCondition(self, conditionExpr):
        self.conditionExpr = conditionExpr

    def evaluate(self, environment):
        result = ValueSet()
        localEnv = environment.newEnv()
        list1 = self.listExpr1.evaluate(environment)
        list2 = self.listExpr2.evaluate(environment)
        values1 = getCollectionValue(list1, self.what1)
        values2 = getCollectionValue(list2, self.what2)
        for value1 in values1:
            localEnv.put(self.identifier1, value1)
            for value2 in values2:
                localEnv.put(self.identifier2, value2)
                value = self.valueExpr.evaluate(localEnv)
                if self.conditionExpr:
                    condition = self.conditionExpr.evaluate(localEnv)
                    if not condition.isBoolean():
                        raise CklRuntimeError(
                            ValueString("ERROR"),
                            "Condition must be boolean but got "
                            + condition.type(),
                            self.pos,
                        )
                    if condition.value:
                        result.addItem(value)
                else:
                    result.addItem(value)
        return result

    def __repr__(self):
        return (
            "<<"
            + repr(self.valueExpr)
            + " for "
            + repr(self.identifier1)
            + " in "
            + ((repr(self.what1) + " ") if self.what1 else "")
            + repr(self.listExpr1)
            + " for "
            + repr(self.identifier2)
            + " in "
            + ((repr(self.what2) + " ") if self.what2 else "")
            + repr(self.listExpr2)
            + (f" if {self.conditionExpr}" if self.conditionExpr else "")
            + ">>"
        )

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        boundVarsLocal = [*boundVars]
        boundVarsLocal.append(self.identifier)
        self.valueExpr.collectVars(
            freeVars, boundVarsLocal, additionalBoundVars
        )
        self.listExpr.collectVars(freeVars, boundVars, additionalBoundVars)
        if self.conditionExpr:
            self.conditionExpr.collectVars(
                freeVars, boundVarsLocal, additionalBoundVars
            )


class NodeSpread:
    def __init__(self, expression, pos):
        self.expression = expression
        self.pos = pos

    def evaluate(self, environment):
        return self.expression.evaluate(environment)

    def __repr__(self):
        return f"...{self.expression}"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)


class NodeWhile:
    def __init__(self, expression, block, pos):
        self.expression = expression
        self.block = block
        self.pos = pos

    def evaluate(self, environment):
        condition = self.expression.evaluate(environment)
        if not condition.isBoolean():
            raise CklRuntimeError(
                ValueString("ERROR"),
                "Expected boolean condition but got " + condition.type(),
                self.pos,
            )
        result = TRUE
        while condition.value:
            result = self.block.evaluate(environment)
            if result.isControlBreak():
                result = TRUE
                break
            elif result.isControlContinue():
                result = TRUE
                # continue
            elif result.isControlReturn():
                break
            condition = self.expression.evaluate(environment)
            if not condition.isBoolean():
                raise CklRuntimeError(
                    ValueString("ERROR"),
                    "Expected boolean condition but got " + condition.type(),
                    self.pos,
                )
        return result

    def __repr__(self):
        return f"(while {self.expression} do {self.block})"

    def collectVars(self, freeVars, boundVars, additionalBoundVars):
        self.expression.collectVars(freeVars, boundVars, additionalBoundVars)
        boundVarsLocal = boundVars[:]
        self.block.collectVars(freeVars, boundVarsLocal, additionalBoundVars)
