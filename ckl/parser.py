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


class Parser:
    @classmethod
    def parseScript(cls, script, filename):
        return Parser().parse(Lexer(script, filename).scan())

    def parse(self, lexer):
        if not lexer.hasNext():
            return NodeNull(SourcePos(lexer.name, 1, 1))
        result = self.parseBareBlock(lexer, True)
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

    def parseBareBlock(self, lexer, toplevel=False):
        block = NodeBlock(lexer.getPosNext(), toplevel)
        if lexer.peekn(1, "do", "keyword"):
            expression = self.parseBlock(lexer)
        else:
            expression = self.parseStatement(lexer, toplevel)
        if not lexer.hasNext():
            return expression
        block.add(expression)
        while lexer.matchIf(";", "interpunction"):
            if not lexer.hasNext():
                break
            if lexer.peekn(1, "do", "keyword"):
                expression = self.parseBlock(lexer)
            else:
                expression = self.parseStatement(lexer, toplevel)
            block.add(expression)
        if (
            len(block.expressions) == 1
            and not block.hasFinally()
            and not block.hasCatch()
        ):
            return block.expressions[0]
        return block

    def parseBlock(self, lexer):
        block = NodeBlock(lexer.getPosNext())
        lexer.match("do", "keyword")
        while (
            not lexer.peekn(1, "end", "keyword")
            and not lexer.peekn(1, "catch", "keyword")
            and not lexer.peekn(1, "finally", "keyword")
        ):
            if lexer.peekn(1, "do", "keyword"):
                expression = self.parseBlock(lexer)
            else:
                expression = self.parseStatement(lexer)
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
                err = self.parseExpression(lexer)
            if lexer.peekn(1, "do", "keyword"):
                expr = self.parseBlock(lexer)
            else:
                expr = self.parseStatement(lexer)
            if lexer.peekn(1, ";", "interpunction"):
                lexer.eat(1)
            block.addCatch(err, expr)
        if lexer.matchIf("finally", "keyword"):
            while not lexer.peekn(1, "end", "keyword"):
                if lexer.peekn(1, "do", "keyword"):
                    expression = self.parseBlock(lexer)
                else:
                    expression = self.parseStatement(lexer)
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

    def parseStatement(self, lexer, toplevel=False):
        if not lexer.hasNext():
            raise CklSyntaxError("Unexpected end of input", lexer.getPos())

        comment = ""
        if lexer.peek().type == "string" and lexer.peekn(2, "def", "keyword"):
            comment = lexer.next().value

        if lexer.matchIf("require", "keyword"):
            pos = lexer.getPos()
            modulespec = self.parseExpression(lexer)
            unqualified = False
            symbols = None
            name = None
            if lexer.matchIf("unqualified", "identifier"):
                unqualified = True
            elif lexer.matchIf(
                ["import", "["], ["identifier", "interpunction"]
            ):
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
                    identifiers, self.parseExpression(lexer), comment, pos
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
                    return NodeDef(
                        token.value, self.parseFn(lexer, pos), comment, pos
                    )
                else:
                    lexer.match("=", "operator")
                    return NodeDef(
                        token.value, self.parseExpression(lexer), comment, pos
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
            expression = self.parseExpression(lexer)
            if lexer.peekn(1, "do", "keyword"):
                return NodeFor(
                    identifiers, expression, self.parseBlock(lexer), what, pos
                )
            return NodeFor(
                identifiers, expression, self.parseExpression(lexer), what, pos
            )

        if lexer.matchIf("while", "keyword"):
            pos = lexer.getPos()
            expr = self.parseOrExpr(lexer)
            block = self.parseBlock(lexer)
            return NodeWhile(expr, block, pos)

        return self.parseExpression(lexer)

    def parseExpression(self, lexer):
        if lexer.peekn(1, "if", "keyword"):
            result = NodeIf(lexer.getPos())
            while lexer.matchIf("if", "keyword") or lexer.matchIf(
                "elif", "keyword"
            ):
                condition = self.parseOrExpr(lexer)
                lexer.match("then", "keyword")
                if lexer.peekn(1, "do", "keyword"):
                    result.addIf(condition, self.parseBlock(lexer))
                else:
                    result.addIf(condition, self.parseOrExpr(lexer))
            if lexer.matchIf("else", "keyword"):
                if lexer.peekn(1, "do", "keyword"):
                    result.setElse(self.parseBlock(lexer))
                else:
                    result.setElse(self.parseOrExpr(lexer))
            return result
        return self.parseOrExpr(lexer)

    def parseOrExpr(self, lexer):
        expr = self.parseAndExpr(lexer)
        if lexer.peekn(1, "or", "keyword"):
            result = NodeOr(lexer.getPosNext()).addOrClause(expr)
            while lexer.matchIf("or", "keyword"):
                result.addOrClause(self.parseAndExpr(lexer))
            return result
        return expr

    def parseAndExpr(self, lexer):
        expr = self.parseNotExpr(lexer)
        if lexer.peekn(1, "and", "keyword"):
            result = NodeAnd(expr, lexer.getPosNext())
            while lexer.matchIf("and", "keyword"):
                result.addAndClause(self.parseNotExpr(lexer))
            return result
        return expr

    def parseNotExpr(self, lexer):
        if lexer.matchIf("not", "keyword"):
            pos = lexer.getPos()
            return NodeNot(self.parseRelExpr(lexer), pos)
        return self.parseRelExpr(lexer)

    def parseRelExpr(self, lexer):
        expr = self.parseAddExpr(lexer)
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
            rhs = self.parseAddExpr(lexer)
            cmp = None
            if relop == "<":
                cmp = self.funcCall("less", lhs, rhs, pos)
            elif relop == "<=":
                cmp = self.funcCall("less_equals", lhs, rhs, pos)
            elif relop == ">":
                cmp = self.funcCall("greater", lhs, rhs, pos)
            elif relop == ">=":
                cmp = self.funcCall("greater_equals", lhs, rhs, pos)
            elif relop in ["==", "is"]:
                cmp = self.funcCall("equals", lhs, rhs, pos)
            elif relop in ["<>", "!=", "is not"]:
                cmp = self.funcCall("not_equals", lhs, rhs, pos)
            result.addAndClause(cmp)
            lhs = rhs
        return result.getSimplified()

    def parseAddExpr(self, lexer):
        expr = self.parseMulExpr(lexer)
        while lexer.peekOne(1, ["+", "-"], "operator"):
            if lexer.matchIf("+", "operator"):
                pos = lexer.getPos()
                expr = self.funcCall(
                    "add", expr, self.parseMulExpr(lexer), pos
                )
            elif lexer.matchIf("-", "operator"):
                pos = lexer.getPos()
                expr = self.funcCall(
                    "sub", expr, self.parseMulExpr(lexer), pos
                )
        return expr

    def parseMulExpr(self, lexer):
        expr = self.parseUnaryExpr(lexer)
        while lexer.peekOne(1, ["*", "/", "%"], "operator"):
            if lexer.matchIf("*", "operator"):
                pos = lexer.getPos()
                expr = self.funcCall(
                    "mul", expr, self.parseUnaryExpr(lexer), pos
                )
            elif lexer.matchIf("/", "operator"):
                pos = lexer.getPos()
                expr = self.funcCall(
                    "div", expr, self.parseUnaryExpr(lexer), pos
                )
            elif lexer.matchIf("%", "operator"):
                pos = lexer.getPos()
                expr = self.funcCall(
                    "mod", expr, self.parseUnaryExpr(lexer), pos
                )
        return expr

    def parseUnaryExpr(self, lexer):
        if lexer.matchIf("+", "operator"):
            return self.parsePredExpr(lexer)
        if lexer.matchIf("-", "operator"):
            pos = lexer.getPos()
            token = lexer.peek()
            if token.type == "int":
                return self.parsePredExpr(lexer, True)
            elif token.type == "decimal":
                return self.parsePredExpr(lexer, True)
            else:
                call = NodeFuncall(NodeIdentifier("sub", pos), pos)
                call.addArg("a", NodeLiteral(ValueInt(0), pos))
                call.addArg("b", self.parsePredExpr(lexer))
                return call
        return self.parsePredExpr(lexer)

    def parsePredExpr(self, lexer, unary_minus=False):
        expr = self.parsePrimaryExpr(lexer, unary_minus)
        pos = lexer.getPosNext()

        if lexer.matchIf("is", "keyword"):
            if lexer.matchIf("not", "keyword"):
                if lexer.matchIf("in"):
                    return NodeNot(
                        NodeIn(expr, self.parsePrimaryExpr(lexer), pos), pos
                    )
                elif lexer.matchIf("empty", "identifier"):
                    return NodeNot(
                        self.funcCall("is_empty", expr, None, pos), pos
                    )
                elif lexer.matchIf("zero", "identifier"):
                    return NodeNot(
                        self.funcCall("is_zero", expr, None, pos), pos
                    )
                elif lexer.matchIf("negative", "identifier"):
                    return NodeNot(
                        self.funcCall("is_negative", expr, None, pos), pos
                    )
                elif lexer.matchIf("numerical", "identifier"):
                    return NodeNot(
                        self.collectPredicateMinMaxExact(
                            "is_numerical",
                            self.funcCall("string", expr, None, pos),
                            lexer,
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("alphanumerical", "identifier"):
                    return NodeNot(
                        self.collectPredicateMinMaxExact(
                            "is_alphanumerical",
                            self.funcCall("string", expr, None, pos),
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
                        self.funcCall2(
                            "is_valid_date",
                            "str",
                            self.funcCall("string", expr, None, pos),
                            "fmt",
                            NodeLiteral(ValueString("yyyyMMddHH"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("date", "identifier"):
                    return NodeNot(
                        self.funcCall2(
                            "is_valid_date",
                            "str",
                            self.funcCall("string", expr, None, pos),
                            "fmt",
                            NodeLiteral(ValueString("yyyyMMdd"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("time", "identifier"):
                    return NodeNot(
                        self.funcCall2(
                            "is_valid_time",
                            "str",
                            self.funcCall("string", expr, None, pos),
                            "fmt",
                            NodeLiteral(ValueString("HHmm"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("string", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("string"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("int", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("int"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("decimal", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("decimal"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("boolean", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("boolean"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("pattern", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("pattern"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("date", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("date"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("None", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("None"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("func", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("func"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("input", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("input"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("output", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("output"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("list", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("lsit"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("set", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("set"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("map", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("map"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("object", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
                            NodeLiteral(ValueString("object"), pos),
                            pos,
                        ),
                        pos,
                    )
                elif lexer.matchIf("node", "identifier"):
                    return NodeNot(
                        self.funcCall(
                            "equals",
                            self.funcCall("type", expr, None, pos),
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
                return NodeIn(expr, self.parsePrimaryExpr(lexer), pos)
            elif lexer.matchIf("empty", "identifier"):
                return self.funcCall("is_empty", expr, None, pos)
            elif lexer.matchIf("zero", "identifier"):
                return self.funcCall("is_zero", expr, None, pos)
            elif lexer.matchIf("negative", "identifier"):
                return self.funcCall("is_negative", expr, None, pos)
            elif lexer.matchIf("numerical", "identifier"):
                return self.collectPredicateMinMaxExact(
                    "is_numerical",
                    self.funcCall("string", expr, None, pos),
                    lexer,
                    pos,
                )
            elif lexer.matchIf("alphanumerical", "identifier"):
                return self.collectPredicateMinMaxExact(
                    "is_alphanumerical",
                    self.funcCall("string", expr, None, pos),
                    lexer,
                    pos,
                )
            elif lexer.matchIf(
                ["date", "with", "hour"],
                ["identifier", "identifier", "identifier"],
            ):
                return self.funcCall2(
                    "is_valid_date",
                    "str",
                    self.funcCall("string", expr, None, pos),
                    "fmt",
                    NodeLiteral(ValueString("yyyyMMddHH"), pos),
                    pos,
                )
            elif lexer.matchIf("date", "identifier"):
                return self.funcCall2(
                    "is_valid_date",
                    "str",
                    self.funcCall("string", expr, None, pos),
                    "fmt",
                    NodeLiteral(ValueString("yyyyMMdd"), pos),
                    pos,
                )
            elif lexer.matchIf("time", "identifier"):
                return self.funcCall2(
                    "is_valid_time",
                    "str",
                    self.funcCall("string", expr, None, pos),
                    "fmt",
                    NodeLiteral(ValueString("HHmm"), pos),
                    pos,
                )
            elif lexer.matchIf("string", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("string"), pos),
                    pos,
                )
            elif lexer.matchIf("int", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("int"), pos),
                    pos,
                )
            elif lexer.matchIf("decimal", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("decimal"), pos),
                    pos,
                )
            elif lexer.matchIf("boolean", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("boolean"), pos),
                    pos,
                )
            elif lexer.matchIf("pattern", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("pattern"), pos),
                    pos,
                )
            elif lexer.matchIf("date", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("date"), pos),
                    pos,
                )
            elif lexer.matchIf("None", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("None"), pos),
                    pos,
                )
            elif lexer.matchIf("func", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("func"), pos),
                    pos,
                )
            elif lexer.matchIf("input", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("input"), pos),
                    pos,
                )
            elif lexer.matchIf("output", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("output"), pos),
                    pos,
                )
            elif lexer.matchIf("list", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("list"), pos),
                    pos,
                )
            elif lexer.matchIf("set", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("set"), pos),
                    pos,
                )
            elif lexer.matchIf("map", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("map"), pos),
                    pos,
                )
            elif lexer.matchIf("object", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("object"), pos),
                    pos,
                )
            elif lexer.matchIf("node", "identifier"):
                return self.funcCall(
                    "equals",
                    self.funcCall("type", expr, None, pos),
                    NodeLiteral(ValueString("node"), pos),
                    pos,
                )
            lexer.previous()  # is
            return expr
        elif lexer.matchIf(["not", "in"], "keyword"):
            return NodeNot(
                NodeIn(expr, self.parsePrimaryExpr(lexer), pos), pos
            )
        elif lexer.matchIf("in", "keyword"):
            return NodeIn(expr, self.parsePrimaryExpr(lexer), pos)
        elif lexer.matchIf(
            ["starts", "not", "with"], ["identifier", "keyword", "identifier"]
        ):
            return NodeNot(
                self.funcCall2(
                    "starts_with",
                    "str",
                    expr,
                    "part",
                    self.parsePrimaryExpr(lexer),
                    pos,
                ),
                pos,
            )
        elif lexer.matchIf(["starts", "with"], ["identifier", "identifier"]):
            return self.funcCall2(
                "starts_with",
                "str",
                expr,
                "part",
                self.parsePrimaryExpr(lexer),
                pos,
            )
        elif lexer.matchIf(
            ["ends", "not", "with"], ["identifier", "keyword", "identifier"]
        ):
            return NodeNot(
                self.funcCall2(
                    "ends_with",
                    "str",
                    expr,
                    "part",
                    self.parsePrimaryExpr(lexer),
                    pos,
                ),
                pos,
            )
        elif lexer.matchIf(["ends", "with"], ["identifier", "identifier"]):
            return self.funcCall2(
                "ends_with",
                "str",
                expr,
                "part",
                self.parsePrimaryExpr(lexer),
                pos,
            )
        elif lexer.matchIf(["contains", "not"], ["identifier", "keyword"]):
            return NodeNot(
                self.funcCall2(
                    "contains",
                    "obj",
                    expr,
                    "part",
                    self.parsePrimaryExpr(lexer),
                    pos,
                ),
                pos,
            )
        elif lexer.matchIf("contains", "identifier"):
            return self.funcCall2(
                "contains",
                "obj",
                expr,
                "part",
                self.parsePrimaryExpr(lexer),
                pos,
            )
        elif lexer.matchIf(["matches", "not"], ["identifier", "keyword"]):
            return NodeNot(
                self.funcCall2(
                    "matches",
                    "str",
                    expr,
                    "pattern",
                    self.parsePrimaryExpr(lexer),
                    pos,
                ),
                pos,
            )
        elif lexer.matchIf("matches", "identifier"):
            return self.funcCall2(
                "matches",
                "str",
                expr,
                "pattern",
                self.parsePrimaryExpr(lexer),
                pos,
            )
        return expr

    def collectPredicateMinMaxExact(self, fn, expr, lexer, pos):
        min_len = NodeLiteral(ValueInt(0), pos)
        max_len = NodeLiteral(ValueInt(9999), pos)
        if lexer.matchIf("min_len", "identifier"):
            min_len = self.parsePrimaryExpr(lexer)
        if lexer.matchIf("max_len", "identifier"):
            max_len = self.parsePrimaryExpr(lexer)
        if lexer.matchIf("exact_len", "identifier"):
            min_len = max_len = self.parsePrimaryExpr(lexer)
        return self.funcCall3(
            fn, "str", expr, "min", min_len, "max", max_len, pos
        )

    def parsePrimaryExpr(self, lexer, unary_minus=False):
        if not lexer.hasNext():
            raise CklSyntaxError("Unexpected end of input", lexer.getPos())

        token = lexer.next()
        if token.value == "(" and token.type == "interpunction":
            result = self.parseBareBlock(lexer, False)
            lexer.match(")", "interpunction")
            return self.derefOrCallOrInvoke(lexer, result)

        if token.type == "identifier":
            result = NodeIdentifier(token.value, token.pos)
            if lexer.matchIf("=", "operator"):
                result = NodeAssign(
                    token.value, self.parseExpression(lexer), token.pos
                )
            elif lexer.matchIf("+=", "operator"):
                value = self.parseExpression(lexer)
                result = NodeAssign(
                    token.value,
                    self.funcCall("add", result, value, token.pos),
                    token.pos,
                )
            elif lexer.matchIf("-=", "operator"):
                value = self.parseExpression(lexer)
                result = NodeAssign(
                    token.value,
                    self.funcCall("sub", result, value, token.pos),
                    token.pos,
                )
            elif lexer.matchIf("*=", "operator"):
                value = self.parseExpression(lexer)
                result = NodeAssign(
                    token.value,
                    self.funcCall("mul", result, value, token.pos),
                    token.pos,
                )
            elif lexer.matchIf("/=", "operator"):
                value = self.parseExpression(lexer)
                result = NodeAssign(
                    token.value,
                    self.funcCall("div", result, value, token.pos),
                    token.pos,
                )
            elif lexer.matchIf("%=", "operator"):
                value = self.parseExpression(lexer)
                result = NodeAssign(
                    token.value,
                    self.funcCall("mod", result, value, token.pos),
                    token.pos,
                )
            else:
                result = self.derefOrCallOrInvoke(lexer, result)
        elif token.type == "string":
            result = NodeLiteral(ValueString(token.value), token.pos)
            result = self.derefOrInvoke(lexer, result)
        elif token.type == "int":
            result = NodeLiteral(
                ValueInt(int(token.value) * (-1 if unary_minus else 1)),
                token.pos,
            )
            result = self.invoke(lexer, result)
        elif token.type == "decimal":
            result = NodeLiteral(
                ValueDecimal(float(token.value) * (-1 if unary_minus else 1)),
                token.pos,
            )
            result = self.invoke(lexer, result)
        elif token.type == "boolean":
            result = NodeLiteral(
                ValueBoolean.fromval(token.value == "TRUE"), token.pos
            )
            result = self.invoke(lexer, result)
        elif token.type == "pattern":
            result = NodeLiteral(ValuePattern(token.value[2, -2]), token.pos)
            result = self.invoke(lexer, result)
        else:
            if token.value == "fn" and token.type == "keyword":
                result = self.parseFn(lexer, token.pos)
            elif token.value == "break" and token.type == "keyword":
                result = NodeBreak(token.pos)
            elif token.value == "continue" and token.type == "keyword":
                result = NodeContinue(token.pos)
            elif token.value == "return" and token.type == "keyword":
                if lexer.peekn(1, ";", "interpunction"):
                    result = NodeReturn(None, token.pos)
                else:
                    result = NodeReturn(self.parseExpression(lexer), token.pos)
            elif token.value == "error" and token.type == "keyword":
                result = NodeError(self.parseExpression(lexer), token.pos)
            elif token.value == "do" and token.type == "keyword":
                lexer.previous()
                result = self.parseBlock(lexer)
            elif token.value == "[" and token.type == "interpunction":
                result = self.parseListLiteral(lexer, token)
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
                        identifiers, self.parseExpression(lexer), token.pos
                    )
            elif token.value == "<<" and token.type == "interpunction":
                result = self.parseSetLiteral(lexer, token)
            elif token.value == "<<<" and token.type == "interpunction":
                result = self.parseMapLiteral(lexer, token)
            elif token.value == "<*" and token.type == "interpunction":
                result = self.parseObjectLiteral(lexer, token)
            elif token.value == "..." and token.type == "interpunction":
                token = lexer.next()
                if token.value == "[" and token.type == "interpunction":
                    result = self.parseListLiteral(lexer, token)
                elif token.value == "<<<" and token.type == "interpunction":
                    result = self.parseMapLiteral(lexer, token)
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

    def parseListLiteral(self, lexer, token):
        if lexer.matchIf("]", "interpunction"):
            return self.derefOrInvoke(lexer, NodeList(token.pos))
        else:
            expr = self.parseExpression(lexer)
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
                listExpr = self.parseOrExpr(lexer)
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
                    listExpr2 = self.parseOrExpr(lexer)
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
                        comprehension.setCondition(self.parseOrExpr(lexer))
                    lexer.match("]", "interpunction")
                    return self.derefOrInvoke(lexer, comprehension)
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
                    listExpr2 = self.parseOrExpr(lexer)
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
                        comprehension.setCondition(self.parseOrExpr(lexer))
                    lexer.match("]", "interpunction")
                    return self.derefOrInvoke(lexer, comprehension)
                else:
                    comprehension = NodeListComprehension(
                        expr, identifier, listExpr, what, token.pos
                    )
                    if lexer.matchIf("if", "keyword"):
                        comprehension.setCondition(self.parseOrExpr(lexer))
                    lexer.match("]", "interpunction")
                    return self.derefOrInvoke(lexer, comprehension)
            else:
                lst = NodeList(token.pos)
                while not lexer.peekn(1, "]", "interpunction"):
                    lst.addItem(expr)
                    expr = None
                    if not lexer.peekn(1, "]", "interpunction"):
                        lexer.match(",", "interpunction")
                        if not lexer.peekn(1, "]", "interpunction"):
                            expr = self.parseExpression(lexer)
                if expr:
                    lst.addItem(expr)
                lexer.match("]", "interpunction")
                return self.derefOrInvoke(lexer, lst)

    def parseSetLiteral(self, lexer, token):
        if lexer.matchIf(">>", "interpunction"):
            return self.derefOrInvoke(lexer, NodeSet(token.pos))
        else:
            expr = self.parseExpression(lexer)
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
                listExpr = self.parseOrExpr(lexer)
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
                    listExpr2 = self.parseOrExpr(lexer)
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
                        comprehension.setCondition(self.parseOrExpr(lexer))
                    lexer.match(">>", "interpunction")
                    return self.derefOrInvoke(lexer, comprehension)
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
                    listExpr2 = self.parseOrExpr(lexer)
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
                        comprehension.setCondition(self.parseOrExpr(lexer))
                    lexer.match(">>", "interpunction")
                    return self.derefOrInvoke(lexer, comprehension)
                else:
                    comprehension = NodeSetComprehension(
                        expr, identifier, listExpr, what, token.pos
                    )
                    if lexer.matchIf("if", "keyword"):
                        comprehension.setCondition(self.parseOrExpr(lexer))
                    lexer.match(">>", "interpunction")
                    return self.derefOrInvoke(lexer, comprehension)
            else:
                s = NodeSet(token.pos)
                s.addItem(expr)
                if not lexer.peekn(1, ">>", "interpunction"):
                    lexer.match(",", "interpunction")
                while not lexer.peekn(1, ">>", "interpunction"):
                    s.addItem(self.parseExpression(lexer))
                    if not lexer.peekn(1, ">>", "interpunction"):
                        lexer.match(",", "interpunction")
                lexer.match(">>", "interpunction")
                return self.derefOrInvoke(lexer, s)

    def parseMapLiteral(self, lexer, token):
        if lexer.matchIf(">>>", "interpunction"):
            return self.derefOrInvoke(lexer, NodeMap(token.pos))
        else:
            key = self.parseExpression(lexer)
            lexer.match("=>", "interpunction")
            value = self.parseExpression(lexer)
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
                listExpr = self.parseOrExpr(lexer)
                comprehension = NodeMapComprehension(
                    key, value, identifier, listExpr, what, token.pos
                )
                if lexer.matchIf("if", "keyword"):
                    comprehension.setCondition(self.parseOrExpr(lexer))
                lexer.match(">>>", "interpunction")
                return self.derefOrInvoke(lexer, comprehension)
            else:
                m = NodeMap(token.pos)
                if isinstance(key, NodeIdentifier):
                    key = NodeLiteral(ValueString(key.value), key.pos)
                m.addKeyValue(key, value)
                if not lexer.peekn(1, ">>>", "interpunction"):
                    lexer.match(",", "interpunction")
                while not lexer.peekn(1, ">>>", "interpunction"):
                    key = self.parseExpression(lexer)
                    if isinstance(key, NodeIdentifier):
                        key = NodeLiteral(ValueString(key.value), key.pos)
                    lexer.match("=>", "interpunction")
                    value = self.parseExpression(lexer)
                    m.addKeyValue(key, value)
                    if not lexer.peekn(1, ">>>", "interpunction"):
                        lexer.match(",", "interpunction")
                lexer.match(">>>", "interpunction")
                return self.derefOrInvoke(lexer, m)

    def parseObjectLiteral(self, lexer, token):
        obj = NodeObject(token.pos)
        while not lexer.peekn(1, "*>", "interpunction"):
            key = lexer.matchIdentifier()
            if lexer.peekn(1, "(", "interpunction"):
                fn = self.parseFn(lexer, lexer.getPos())
                obj.addKeyValue(key, fn)
            else:
                lexer.match("=", "operator")
                value = self.parseExpression(lexer)
                obj.addKeyValue(key, value)
            if not lexer.peekn(1, "*>", "interpunction"):
                lexer.match(",", "interpunction")
        lexer.match("*>", "interpunction")
        return self.derefOrInvoke(lexer, obj)

    def parseFn(self, lexer, pos):
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
                defvalue = self.parseExpression(lexer)
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
            fn.setBody(self.parseBlock(lexer))
        else:
            fn.setBody(self.parseExpression(lexer))
        return fn

    def _invoke(self, lexer, node):
        if lexer.matchIf("!>", "operator"):
            fn = None
            if lexer.matchIf(["(", "fn"], ["interpunction", "keyword"]):
                fn = self.parseFn(lexer, lexer.getPos())
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
                    call.addArg(name, self.parseExpression(lexer))
                else:
                    call.addArg(None, self.parseExpression(lexer))
                if not lexer.peekn(1, ")", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.eat(1)
            node = call
        return node

    def _call(self, lexer, node):
        if lexer.matchIf("(", "interpunction"):
            call = NodeFuncall(node, lexer.getPos())
            while not lexer.peekn(1, ")", "interpunction"):
                if lexer.peek().type == "identifier" and lexer.peekn(
                    2, "=", "operator"
                ):
                    name = lexer.matchIdentifier()
                    lexer.match("=", "operator")
                    call.addArg(name, self.parseExpression(lexer))
                else:
                    call.addArg(None, self.parseExpression(lexer))
                if not lexer.peekn(1, ")", "interpunction"):
                    lexer.match(",", "interpunction")
            lexer.eat(1)
            node = call
        return node

    def _deref(self, lexer, node):
        interrupt = False
        if lexer.matchIf("->", "operator"):
            pos = lexer.getPos()
            identifier = lexer.matchIdentifier()
            index = NodeLiteral(ValueString(identifier), pos)
            if lexer.matchIf("=", "operator"):
                value = self.parseExpression(lexer)
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
                        node.addArg(name, self.parseExpression(lexer))
                    else:
                        node.addArg(None, self.parseExpression(lexer))
                    if not lexer.peekn(1, ")", "interpunction"):
                        lexer.match(",", "interpunction")
                lexer.eat(1)
            elif lexer.matchIf("+=", "operator"):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "add", NodeDeref(node, index, None, pos), value, pos
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf("-=", "operator"):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "sub", NodeDeref(node, index, None, pos), value, pos
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf("*=", "operator"):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "mul", NodeDeref(node, index, None, pos), value, pos
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf("/=", "operator"):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "div", NodeDeref(node, index, None, pos), value, pos
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf("%=", "operator"):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "mod", NodeDeref(node, index, None, pos), value, pos
                    ),
                    pos,
                )
                interrupt = True
            else:
                node = NodeDeref(node, index, None, pos)
        elif lexer.matchIf("[", "interpunction"):
            pos = lexer.getPos()
            index = self.parseExpression(lexer)
            default_value = None
            if lexer.matchIf(",", "interpunction"):
                default_value = self.parseExpression(lexer)
            if lexer.matchIf(["]", "="], ["interpunction", "operator"]):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(node, index, value, pos)
                interrupt = True
            elif lexer.matchIf(["]", "+="], ["interpunction", "operator"]):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "add",
                        NodeDeref(node, index, default_value, pos),
                        value,
                        pos,
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf(["]", "-="], ["interpunction", "operator"]):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "sub",
                        NodeDeref(node, index, default_value, pos),
                        value,
                        pos,
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf(["]", "*="], ["interpunction", "operator"]):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "mul",
                        NodeDeref(node, index, default_value, pos),
                        value,
                        pos,
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf(["]", "/="], ["interpunction", "operator"]):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
                        "div",
                        NodeDeref(node, index, default_value, pos),
                        value,
                        pos,
                    ),
                    pos,
                )
                interrupt = True
            elif lexer.matchIf(["]", "%="], ["interpunction", "operator"]):
                value = self.parseExpression(lexer)
                node = NodeDerefAssign(
                    node,
                    index,
                    self.funcCall(
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

    def derefOrCallOrInvoke(self, lexer, node):
        while (
            lexer.peekn(1, "!>", "operator")
            or lexer.peekn(1, "[", "interpunction")
            or lexer.peekn(1, "(", "interpunction")
            or lexer.peekn(1, "->", "operator")
        ):
            if lexer.peekn(1, "!>", "operator"):
                node = self._invoke(lexer, node)
            elif lexer.peekn(1, "(", "interpunction"):
                node = self._call(lexer, node)
            elif lexer.peekn(1, "[", "interpunction") or lexer.peekn(
                1, "->", "operator"
            ):
                result = self._deref(lexer, node)
                node = result[0]
                if result[1]:
                    break
        return node

    def derefOrInvoke(self, lexer, node):
        while (
            lexer.peekn(1, "!>", "operator")
            or lexer.peekn(1, "[", "interpunction")
            or lexer.peekn(1, "->", "operator")
        ):
            if lexer.peekn(1, "!>", "operator"):
                node = self._invoke(lexer, node)
            elif lexer.peekn(1, "[", "interpunction") or lexer.peekn(
                1, "->", "operator"
            ):
                result = self._deref(lexer, node)
                node = result[0]
                if result[1]:
                    break
        return node

    def invoke(self, lexer, node):
        while lexer.peekn(1, "!>", "operator"):
            node = self._invoke(lexer, node)
        return node

    def funcCall(self, fn, exprA, exprB, pos):
        result = NodeFuncall(NodeIdentifier(fn, pos), pos)
        if exprB:
            return self.funcCall2(fn, "a", exprA, "b", exprB, pos)
        else:
            return self.funcCall1(fn, "obj", exprA, pos)
        return result

    def funcCall1(self, fn, a, exprA, pos):
        result = NodeFuncall(NodeIdentifier(fn, pos), pos)
        result.addArg(a, exprA)
        return result

    def funcCall2(self, fn, a, exprA, b, exprB, pos):
        result = NodeFuncall(NodeIdentifier(fn, pos), pos)
        result.addArg(a, exprA)
        result.addArg(b, exprB)
        return result

    def funcCall3(self, fn, a, exprA, b, exprB, c, exprC, pos):
        result = NodeFuncall(NodeIdentifier(fn, pos), pos)
        result.addArg(a, exprA)
        result.addArg(b, exprB)
        result.addArg(c, exprC)
        return result
