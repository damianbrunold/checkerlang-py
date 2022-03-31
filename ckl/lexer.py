from ckl.errors import CklSyntaxError

KEYWORDS = [
    "if", "then", "elif", "else", "and", "or", "not", 
    "is", "in", "def", "fn", "for", "while", 
    "do", "end", "finally", "catch", "break", "continue", 
    "return", "error", "require", "as", "also"
]

OPERATORS = [
    "+", "-", "*", "/", "%", 
    "==", "<>", "!=", "<", "<=", ">", ">=", 
    "=", "+=", "-=", "*=", "/=", "%=", 
    "!>", "->"
]


class SourcePos:
    def __init__(self, filename, line, column):
        self.filename = filename
        self.line = line
        self.column = column

    def __repr__(self):
        if not self.filename: return "-"
        return ((self.filename + ":") if self.filename != "-" else ":") + self.line + ":" + self.column


class Token:
    def __init__(self, value, tokentype, pos):
        self.value = value
        self.type = tokentype
        self.pos = pos

    def __repr__(self):
        result = self.value
        result = result.replace("\\", "\\\\")
        result = result.replace("'", "\\'")
        result = result.replace("\n", "\\n")
        result = result.replace("\r", "\\r")
        result = result.replace("\t", "\\t")
        return result + " (" + self.type + ")"


