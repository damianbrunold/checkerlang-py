from ckl.errors import CklSyntaxError
from ckl.lexer import Lexer, SourcePos

from ckl.values import (
    ValueBoolean,
    ValueDecimal,
    ValueInt,
    ValuePattern,
    ValueString,
)

from ckl.nodes import (
    NodeAnd,
    NodeAssign,
    NodeAssignDestructuring,
    NodeBlock,
    NodeBreak,
    NodeContinue,
    NodeDef,
    NodeDeref,
    NodeDerefAssign,
    NodeDerefInvoke,
    NodeDefDestructuring,
    NodeError,
    NodeFor,
    NodeFuncall,
    NodeIdentifier,
    NodeIf,
    NodeIn,
    NodeLambda,
    NodeList,
    NodeListComprehension,
    NodeListComprehensionParallel,
    NodeListComprehensionProduct,
    NodeLiteral,
    NodeMap,
    NodeMapComprehension,
    NodeNot,
    NodeNull,
    NodeObject,
    NodeOr,
    NodeRequire,
    NodeReturn,
    NodeSet,
    NodeSetComprehension,
    NodeSetComprehensionParallel,
    NodeSetComprehensionProduct,
    NodeSpread,
    NodeWhile,
)


def parse_script(script, filename="-"):
    return parse(Lexer(script, filename).scan())


def parse(lexer):
    if not lexer.hasNext():
        return NodeNull(SourcePos(lexer.name, 1, 1))
    result = parse_bare_block(lexer, True)
    if lexer.hasNext():
        raise CklSyntaxError(
            f"Expected end of input but got '{lexer.next()}'",
            lexer.getPos(),
        )
    if isinstance(result, NodeReturn):
        result = result.expression
    elif isinstance(result, NodeBlock):
        expressions = result.expressions
        if len(expressions) > 0:
            lastexpr = expressions[-1]
            if isinstance(lastexpr, NodeReturn):
                expressions[-1] = lastexpr.expression
    return result


def parse_bare_block(lexer, toplevel=False):
    block = NodeBlock(lexer.getPosNext(), toplevel)
    if lexer.peekn(1, "do", "keyword"):
        expression = parse_block(lexer)
    else:
        expression = parse_statement(lexer, toplevel)
    if not lexer.hasNext():
        return expression
    block.add(expression)
    while lexer.matchIf(";", "interpunction"):
        if not lexer.hasNext():
            break
        if lexer.peekn(1, "do", "keyword"):
            expression = parse_block(lexer)
        else:
            expression = parse_statement(lexer, toplevel)
        block.add(expression)
    if (
        len(block.expressions) == 1
        and not block.hasFinally()
        and not block.hasCatch()
    ):
        return block.expressions[0]
    return block


def parse_block(lexer):
    block = NodeBlock(lexer.getPosNext())
    lexer.match("do", "keyword")
    while (
        not lexer.peekn(1, "end", "keyword")
        and not lexer.peekn(1, "catch", "keyword")
        and not lexer.peekn(1, "finally", "keyword")
    ):
        if lexer.peekn(1, "do", "keyword"):
            expression = parse_block(lexer)
        else:
            expression = parse_statement(lexer)
        block.add(expression)
        if (
            lexer.peekn(1, "end", "keyword")
            or lexer.peekn(1, "catch", "keyword")
            or lexer.peekn(1, "finally", "keyword")
        ):
            break
        lexer.match(";", "interpunction")
        if (
            lexer.peekn(1, "end", "keyword")
            or lexer.peekn(1, "catch", "keyword")
            or lexer.peekn(1, "finally", "keyword")
        ):
            break
    while lexer.matchIf("catch", "keyword"):
        if lexer.matchIf("all", "identifier"):
            err = None
        else:
            err = parse_expression(lexer)
        if lexer.peekn(1, "do", "keyword"):
            expr = parse_block(lexer)
        else:
            expr = parse_statement(lexer)
        if lexer.peekn(1, ";", "interpunction"):
            lexer.eat(1)
        block.addCatch(err, expr)
    if lexer.matchIf("finally", "keyword"):
        while not lexer.peekn(1, "end", "keyword"):
            if lexer.peekn(1, "do", "keyword"):
                expression = parse_block(lexer)
            else:
                expression = parse_statement(lexer)
            block.addFinally(expression)
            if lexer.peekn(1, "end", "keyword"):
                break
            lexer.match(";", "interpunction")
    lexer.match("end", "keyword")
    if (
        len(block.expressions) == 1
        and not block.hasFinally()
        and not block.hasCatch()
    ):
        return block.expressions[0]
    return block