class Lexer:
    def __init__(self, script, name):
        self.script = script + ' '
        self.name = name
        self.tokens = []

    @classmethod
    def init(cls, script, name):
        return Lexer(script, name).scan()

    def hasNext(self):
        return self.nextToken < len(self.tokens)

    def next(self):
        result = self.tokens[self.nextToken]
        self.nextToken += 1
        return result

    def peek(self):
        return self.tokens[self.nextToken]

    def eat(self, n):
        self.nextToken += n

    def previous(self):
        if self.nextToken == 0:
            raise CklSyntaxError("Cannot go before beginning", self.getPos())
        self.nextToken -= 1

    def getPos(self):
        if self.nextToken == 0:
            return self.getPosNext()
        return self.tokens[self.nextToken - 1].pos

    def getPosNext(self):
        if not self.hasNext():
            return self.getPos()
        return self.tokens[self.nextToken].pos

    def peekn(self, n, token, tokentype=None):
        if self.nextToken + n - 1 < len(self.tokens):
            t = self.tokens[self.nextToken + n - 1]
            if tokentype is None:
                return t.value == token and (t.type == "identifier" or t.type == "keyword")
            else:
                return t.value == token and t.type == tokentype
        return False

    def peekOne(self, n, tokens, tokentype=None):
        for token in tokens:
            if self.peekn(n, token, tokentype):
                return True
        return False

    def matchIf(self, token, tokentype=None):
        if isinstance(token, list):
            if isinstance(tokentype, list):
                for i in range(len(token)):
                    if not self.peekn(i+1, token[i], tokentype[i]):
                        return False
            else:
                for i in range(len(token)):
                    if not self.peekn(i+1, token[i], tokentype):
                        return False
            self.eat(len(token))
            return True
        else:
            if self.peekn(1, token, tokentype):
                self.eat(1)
                return True
            return False

    def match(self, token, tokentype):
        if not self.hasNext():
            raise CklSyntaxError("Unexpected end of input", self.getPos())
        t = self.next()
        if t.value != token or t.type != tokentype:
            raise CklSyntaxError("Expected " + token + " but got " + t, t.pos)

    def matchIdentifier(self):
        if not self.hasNext():
            raise CklSyntaxError("Unexpected end of input", self.getPos())
        t = self.next()
        if t.type != "identifier":
            raise CklSyntaxError("Expected identifier but got " + t, t.pos)
        return t.value

    def scan(self):
        self.tokens = []
        self.nextToken = 0
        
        filename = self.name

        tempbuf = ""
        token = ""
        state = 0
        pos = 0
        line = 1
        column = 0
        updatepos = True
        while pos < len(self.script):
            ch = self.script[pos]
            pos += 1
            if updatepos:
                if ch == '\n':
                    line += 1
                    column = 0
                else:
                    column += 1
            updatepos = True

            if state == 0: # Eat whitespace
                if ch == '#':
                    state = 9
                elif ch in "+-*%":
                    token += ch
                    state = 10
                elif ch in "()[],;":
                    self.tokens.append(Token(ch, "interpunction", SourcePos(filename, line, column)))
                elif ch == '/':
                    state = 5
                elif ch in "<>=!":
                    token += ch
                    state = 2
                elif ch == '"':
                    state = 3
                elif ch == '\'':
                    state = 4
                elif ch == '0':
                    state = 70
                elif ch in "0123456789":
                    token += ch
                    state = 7
                elif ch not in " \t\r\n":
                    token += ch
                    state = 1

            elif state == 1: # normal token
                if ch in "()+-*/%[]<>=,;!\"' \t\r\n#":
                    if token:
                        if token == "TRUE":
                            here = SourcePos(filename, line, column-len("TRUE"))
                            self.tokens.append(Token("TRUE", "boolean", here))
                        elif token == "FALSE":
                            here = SourcePos(filename, line, column-len("TRUE"))
                            self.tokens.append(Token("FALSE", "boolean", here))
                        elif token in KEYWORDS:
                            here = SourcePos(filename, line, column-len(token))
                            self.tokens.append(Token(token, "keyword", here))
                        else:
                            here = SourcePos(filename, line, column-len(token))
                            self.tokens.append(Token(token, "identifier", here))
                        token = ""
                    pos -= 1
                    updatepos = False
                    state = 0
                else:
                    token += ch
                    if token == "...":
                        here = SourcePos(filename, line, column-len(token))
                        self.tokens.append(Token(token, "interpunction", here))
                        token = ""
                        state = 0

            elif state == 2: # <>, <=, >=, ==, <<, >>, <<<, >>>, !>, <*, *>
                if ch == '=':
                    token += ch
                    here = SourcePos(filename, line, column-len(token)-1)
                    self.tokens.append(Token(token, "operator", here))
                    token = ""
                    state = 0
                elif ch == '>' and token == "=":
                    token += ch
                    here = SourcePos(filename, line, column-len(token)-1)
                    self.tokens.append(Token(token, "interpunction", here))
                    token = ""
                    state = 0
                elif ch == '>' and token == "<":
                    here = SourcePos(filename, line, column-1)
                    self.tokens.append(Token("<>", "operator", here))
                    token = ""
                    state = 0
                elif ch == '<' and token == "<":
                    token += ch
                    state = 21
                elif ch == '>' and token == ">":
                    token += ch
                    state = 21
                elif ch == '>' and token == "!":
                    token += ch
                    here = SourcePos(filename, line, column-len(token)-1)
                    self.tokens.append(Token("!>", "operator", here))
                    token = ""
                    state = 0
                elif ch == '*' and token == "<":
                    here = SourcePos(filename, line, column-1)
                    self.tokens.append(Token("<*", "interpunction", here))
                    token = ""
                    state = 0
                else:
                    here = SourcePos(filename, line, column-len(token))
                    self.tokens.append(Token(token, "operator", here))
                    token = ""
                    pos -= 1
                    updatepos = False
                    state = 0

            elif state == 21: # <<, >>, <<<, >>>
                if ch == '<' and token == "<<":
                    here = SourcePos(filename, line, column-3)
                    self.tokens.append(Token("<<<", "interpunction", here))
                    token = ""
                    state = 0
                elif ch == '>' and token == ">>":
                    here = SourcePos(filename, line, column-3)
                    self.tokens.append(Token(">>>", "interpunction", here))
                    token = ""
                    state = 0
                else:
                    here = SourcePos(filename, line, column-len(token))
                    self.tokens.append(Token(token, "interpunction", here))
                    token = ""
                    pos -= 1
                    updatepos = False
                    state = 0

            elif state ==  3: # double quotes
                if ch == '"':
                    here = SourcePos(filename, line, column-len(token)-2+1)
                    self.tokens.append(Token(token, "string", here))
                    token = ""
                    state = 0
                elif ch == '\\':
                    state = 31
                else:
                    token += ch

            elif state == 31: # double quotes escapes
                if ch == 'n':
                    token += '\n'
                    state = 3
                elif ch == 'r':
                    token += '\r'
                    state = 3
                elif ch == 't':
                    token += '\t'
                    state = 3
                elif ch == 'x':
                    state = 311
                else:
                    token += ch
                    state = 3

            elif state == 311: # hex num first digit
                tempbuf = ch
                state = 312

            elif state == 312: # hex num second digit
                tempbuf += ch
                token += chr(int(tempbuf, 16))
                tempbuf = ""
                state = 3

            elif state == 4: # single quote
                if ch == '\'':
                    here = SourcePos(filename, line, column-len(token)-2+1)
                    self.tokens.append(Token(token, "string", here))
                    token = ""
                    state = 0
                elif ch == '\\':
                    state = 41
                else:
                    token += ch

            elif state == 41: # single quotes escapes
                if ch == 'n':
                    token += '\n'
                    state = 4
                elif ch == 'r':
                    token += '\r'
                    state = 4
                elif ch == 't':
                    token += '\t'
                    state = 4
                elif ch == 'x':
                    state = 411
                else:
                    token += ch
                    state = 4

            elif state == 411: # hex num first digit
                tempbuf = ch
                state = 412

            elif state == 412: # hex num second digit
                tempbuf += ch
                token += chr(int(tempbuf, 16))
                tempbuf = ""
                state = 4

            elif state == 5: # check for pattern
                if ch == '/':
                    token += "//"
                    state = 6
                elif ch == '=':
                    here = SourcePos(filename, line, column-1)
                    self.tokens.append(Token("/=", "operator", here))
                    state = 0
                else:
                    here = SourcePos(filename, line, column-1)
                    self.tokens.append(Token("/", "operator", here))
                    pos -= 1
                    updatepos = False
                    state = 0

            elif state == 6: # pattern
                token += ch
                if token.endswith("//"):
                    here = SourcePos(filename, line, column-len(token)-4+1)
                    self.tokens.append(Token(token, "pattern", here))
                    token = ""
                    state = 0

            elif state == 7: # int or decimal
                if ch == '.':
                    token += ch
                    state = 8
                elif ch in "0123456789_":
                    token += ch
                elif ch in "()[]<>=! \t\n\r+-*/%,;#":
                    here = SourcePos(filename, line, column-len(token))
                    self.tokens.append(Token(token.replace("_", ""), "int", here))
                    token = ""
                    pos -= 1
                    updatepos = False
                    state = 0
                else:
                    token += ch
                    state = 1

            elif state == 70: # int, decimal or hex/binary int literal
                if ch == 'x':
                    state = 71; # hex int literal
                elif ch == 'b':
                    state = 72; # binary int literal
                else:
                    token += '0'
                    pos -= 1
                    updatepos = False
                    state = 7

            elif state == 71: # hex int literal
                if ch in "0123456789abcdefABCDEF_":
                    token += ch
                elif ch in "()[]<>=! \t\n\r+-*/%,;#":
                    here = SourcePos(filename, line, column-len(token))
                    self.tokens.append(Token(str(int(token.replace("_", ""), 16)), "int", here))
                    token = ""
                    pos -= 1
                    updatepos = False
                    state = 0
                else:
                    token += ch
                    state = 1

            elif state == 72: # binary int literal
                if ch in "01_":
                    token += ch
                elif ch in "()[]<>=! \t\n\r+-*/%,;#":
                    here = SourcePos(filename, line, column-len(token))
                    self.tokens.append(Token(str(int(token.replace("_", ""), 2)), "int", here))
                    token = ""
                    pos -= 1
                    updatepos = False
                    state = 0
                else:
                    token += ch
                    state = 1

            elif state == 8: # decimal
                if ch in "0123456789_":
                    token += ch
                elif ch in "()[]<>=! \t\n\r+-*/%,;#":
                    here = SourcePos(filename, line, column-len(token))
                    self.tokens.append(Token(token.replace("_", ""), "decimal", here))
                    token = ""
                    pos -= 1
                    updatepos = False
                    state = 0
                else:
                    token += ch
                    state = 1

            elif state == 9: # comment
                if ch == '\n':
                    state = 0

            elif state == 10: # potentially composite assign or -> or *>
                if ch == '=':
                    token += ch
                    here = SourcePos(filename, line, column)
                    self.tokens.append(Token(token, "operator", here))
                    token = ""
                    state = 0
                elif (token == '-' and ch == '>'):
                    here = SourcePos(filename, line, column)
                    self.tokens.append(Token("->", "operator", here))
                    token = ""
                    state = 0
                elif (token == '*' and ch == '>'):
                    here = SourcePos(filename, line, column)
                    self.tokens.append(Token("*>", "interpunction", here))
                    token = ""
                    state = 0
                else:
                    here = SourcePos(filename, line, column)
                    self.tokens.append(Token(token, "operator", here))
                    token = ""
                    pos -= 1
                    updatepos = False
                    state = 0
        return self


    def __repr__(self):
        return "[" + ", ".join([str(s) for s in self.tokens]) + "] @" + str(self.nextToken)