def parse_statement(lexer, toplevel=False):
    if not lexer.hasNext():
        raise CklSyntaxError("Unexpected end of input", lexer.getPos())

    comment = ""
    if lexer.peek().type == "string" and lexer.peekn(2, "def", "keyword"):
        comment = lexer.next().value

    if lexer.matchIf("require", "keyword"):
        pos = lexer.getPos()
        modulespec = parse_expression(lexer)
        unqualified = False
        symbols = None
        name = None
        if lexer.matchIf("unqualified", "identifier"):
            unqualified = True
        elif lexer.matchIf(["import", "["], ["identifier", "interpunction"]):
            symbols = dict()
            while not lexer.peekn(1, "]", "interpunction"):
                symbol = lexer.matchIdentifier()
                symbolname = symbol
                if lexer.matchIf("as", "keyword"):
                    symbolname = lexer.matchIdentifier()
                symbols[symbol] = symbolname
                if not lexer.peekn(1, "]", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.match("]", "interpunction")
        elif lexer.matchIf("as", "keyword"):
            name = lexer.matchIdentifier()
        return NodeRequire(modulespec, name, unqualified, symbols, pos)

    if lexer.matchIf("def", "keyword"):
        pos = lexer.getPos()
        if lexer.matchIf("[", "interpunction"):
            # handle destructuring def
            identifiers = []
            while not lexer.peekn(1, "]", "interpunction"):
                token = lexer.next()
                if token.type == "keyword":
                    raise CklSyntaxError(
                        f"Cannot redefine keyword '{token}'", token.pos
                    )
                if token.type != "identifier":
                    raise CklSyntaxError(
                        f"Expected identifier but got '{token}'", token.pos
                    )
                identifiers.push(token.value)
                if not lexer.peekn(1, "]", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.match("]", "interpunction")
            lexer.match("=", "operator")
            return NodeDefDestructuring(
                identifiers, parse_expression(lexer), comment, pos
            )
        else:
            # handle single var def
            token = lexer.next()
            if token.type == "keyword":
                raise CklSyntaxError(
                    f"Cannot redefine keyword '{token}'", token.pos
                )
            if token.type != "identifier":
                raise CklSyntaxError(
                    f"Expected identifier but got '{token}'", token.pos
                )
            if lexer.peekn(1, "(", "interpunction"):
                return NodeDef(token.value, parse_fn(lexer, pos), comment, pos)
            else:
                lexer.match("=", "operator")
                return NodeDef(
                    token.value, parse_expression(lexer), comment, pos
                )

    if lexer.matchIf("for", "keyword"):
        pos = lexer.getPos()
        identifiers = []
        if lexer.matchIf("[", "interpunction"):
            while not lexer.peekn(1, "]", "interpunction"):
                token = lexer.next()
                if token.type != "identifier":
                    raise CklSyntaxError(
                        f"Expected identifier in "
                        f"for loop but got '{token}'",
                        token.pos,
                    )
                identifiers.push(token.value)
                if not lexer.peekn(1, "]", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.match("]", "interpunction")
        else:
            token = lexer.next()
            if token.type != "identifier":
                raise CklSyntaxError(
                    f"Expected identifier in for loop but got '{token}'",
                    token.pos,
                )
            identifiers.push(token.value)
        lexer.match("in", "keyword")
        what = "values"
        if lexer.matchIf("keys", "identifier"):
            what = "keys"
        elif lexer.matchIf("values", "identifier"):
            what = "values"
        elif lexer.matchIf("entries", "identifier"):
            what = "entries"
        expression = parse_expression(lexer)
        if lexer.peekn(1, "do", "keyword"):
            return NodeFor(
                identifiers, expression, parse_block(lexer), what, pos
            )
        return NodeFor(
            identifiers, expression, parse_expression(lexer), what, pos
        )

    if lexer.matchIf("while", "keyword"):
        pos = lexer.getPos()
        expr = parse_or_expr(lexer)
        block = parse_block(lexer)
        return NodeWhile(expr, block, pos)

    return parse_expression(lexer)


def parse_expression(lexer):
    if lexer.peekn(1, "if", "keyword"):
        result = NodeIf(lexer.getPos())
        while lexer.matchIf("if", "keyword") or lexer.matchIf(
            "elif", "keyword"
        ):
            condition = parse_or_expr(lexer)
            lexer.match("then", "keyword")
            if lexer.peekn(1, "do", "keyword"):
                result.addIf(condition, parse_block(lexer))
            else:
                result.addIf(condition, parse_or_expr(lexer))
        if lexer.matchIf("else", "keyword"):
            if lexer.peekn(1, "do", "keyword"):
                result.setElse(parse_block(lexer))
            else:
                result.setElse(parse_or_expr(lexer))
        return result
    return parse_or_expr(lexer)


def parse_or_expr(lexer):
    expr = parse_and_expr(lexer)
    if lexer.peekn(1, "or", "keyword"):
        result = NodeOr(lexer.getPosNext()).addOrClause(expr)
        while lexer.matchIf("or", "keyword"):
            result.addOrClause(parse_and_expr(lexer))
        return result
    return expr


def parse_and_expr(lexer):
    expr = parse_not_expr(lexer)
    if lexer.peekn(1, "and", "keyword"):
        result = NodeAnd(expr, lexer.getPosNext())
        while lexer.matchIf("and", "keyword"):
            result.addAndClause(parse_not_expr(lexer))
        return result
    return expr


def parse_not_expr(lexer):
    if lexer.matchIf("not", "keyword"):
        pos = lexer.getPos()
        return NodeNot(parse_rel_expr(lexer), pos)
    return parse_rel_expr(lexer)


def parse_rel_expr(lexer):
    expr = parse_add_expr(lexer)
    relops = ["==", "!=", "<>", "<", "<=", ">", ">=", "is"]
    if (
        not lexer.hasNext()
        or lexer.peek().value not in relops
        or lexer.peek().type not in ["operator", "keyword"]
    ):
        return expr
    result = NodeAnd(None, lexer.getPosNext())
    lhs = expr
    while (
        lexer.hasNext()
        and lexer.peek().value in relops
        and lexer.peek().type in ["operator", "keyword"]
    ):
        relop = lexer.next().value
        if relop == "is" and lexer.peek().value == "not":
            relop = "is not"
            lexer.eat(1)
        pos = lexer.getPos()
        rhs = parse_add_expr(lexer)
        cmp = None
        if relop == "<":
            cmp = func_call("less", lhs, rhs, pos)
        elif relop == "<=":
            cmp = func_call("less_equals", lhs, rhs, pos)
        elif relop == ">":
            cmp = func_call("greater", lhs, rhs, pos)
        elif relop == ">=":
            cmp = func_call("greater_equals", lhs, rhs, pos)
        elif relop in ["==", "is"]:
            cmp = func_call("equals", lhs, rhs, pos)
        elif relop in ["<>", "!=", "is not"]:
            cmp = func_call("not_equals", lhs, rhs, pos)
        result.addAndClause(cmp)
        lhs = rhs
    return result.getSimplified()


def parse_add_expr(lexer):
    expr = parse_mul_expr(lexer)
    while lexer.peekOne(1, ["+", "-"], "operator"):
        if lexer.matchIf("+", "operator"):
            pos = lexer.getPos()
            expr = func_call("add", expr, parse_mul_expr(lexer), pos)
        elif lexer.matchIf("-", "operator"):
            pos = lexer.getPos()
            expr = func_call("sub", expr, parse_mul_expr(lexer), pos)
    return expr


def parse_mul_expr(lexer):
    expr = parse_unary_expr(lexer)
    while lexer.peekOne(1, ["*", "/", "%"], "operator"):
        if lexer.matchIf("*", "operator"):
            pos = lexer.getPos()
            expr = func_call("mul", expr, parse_unary_expr(lexer), pos)
        elif lexer.matchIf("/", "operator"):
            pos = lexer.getPos()
            expr = func_call("div", expr, parse_unary_expr(lexer), pos)
        elif lexer.matchIf("%", "operator"):
            pos = lexer.getPos()
            expr = func_call("mod", expr, parse_unary_expr(lexer), pos)
    return expr


def parse_unary_expr(lexer):
    if lexer.matchIf("+", "operator"):
        return parse_pred_expr(lexer)
    if lexer.matchIf("-", "operator"):
        pos = lexer.getPos()
        token = lexer.peek()
        if token.type == "int":
            return parse_pred_expr(lexer, True)
        elif token.type == "decimal":
            return parse_pred_expr(lexer, True)
        else:
            call = NodeFuncall(NodeIdentifier("sub", pos), pos)
            call.addArg("a", NodeLiteral(ValueInt(0), pos))
            call.addArg("b", parse_pred_expr(lexer))
            return call
    return parse_pred_expr(lexer)


def parse_pred_expr(lexer, unary_minus=False):
    expr = parse_primary_expr(lexer, unary_minus)
    pos = lexer.getPosNext()

    if lexer.matchIf("is", "keyword"):
        if lexer.matchIf("not", "keyword"):
            if lexer.matchIf("in"):
                return NodeNot(NodeIn(expr, parse_primary_expr(lexer), pos), pos)
            elif lexer.matchIf("empty", "identifier"):
                return NodeNot(func_call("is_empty", expr, None, pos), pos)
            elif lexer.matchIf("zero", "identifier"):
                return NodeNot(func_call("is_zero", expr, None, pos), pos)
            elif lexer.matchIf("negative", "identifier"):
                return NodeNot(func_call("is_negative", expr, None, pos), pos)
            elif lexer.matchIf("numerical", "identifier"):
                return NodeNot(
                    collect_predicate_min_max_exact(
                        "is_numerical",
                        func_call("string", expr, None, pos),
                        lexer,
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("alphanumerical", "identifier"):
                return NodeNot(
                    collect_predicate_min_max_exact(
                        "is_alphanumerical",
                        func_call("string", expr, None, pos),
                        lexer,
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf(
                ["date", "with", "hour"],
                ["identifier", "identifier", "identifier"],
            ):
                return NodeNot(
                    func_call2(
                        "is_valid_date",
                        "str",
                        func_call("string", expr, None, pos),
                        "fmt",
                        NodeLiteral(ValueString("yyyyMMddHH"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("date", "identifier"):
                return NodeNot(
                    func_call2(
                        "is_valid_date",
                        "str",
                        func_call("string", expr, None, pos),
                        "fmt",
                        NodeLiteral(ValueString("yyyyMMdd"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("time", "identifier"):
                return NodeNot(
                    func_call2(
                        "is_valid_time",
                        "str",
                        func_call("string", expr, None, pos),
                        "fmt",
                        NodeLiteral(ValueString("HHmm"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("string", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("string"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("int", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("int"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("decimal", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("decimal"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("boolean", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("boolean"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("pattern", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("pattern"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("date", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("date"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("None", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("None"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("func", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("func"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("input", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("input"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("output", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("output"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("list", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("lsit"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("set", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("set"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("map", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("map"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("object", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("object"), pos),
                        pos,
                    ),
                    pos,
                )
            elif lexer.matchIf("node", "identifier"):
                return NodeNot(
                    func_call(
                        "equals",
                        func_call("type", expr, None, pos),
                        NodeLiteral(ValueString("node"), pos),
                        pos,
                    ),
                    pos,
                )
            else:
                lexer.previous()  # not
                lexer.previous()  # is
                return expr
        elif lexer.matchIf("in", "keyword"):
            return NodeIn(expr, parse_primary_expr(lexer), pos)
        elif lexer.matchIf("empty", "identifier"):
            return func_call("is_empty", expr, None, pos)
        elif lexer.matchIf("zero", "identifier"):
            return func_call("is_zero", expr, None, pos)
        elif lexer.matchIf("negative", "identifier"):
            return func_call("is_negative", expr, None, pos)
        elif lexer.matchIf("numerical", "identifier"):
            return collect_predicate_min_max_exact(
                "is_numerical",
                func_call("string", expr, None, pos),
                lexer,
                pos,
            )
        elif lexer.matchIf("alphanumerical", "identifier"):
            return collect_predicate_min_max_exact(
                "is_alphanumerical",
                func_call("string", expr, None, pos),
                lexer,
                pos,
            )
        elif lexer.matchIf(
            ["date", "with", "hour"],
            ["identifier", "identifier", "identifier"],
        ):
            return func_call2(
                "is_valid_date",
                "str",
                func_call("string", expr, None, pos),
                "fmt",
                NodeLiteral(ValueString("yyyyMMddHH"), pos),
                pos,
            )
        elif lexer.matchIf("date", "identifier"):
            return func_call2(
                "is_valid_date",
                "str",
                func_call("string", expr, None, pos),
                "fmt",
                NodeLiteral(ValueString("yyyyMMdd"), pos),
                pos,
            )
        elif lexer.matchIf("time", "identifier"):
            return func_call2(
                "is_valid_time",
                "str",
                func_call("string", expr, None, pos),
                "fmt",
                NodeLiteral(ValueString("HHmm"), pos),
                pos,
            )
        elif lexer.matchIf("string", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("string"), pos),
                pos,
            )
        elif lexer.matchIf("int", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("int"), pos),
                pos,
            )
        elif lexer.matchIf("decimal", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("decimal"), pos),
                pos,
            )
        elif lexer.matchIf("boolean", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("boolean"), pos),
                pos,
            )
        elif lexer.matchIf("pattern", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("pattern"), pos),
                pos,
            )
        elif lexer.matchIf("date", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("date"), pos),
                pos,
            )
        elif lexer.matchIf("None", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("None"), pos),
                pos,
            )
        elif lexer.matchIf("func", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("func"), pos),
                pos,
            )
        elif lexer.matchIf("input", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("input"), pos),
                pos,
            )
        elif lexer.matchIf("output", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("output"), pos),
                pos,
            )
        elif lexer.matchIf("list", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("list"), pos),
                pos,
            )
        elif lexer.matchIf("set", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("set"), pos),
                pos,
            )
        elif lexer.matchIf("map", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("map"), pos),
                pos,
            )
        elif lexer.matchIf("object", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("object"), pos),
                pos,
            )
        elif lexer.matchIf("node", "identifier"):
            return func_call(
                "equals",
                func_call("type", expr, None, pos),
                NodeLiteral(ValueString("node"), pos),
                pos,
            )
        lexer.previous()  # is
        return expr
    elif lexer.matchIf(["not", "in"], "keyword"):
        return NodeNot(NodeIn(expr, parse_primary_expr(lexer), pos), pos)
    elif lexer.matchIf("in", "keyword"):
        return NodeIn(expr, parse_primary_expr(lexer), pos)
    elif lexer.matchIf(
        ["starts", "not", "with"], ["identifier", "keyword", "identifier"]
    ):
        return NodeNot(
            func_call2(
                "starts_with",
                "str",
                expr,
                "part",
                parse_primary_expr(lexer),
                pos,
            ),
            pos,
        )
    elif lexer.matchIf(["starts", "with"], ["identifier", "identifier"]):
        return func_call2(
            "starts_with",
            "str",
            expr,
            "part",
            parse_primary_expr(lexer),
            pos,
        )
    elif lexer.matchIf(
        ["ends", "not", "with"], ["identifier", "keyword", "identifier"]
    ):
        return NodeNot(
            func_call2(
                "ends_with",
                "str",
                expr,
                "part",
                parse_primary_expr(lexer),
                pos,
            ),
            pos,
        )
    elif lexer.matchIf(["ends", "with"], ["identifier", "identifier"]):
        return func_call2(
            "ends_with",
            "str",
            expr,
            "part",
            parse_primary_expr(lexer),
            pos,
        )
    elif lexer.matchIf(["contains", "not"], ["identifier", "keyword"]):
        return NodeNot(
            func_call2(
                "contains",
                "obj",
                expr,
                "part",
                parse_primary_expr(lexer),
                pos,
            ),
            pos,
        )
    elif lexer.matchIf("contains", "identifier"):
        return func_call2(
            "contains",
            "obj",
            expr,
            "part",
            parse_primary_expr(lexer),
            pos,
        )
    elif lexer.matchIf(["matches", "not"], ["identifier", "keyword"]):
        return NodeNot(
            func_call2(
                "matches",
                "str",
                expr,
                "pattern",
                parse_primary_expr(lexer),
                pos,
            ),
            pos,
        )
    elif lexer.matchIf("matches", "identifier"):
        return func_call2(
            "matches",
            "str",
            expr,
            "pattern",
            parse_primary_expr(lexer),
            pos,
        )
    return expr


def collect_predicate_min_max_exact(fn, expr, lexer, pos):
    min_len = NodeLiteral(ValueInt(0), pos)
    max_len = NodeLiteral(ValueInt(9999), pos)
    if lexer.matchIf("min_len", "identifier"):
        min_len = parse_primary_expr(lexer)
    if lexer.matchIf("max_len", "identifier"):
        max_len = parse_primary_expr(lexer)
    if lexer.matchIf("exact_len", "identifier"):
        min_len = max_len = parse_primary_expr(lexer)
    return func_call3(fn, "str", expr, "min", min_len, "max", max_len, pos)


def parse_primary_expr(lexer, unary_minus=False):
    if not lexer.hasNext():
        raise CklSyntaxError("Unexpected end of input", lexer.getPos())

    token = lexer.next()
    if token.value == "(" and token.type == "interpunction":
        result = parse_bare_block(lexer, False)
        lexer.match(")", "interpunction")
        return deref_or_call_or_invoke(lexer, result)

    if token.type == "identifier":
        result = NodeIdentifier(token.value, token.pos)
        if lexer.matchIf("=", "operator"):
            result = NodeAssign(token.value, parse_expression(lexer), token.pos)
        elif lexer.matchIf("+=", "operator"):
            value = parse_expression(lexer)
            result = NodeAssign(
                token.value,
                func_call("add", result, value, token.pos),
                token.pos,
            )
        elif lexer.matchIf("-=", "operator"):
            value = parse_expression(lexer)
            result = NodeAssign(
                token.value,
                func_call("sub", result, value, token.pos),
                token.pos,
            )
        elif lexer.matchIf("*=", "operator"):
            value = parse_expression(lexer)
            result = NodeAssign(
                token.value,
                func_call("mul", result, value, token.pos),
                token.pos,
            )
        elif lexer.matchIf("/=", "operator"):
            value = parse_expression(lexer)
            result = NodeAssign(
                token.value,
                func_call("div", result, value, token.pos),
                token.pos,
            )
        elif lexer.matchIf("%=", "operator"):
            value = parse_expression(lexer)
            result = NodeAssign(
                token.value,
                func_call("mod", result, value, token.pos),
                token.pos,
            )
        else:
            result = deref_or_call_or_invoke(lexer, result)
    elif token.type == "string":
        result = NodeLiteral(ValueString(token.value), token.pos)
        result = deref_or_invoke(lexer, result)
    elif token.type == "int":
        result = NodeLiteral(
            ValueInt(int(token.value) * (-1 if unary_minus else 1)),
            token.pos,
        )
        result = invoke(lexer, result)
    elif token.type == "decimal":
        result = NodeLiteral(
            ValueDecimal(float(token.value) * (-1 if unary_minus else 1)),
            token.pos,
        )
        result = invoke(lexer, result)
    elif token.type == "boolean":
        result = NodeLiteral(
            ValueBoolean.fromval(token.value == "TRUE"), token.pos
        )
        result = invoke(lexer, result)
    elif token.type == "pattern":
        result = NodeLiteral(ValuePattern(token.value[2, -2]), token.pos)
        result = invoke(lexer, result)
    else:
        if token.value == "fn" and token.type == "keyword":
            result = parse_fn(lexer, token.pos)
        elif token.value == "break" and token.type == "keyword":
            result = NodeBreak(token.pos)
        elif token.value == "continue" and token.type == "keyword":
            result = NodeContinue(token.pos)
        elif token.value == "return" and token.type == "keyword":
            if lexer.peekn(1, ";", "interpunction"):
                result = NodeReturn(None, token.pos)
            else:
                result = NodeReturn(parse_expression(lexer), token.pos)
        elif token.value == "error" and token.type == "keyword":
            result = NodeError(parse_expression(lexer), token.pos)
        elif token.value == "do" and token.type == "keyword":
            lexer.previous()
            result = parse_block(lexer)
        elif token.value == "[" and token.type == "interpunction":
            result = parse_list_literal(lexer, token)
            if lexer.peekn(1, "=", "operator"):
                identifiers = []
                for item in result.items:
                    if not isinstance(item, NodeIdentifier):
                        raise CklSyntaxError(
                            f"Destructuring assign expected "
                            f"identifier but got {item}",
                            token.pos,
                        )
                    identifiers.push(item.value)
                lexer.match("=", "operator")
                result = NodeAssignDestructuring(
                    identifiers, parse_expression(lexer), token.pos
                )
        elif token.value == "<<" and token.type == "interpunction":
            result = parse_set_literal(lexer, token)
        elif token.value == "<<<" and token.type == "interpunction":
            result = parse_map_literal(lexer, token)
        elif token.value == "<*" and token.type == "interpunction":
            result = parse_object_literal(lexer, token)
        elif token.value == "..." and token.type == "interpunction":
            token = lexer.next()
            if token.value == "[" and token.type == "interpunction":
                result = parse_list_literal(lexer, token)
            elif token.value == "<<<" and token.type == "interpunction":
                result = parse_map_literal(lexer, token)
            elif token.type == "identifier":
                result = NodeIdentifier(token.value, token.pos)
            else:
                raise CklSyntaxError(
                    "Spread operator only allowed with "
                    "identifiers, list and map literals",
                    token.pos,
                )
            result = NodeSpread(result, token.pos)
        else:
            raise CklSyntaxError(f"Invalid syntax at '{token}'", token.pos)
    return result


def parse_list_literal(lexer, token):
    if lexer.matchIf("]", "interpunction"):
        return deref_or_invoke(lexer, NodeList(token.pos))
    else:
        expr = parse_expression(lexer)
        if lexer.matchIf("for", "keyword"):
            identifier = lexer.matchIdentifier()
            lexer.match("in", "keyword")
            what = None
            if lexer.matchIf("keys", "identifier"):
                what = "keys"
            elif lexer.matchIf("values", "identifier"):
                what = "values"
            elif lexer.matchIf("entries", "identifier"):
                what = "entries"
            listExpr = parse_or_expr(lexer)
            if lexer.matchIf("for", "keyword"):
                identifier2 = lexer.matchIdentifier()
                lexer.match("in", "keyword")
                what2 = None
                if lexer.matchIf("keys", "identifier"):
                    what2 = "keys"
                elif lexer.matchIf("values", "identifier"):
                    what2 = "values"
                elif lexer.matchIf("entries", "identifier"):
                    what2 = "entries"
                listExpr2 = parse_or_expr(lexer)
                comprehension = NodeListComprehensionProduct(
                    expr,
                    identifier,
                    listExpr,
                    what,
                    identifier2,
                    listExpr2,
                    what2,
                    token.pos,
                )
                if lexer.matchIf("if", "keyword"):
                    comprehension.setCondition(parse_or_expr(lexer))
                lexer.match("]", "interpunction")
                return deref_or_invoke(lexer, comprehension)
            elif lexer.matchIf(["also", "for"], "keyword"):
                identifier2 = lexer.matchIdentifier()
                lexer.match("in", "keyword")
                what2 = None
                if lexer.matchIf("keys", "identifier"):
                    what2 = "keys"
                elif lexer.matchIf("values", "identifier"):
                    what2 = "values"
                elif lexer.matchIf("entries", "identifier"):
                    what2 = "entries"
                listExpr2 = parse_or_expr(lexer)
                comprehension = NodeListComprehensionParallel(
                    expr,
                    identifier,
                    listExpr,
                    what,
                    identifier2,
                    listExpr2,
                    what2,
                    token.pos,
                )
                if lexer.matchIf("if", "keyword"):
                    comprehension.setCondition(parse_or_expr(lexer))
                lexer.match("]", "interpunction")
                return deref_or_invoke(lexer, comprehension)
            else:
                comprehension = NodeListComprehension(
                    expr, identifier, listExpr, what, token.pos
                )
                if lexer.matchIf("if", "keyword"):
                    comprehension.setCondition(parse_or_expr(lexer))
                lexer.match("]", "interpunction")
                return deref_or_invoke(lexer, comprehension)
        else:
            lst = NodeList(token.pos)
            while not lexer.peekn(1, "]", "interpunction"):
                lst.addItem(expr)
                expr = None
                if not lexer.peekn(1, "]", "interpunction"):
                    lexer.match(",", "interpunction")
                    if not lexer.peekn(1, "]", "interpunction"):
                        expr = parse_expression(lexer)
            if expr:
                lst.addItem(expr)
            lexer.match("]", "interpunction")
            return deref_or_invoke(lexer, lst)


def parse_set_literal(lexer, token):
    if lexer.matchIf(">>", "interpunction"):
        return deref_or_invoke(lexer, NodeSet(token.pos))
    else:
        expr = parse_expression(lexer)
        if lexer.matchIf("for", "keyword"):
            identifier = lexer.matchIdentifier()
            lexer.match("in", "keyword")
            what = None
            if lexer.matchIf("keys", "identifier"):
                what = "keys"
            elif lexer.matchIf("values", "identifier"):
                what = "values"
            elif lexer.matchIf("entries", "identifier"):
                what = "entries"
            listExpr = parse_or_expr(lexer)
            if lexer.matchIf("for", "keyword"):
                identifier2 = lexer.matchIdentifier()
                lexer.match("in", "keyword")
                what2 = None
                if lexer.matchIf("keys", "identifier"):
                    what2 = "keys"
                elif lexer.matchIf("values", "identifier"):
                    what2 = "values"
                elif lexer.matchIf("entries", "identifier"):
                    what2 = "entries"
                listExpr2 = parse_or_expr(lexer)
                comprehension = NodeSetComprehensionProduct(
                    expr,
                    identifier,
                    listExpr,
                    what,
                    identifier2,
                    listExpr2,
                    what2,
                    token.pos,
                )
                if lexer.matchIf("if", "keyword"):
                    comprehension.setCondition(parse_or_expr(lexer))
                lexer.match(">>", "interpunction")
                return deref_or_invoke(lexer, comprehension)
            elif lexer.matchIf(["also", "for"], "keyword"):
                identifier2 = lexer.matchIdentifier()
                lexer.match("in", "keyword")
                what2 = None
                if lexer.matchIf("keys", "identifier"):
                    what2 = "keys"
                elif lexer.matchIf("values", "identifier"):
                    what2 = "values"
                elif lexer.matchIf("entries", "identifier"):
                    what2 = "entries"
                listExpr2 = parse_or_expr(lexer)
                comprehension = NodeSetComprehensionParallel(
                    expr,
                    identifier,
                    listExpr,
                    what,
                    identifier2,
                    listExpr2,
                    what2,
                    token.pos,
                )
                if lexer.matchIf("if", "keyword"):
                    comprehension.setCondition(parse_or_expr(lexer))
                lexer.match(">>", "interpunction")
                return deref_or_invoke(lexer, comprehension)
            else:
                comprehension = NodeSetComprehension(
                    expr, identifier, listExpr, what, token.pos
                )
                if lexer.matchIf("if", "keyword"):
                    comprehension.setCondition(parse_or_expr(lexer))
                lexer.match(">>", "interpunction")
                return deref_or_invoke(lexer, comprehension)
        else:
            s = NodeSet(token.pos)
            s.addItem(expr)
            if not lexer.peekn(1, ">>", "interpunction"):
                lexer.match(",", "interpunction")
            while not lexer.peekn(1, ">>", "interpunction"):
                s.addItem(parse_expression(lexer))
                if not lexer.peekn(1, ">>", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.match(">>", "interpunction")
            return deref_or_invoke(lexer, s)


def parse_map_literal(lexer, token):
    if lexer.matchIf(">>>", "interpunction"):
        return deref_or_invoke(lexer, NodeMap(token.pos))
    else:
        key = parse_expression(lexer)
        lexer.match("=>", "interpunction")
        value = parse_expression(lexer)
        if lexer.matchIf("for", "keyword"):
            identifier = lexer.matchIdentifier()
            lexer.match("in", "keyword")
            what = None
            if lexer.matchIf("keys", "identifier"):
                what = "keys"
            elif lexer.matchIf("values", "identifier"):
                what = "values"
            elif lexer.matchIf("entries", "identifier"):
                what = "entries"
            listExpr = parse_or_expr(lexer)
            comprehension = NodeMapComprehension(
                key, value, identifier, listExpr, what, token.pos
            )
            if lexer.matchIf("if", "keyword"):
                comprehension.setCondition(parse_or_expr(lexer))
            lexer.match(">>>", "interpunction")
            return deref_or_invoke(lexer, comprehension)
        else:
            m = NodeMap(token.pos)
            if isinstance(key, NodeIdentifier):
                key = NodeLiteral(ValueString(key.value), key.pos)
            m.addKeyValue(key, value)
            if not lexer.peekn(1, ">>>", "interpunction"):
                lexer.match(",", "interpunction")
            while not lexer.peekn(1, ">>>", "interpunction"):
                key = parse_expression(lexer)
                if isinstance(key, NodeIdentifier):
                    key = NodeLiteral(ValueString(key.value), key.pos)
                lexer.match("=>", "interpunction")
                value = parse_expression(lexer)
                m.addKeyValue(key, value)
                if not lexer.peekn(1, ">>>", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.match(">>>", "interpunction")
            return deref_or_invoke(lexer, m)


def parse_object_literal(lexer, token):
    obj = NodeObject(token.pos)
    while not lexer.peekn(1, "*>", "interpunction"):
        key = lexer.matchIdentifier()
        if lexer.peekn(1, "(", "interpunction"):
            fn = parse_fn(lexer, lexer.getPos())
            obj.addKeyValue(key, fn)
        else:
            lexer.match("=", "operator")
            value = parse_expression(lexer)
            obj.addKeyValue(key, value)
        if not lexer.peekn(1, "*>", "interpunction"):
            lexer.match(",", "interpunction")
    lexer.match("*>", "interpunction")
    return deref_or_invoke(lexer, obj)


def parse_fn(lexer, pos):
    fn = NodeLambda(pos)
    lexer.match("(", "interpunction")
    while not lexer.matchIf(")", "interpunction"):
        token = lexer.next()
        if token.type == "keyword":
            raise CklSyntaxError(
                f"Cannot use keyword '{token}' as parameter name",
                token.pos,
            )
        if token.type != "identifier":
            raise CklSyntaxError(
                f"Expected parameter name but got '{token}'", token.pos
            )
        argname = token.value
        defvalue = None
        if lexer.matchIf("=", "operator"):
            defvalue = parse_expression(lexer)
        fn.addArg(argname, defvalue)
        if argname.endswith("...") and not lexer.peekn(
            1, ")", "interpunction"
        ):
            raise CklSyntaxError(
                f"Rest argument {argname} must be last argument", token.pos
            )
        if not lexer.peekn(1, ")", "interpunction"):
            lexer.match(",", "interpunction")
    if lexer.peekn(1, "do", "keyword"):
        fn.setBody(parse_block(lexer))
    else:
        fn.setBody(parse_expression(lexer))
    return fn


def _invoke(lexer, node):
    if lexer.matchIf("!>", "operator"):
        fn = None
        if lexer.matchIf(["(", "fn"], ["interpunction", "keyword"]):
            fn = parse_fn(lexer, lexer.getPos())
            lexer.match(")", "interpunction")
        else:
            fn = NodeIdentifier(lexer.matchIdentifier(), lexer.getPos())
            while lexer.matchIf("->", "operator"):
                fn = NodeDeref(
                    fn,
                    NodeLiteral(
                        ValueString(lexer.matchIdentifier()),
                        lexer.getPos(),
                    ),
                    None,
                    lexer.getPos(),
                )
        call = NodeFuncall(fn, lexer.getPos())
        call.addArg(None, node)
        lexer.match("(", "interpunction")
        while not lexer.peekn(1, ")", "interpunction"):
            if lexer.peek().type == "identifier" and lexer.peekn(
                2, "=", "operator"
            ):
                name = lexer.matchIdentifier()
                lexer.match("=", "operator")
                call.addArg(name, parse_expression(lexer))
            else:
                call.addArg(None, parse_expression(lexer))
            if not lexer.peekn(1, ")", "interpunction"):
                lexer.match(",", "interpunction")
        lexer.eat(1)
        node = call
    return node


def _call(lexer, node):
    if lexer.matchIf("(", "interpunction"):
        call = NodeFuncall(node, lexer.getPos())
        while not lexer.peekn(1, ")", "interpunction"):
            if lexer.peek().type == "identifier" and lexer.peekn(
                2, "=", "operator"
            ):
                name = lexer.matchIdentifier()
                lexer.match("=", "operator")
                call.addArg(name, parse_expression(lexer))
            else:
                call.addArg(None, parse_expression(lexer))
            if not lexer.peekn(1, ")", "interpunction"):
                lexer.match(",", "interpunction")
        lexer.eat(1)
        node = call
    return node


def _deref(lexer, node):
    interrupt = False
    if lexer.matchIf("->", "operator"):
        pos = lexer.getPos()
        identifier = lexer.matchIdentifier()
        index = NodeLiteral(ValueString(identifier), pos)
        if lexer.matchIf("=", "operator"):
            value = parse_expression(lexer)
            node = NodeDerefAssign(node, index, value, pos)
            interrupt = True
        elif lexer.matchIf("(", "interpunction"):
            node = NodeDerefInvoke(node, identifier, pos)
            while not lexer.peekn(1, ")", "interpunction"):
                if lexer.peek().type == "identifier" and lexer.peekn(
                    2, "=", "operator"
                ):
                    name = lexer.matchIdentifier()
                    lexer.match("=", "operator")
                    node.addArg(name, parse_expression(lexer))
                else:
                    node.addArg(None, parse_expression(lexer))
                if not lexer.peekn(1, ")", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.eat(1)
        elif lexer.matchIf("+=", "operator"):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call("add", NodeDeref(node, index, None, pos), value, pos),
                pos,
            )
            interrupt = True
        elif lexer.matchIf("-=", "operator"):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call("sub", NodeDeref(node, index, None, pos), value, pos),
                pos,
            )
            interrupt = True
        elif lexer.matchIf("*=", "operator"):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call("mul", NodeDeref(node, index, None, pos), value, pos),
                pos,
            )
            interrupt = True
        elif lexer.matchIf("/=", "operator"):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call("div", NodeDeref(node, index, None, pos), value, pos),
                pos,
            )
            interrupt = True
        elif lexer.matchIf("%=", "operator"):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call("mod", NodeDeref(node, index, None, pos), value, pos),
                pos,
            )
            interrupt = True
        else:
            node = NodeDeref(node, index, None, pos)
    elif lexer.matchIf("[", "interpunction"):
        pos = lexer.getPos()
        index = parse_expression(lexer)
        default_value = None
        if lexer.matchIf(",", "interpunction"):
            default_value = parse_expression(lexer)
        if lexer.matchIf(["]", "="], ["interpunction", "operator"]):
            value = parse_expression(lexer)
            node = NodeDerefAssign(node, index, value, pos)
            interrupt = True
        elif lexer.matchIf(["]", "+="], ["interpunction", "operator"]):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call(
                    "add",
                    NodeDeref(node, index, default_value, pos),
                    value,
                    pos,
                ),
                pos,
            )
            interrupt = True
        elif lexer.matchIf(["]", "-="], ["interpunction", "operator"]):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call(
                    "sub",
                    NodeDeref(node, index, default_value, pos),
                    value,
                    pos,
                ),
                pos,
            )
            interrupt = True
        elif lexer.matchIf(["]", "*="], ["interpunction", "operator"]):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call(
                    "mul",
                    NodeDeref(node, index, default_value, pos),
                    value,
                    pos,
                ),
                pos,
            )
            interrupt = True
        elif lexer.matchIf(["]", "/="], ["interpunction", "operator"]):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call(
                    "div",
                    NodeDeref(node, index, default_value, pos),
                    value,
                    pos,
                ),
                pos,
            )
            interrupt = True
        elif lexer.matchIf(["]", "%="], ["interpunction", "operator"]):
            value = parse_expression(lexer)
            node = NodeDerefAssign(
                node,
                index,
                func_call(
                    "mod",
                    NodeDeref(node, index, default_value, pos),
                    value,
                    pos,
                ),
                pos,
            )
            interrupt = True
        else:
            node = NodeDeref(node, index, default_value, pos)
            lexer.match("]", "interpunction")
    return [node, interrupt]


def deref_or_call_or_invoke(lexer, node):
    while (
        lexer.peekn(1, "!>", "operator")
        or lexer.peekn(1, "[", "interpunction")
        or lexer.peekn(1, "(", "interpunction")
        or lexer.peekn(1, "->", "operator")
    ):
        if lexer.peekn(1, "!>", "operator"):
            node = _invoke(lexer, node)
        elif lexer.peekn(1, "(", "interpunction"):
            node = _call(lexer, node)
        elif lexer.peekn(1, "[", "interpunction") or lexer.peekn(
            1, "->", "operator"
        ):
            result = _deref(lexer, node)
            node = result[0]
            if result[1]:
                break
    return node


def deref_or_invoke(lexer, node):
    while (
        lexer.peekn(1, "!>", "operator")
        or lexer.peekn(1, "[", "interpunction")
        or lexer.peekn(1, "->", "operator")
    ):
        if lexer.peekn(1, "!>", "operator"):
            node = _invoke(lexer, node)
        elif lexer.peekn(1, "[", "interpunction") or lexer.peekn(
            1, "->", "operator"
        ):
            result = _deref(lexer, node)
            node = result[0]
            if result[1]:
                break
    return node


def invoke(lexer, node):
    while lexer.peekn(1, "!>", "operator"):
        node = _invoke(lexer, node)
    return node


def func_call(fn, exprA, exprB, pos):
    result = NodeFuncall(NodeIdentifier(fn, pos), pos)
    if exprB:
        return func_call2(fn, "a", exprA, "b", exprB, pos)
    else:
        return func_call1(fn, "obj", exprA, pos)
    return result


def func_call1(fn, a, exprA, pos):
    result = NodeFuncall(NodeIdentifier(fn, pos), pos)
    result.addArg(a, exprA)
    return result


def func_call2(fn, a, exprA, b, exprB, pos):
    result = NodeFuncall(NodeIdentifier(fn, pos), pos)
    result.addArg(a, exprA)
    result.addArg(b, exprB)
    return result


def func_call3(fn, a, exprA, b, exprB, c, exprC, pos):
    result = NodeFuncall(NodeIdentifier(fn, pos), pos)
    result.addArg(a, exprA)
    result.addArg(b, exprB)
    result.addArg(c, exprC)
    return result
