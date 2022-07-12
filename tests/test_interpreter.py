from ckl.interpreter import Interpreter
from ckl.functions import get_none_environment

interpreter = Interpreter(False, False)

def interpreter_test(source, expected):
    assert (
        repr(interpreter.interpret(source, "{test}", get_none_environment()))
        ==
        expected
    )


def test_string():
    interpreter_test("'abc'", "'abc'")


def test_int():
    interpreter_test("123", "123")


def test_int_list():
    interpreter_test("[1, 2, 3]", "[1, 2, 3]")


def test_block():
    interpreter_test("do 2 * 3; 3 * 4; end", "12")


def test_if_then1():
    interpreter_test("if 13 < 12 then 'a' if 11 < 12 then 'b'", "'b'")


def test_if_then2():
    interpreter_test("if 13 < 12 then 'a' if 14 < 12 then 'b'", "TRUE")


def test_if_then_else():
    interpreter_test("if 13 < 12 then 'a' if 14 < 12 then 'b' else 'c'", "'c'")


def test_if_then_with_block():
    interpreter_test(
        "if 13 < 12 then do 'a' end if 11 < 12 then do 2 * 2; 'b'; end", "'b'"
    )


def test_list_with_if():
    interpreter_test(
        "[if 1 < 2 then 'a' else 'b', 'x', if 1 > 2 then 'c' else 'd']",
        "['a', 'x', 'd']",
    )


def test_list_with_fn():
    interpreter_test("[1, fn(x) 2*x, 2]", "[1, <#lambda>, 2]")


def test_for_loop():
    interpreter_test("for i in range(10) do if i == 5 then return i end", "5")


def test_def():
    interpreter_test("def a=12;a+2", "14")


def test_assign():
    interpreter_test("def a=12; def b = 3; a = b + 2 * a; a", "27")


def test_or_expr_1():
    interpreter_test("2 == 3 or 3 == 4 or 4 == 4", "TRUE")


def test_or_expr_2():
    interpreter_test("2 == 3 or 3 == 4 or 4 == 5", "FALSE")


def test_and_expr_1():
    interpreter_test("2 == 2 and 3 == 3 and 4 == 4", "TRUE")


def test_and_expr_2():
    interpreter_test("2 == 2 and 3 == 3 and 4 == 5", "FALSE")


def test_not_expr_1():
    interpreter_test("not 2 == 3", "TRUE")


def test_not_expr_2():
    interpreter_test("not 2 == 2", "FALSE")


def test_boolean_algebra():
    interpreter_test("2 == 3 or 3 == 3 and not 4 == 5", "TRUE")


def test_comparison_1():
    interpreter_test("2 == 2", "TRUE")


def test_comparison_2():
    interpreter_test("2 == 2 != 3", "TRUE")


def test_comparison_3():
    interpreter_test("2 == 2 <> 3", "TRUE")


def test_comparison_4():
    interpreter_test("2 < 3", "TRUE")


def test_comparison_5():
    interpreter_test("2 < 3 <= 3 < 4", "TRUE")


def test_comparison_6():
    interpreter_test("2 < 3 < 3 <= 4", "FALSE")


def test_comparison_7():
    interpreter_test("5 >= 5 > 4 >= 2 == 2", "TRUE")


def test_comparison_8():
    interpreter_test("5 >= 5 > 5 >= 2 == 2", "FALSE")


def test_arithmetic_add_1():
    interpreter_test("2 + 3", "5")


def test_arithmetic_add_2():
    interpreter_test("2 + 3 + 4", "9")


def test_arithmetic_sub_1():
    interpreter_test("2 - 3", "-1")


def test_arithmetic_sub_2():
    interpreter_test("2 - 3 - 4", "-5")


def test_arithmetic_mul_1():
    interpreter_test("2 * 3", "6")


def test_arithmetic_mul_2():
    interpreter_test("2 * 3 * 4", "24")


def test_arithmetic_div_1():
    interpreter_test("6 / 2", "3")


def test_arithmetic_div_2():
    interpreter_test("10 / 20.0", "0.5")


def test_arithmetic_mod_1():
    interpreter_test("6 % 2", "0")


def test_arithmetic_mod_2():
    interpreter_test("7 % 2", "1")


def test_arithmetic_1():
    interpreter_test("(2 + 3) * (3 + 4) / 5", "7")


def test_arithmetic_2():
    interpreter_test("2 + 3 * 3 + 4 / 5", "11")


def test_arithmetic_3():
    interpreter_test("2 + 3 * 3 + 4 / 5.0", "11.8")


def test_unary_1():
    interpreter_test("-2", "-2")


def test_unary_2():
    interpreter_test("2 + -2", "0")


def test_isempty_1():
    interpreter_test("[] is empty", "TRUE")


def test_isempty_2():
    interpreter_test("[1, 2] is empty", "FALSE")


def test_isnotempty_1():
    interpreter_test("[] is not empty", "FALSE")


def test_isnotempty_2():
    interpreter_test("[1, 2] is not empty", "TRUE")


def test_inlist_1():
    interpreter_test(
        "def feld1 = 'M231'; feld1 is in ['M230', 'M231', 'M232']", "TRUE"
    )


def test_inlist_2():
    interpreter_test(
        "def feld1 = 'M233'; feld1 is in ['M230', 'M231', 'M232']", "FALSE"
    )


def test_inlist_3():
    interpreter_test(
        "def feld1 = 'M231'; feld1 not in ['M230', 'M231', 'M232']", "FALSE"
    )


def test_inlist_4():
    interpreter_test("def feld1 = 2; feld1 in [1, 2, 3]", "TRUE")


def test_inlist_5():
    interpreter_test("def feld1 = '2'; feld1 is in [1, 2, 3]", "FALSE")


def test_inlist_6():
    interpreter_test("def feld1 = 4; feld1 in [1, 2, 3]", "FALSE")


def test_IsZero1():
    interpreter_test("1 is zero", "FALSE")


def test_IsZero2():
    interpreter_test("0 is zero", "TRUE")


def test_IsNotZero():
    interpreter_test("1 is not zero", "TRUE")


def test_IsNegative1():
    interpreter_test("0 is negative", "FALSE")


def test_IsNegative2():
    interpreter_test("-1 is negative", "TRUE")


def test_IsNotNegative():
    interpreter_test("1 is not negative", "TRUE")


def test_IsNumerical():
    interpreter_test("'1234' is numerical", "TRUE")


def test_IsNotNumerical():
    interpreter_test("'12a' is not numerical", "TRUE")


def test_IsAlphanumerical():
    interpreter_test("'abc123' is alphanumerical", "TRUE")


def test_IsNotAlphanumerical():
    interpreter_test("'abc--' is not alphanumerical", "TRUE")


def test_IsNotDateWithHour():
    interpreter_test("'2001010199' is not date with hour", "TRUE")


def test_IsDateWithHour1():
    interpreter_test("'2001010112' is date with hour", "TRUE")


def test_IsDateWithHour2():
    interpreter_test("'20010101' is date with hour", "FALSE")


def test_IsNotDate():
    interpreter_test("'20010133' is not date", "TRUE")


def test_IsDate():
    interpreter_test("'20010101' is date", "TRUE")


def test_IsTime():
    interpreter_test("'1245' is time", "TRUE")


def test_IsNotTime():
    interpreter_test("'2512' is not time", "TRUE")


def test_StartsWith():
    interpreter_test("'abc' starts with 'a'", "TRUE")


def test_StartsNotWith():
    interpreter_test("'abc' starts not with 'b'", "TRUE")


def test_EndsWith():
    interpreter_test("'abc' ends with 'c'", "TRUE")


def test_EndsNotWith():
    interpreter_test("'abc' ends not with 'b'", "TRUE")


def test_Contains():
    interpreter_test("'abc' contains 'b'", "TRUE")


def test_ContainsNot():
    interpreter_test("'abc' contains not 'x'", "TRUE")


def test_Matches():
    interpreter_test("'abc' matches //[a-z]+//", "TRUE")


def test_MatchesNot():
    interpreter_test("'abc' matches not //[1-9]+//", "TRUE")


def test_Deref_1():
    interpreter_test("def feld1 = 'abc123'; feld1[1]", "'b'")


def test_Deref_2():
    interpreter_test("[1, 2, 3][2]", "3")


def test_Deref_3():
    interpreter_test("[['a', 1], ['b', 2]][1][0]", "'b'")


def test_Deref_4():
    interpreter_test("'abcd'[2]'", "'c'")


def test_FuncDef_1():
    interpreter_test("def dup = fn(n) 2 * n; dup(3)", "6")


def test_FuncDef_2():
    interpreter_test("def dup(n) 2 * n; dup(3)", "6")


def test_FuncDefWithBlock():
    interpreter_test(
        "def myfn = fn(n) do def m = 2 * n; "
        "if m % 2 == 0 then m + 1 else m end; myfn(3)",
        "7",
    )


def test_Lambda():
    interpreter_test("(fn(a, b = 3) string(a) * b)(55)", "'555555'")


def test_FuncRecursive():
    interpreter_test(
        "def a = fn(x) do def y = x - 1; "
        "if x == 0 then 1 else x * a(y) end; a(10)",
        "3628800",
    )


def test_FuncDefaultArg_1():
    interpreter_test("def a = fn(x = 12) x; a(10)", "10")


def test_FuncDefaultArg_2():
    interpreter_test("def a = fn(x = 12) x; a()", "12")


def test_FuncLength_1():
    interpreter_test("length('abc')", "3")


def test_FuncLength_2():
    interpreter_test("length([1, 2, 3])", "3")


def test_FuncLower():
    interpreter_test("require String; String->lower('Abc')", "'abc'")


def test_FuncUpper():
    interpreter_test("require String; String->upper('Abc')", "'ABC'")


def test_FuncNonZero_1():
    interpreter_test("non_zero('12', '3')", "'12'")


def test_FuncNonZero_2():
    interpreter_test("non_zero('0', '3')", "'3'")


def test_FuncNonEmpty_1():
    interpreter_test("non_empty('12', '3')", "'12'")


def test_FuncNonEmpty_2():
    interpreter_test("non_empty('', '3')", "'3'")


def test_FuncInt():
    interpreter_test("int('12')", "12")


def test_FuncDecimal():
    interpreter_test("decimal('12.3')", "12.3")


def test_FuncBoolean_1():
    interpreter_test("boolean('1')", "TRUE")


def test_FuncBoolean_2():
    interpreter_test("boolean('0')", "FALSE")


def test_FuncString():
    interpreter_test("string(123)", "'123'")


def test_FuncPattern():
    interpreter_test("pattern('^abc[0-9]+$')", "//^abc[0-9]+$//")


def test_FuncSplit_1():
    interpreter_test(
        "split('a,b,ccc,d,e', ',')", "['a', 'b', 'ccc', 'd', 'e']"
    )


def test_FuncSplit_2():
    interpreter_test(
        "split('a, b;ccc,d ,e', ' ?[,;] ?')", "['a', 'b', 'ccc', 'd', 'e']"
    )


def test_List_1():
    interpreter_test("[1, 2, 3]", "[1, 2, 3]")


def test_List_2():
    interpreter_test("[1, 2, 3,]", "[1, 2, 3]")


def test_List_3():
    interpreter_test("[1]", "[1]")


def test_List_4():
    interpreter_test("[]", "[]")


def test_ListComprehensionSimple():
    interpreter_test("[x * 2 for x in range(5)]", "[0, 2, 4, 6, 8]")


def test_ListComprehensionKeysMap():
    interpreter_test(
        "[x for x in keys <<<'a' => 12, 'b' => 13>>>]", "['a', 'b']"
    )


def test_ListComprehensionValuesMap():
    interpreter_test(
        "[x for x in values <<<'a' => 12, 'b' => 13>>>]", "[12, 13]"
    )


def test_ListComprehensionEntriesMap():
    interpreter_test(
        "[x for x in entries <<<'a' => 12, 'b' => 13>>>]",
        "[['a', 12], ['b', 13]]",
    )


def test_ListComprehensionKeysObject():
    interpreter_test("[x for x in keys <*a = 12, b = 13*>]", "['a', 'b']")


def test_ListComprehensionValuesObject():
    interpreter_test("[x for x in values <*a = 12, b = 13*>]", "[12, 13]")


def test_ListComprehensionEntriesObject():
    interpreter_test(
        "[x for x in entries <*a = 12, b = 13*>]", "[['a', 12], ['b', 13]]"
    )


def test_ListComprehensionWithCondition():
    interpreter_test("[x * 2 for x in range(5) if x % 2 == 1]", "[2, 6]")


def test_ListComprehensionString():
    interpreter_test("[int(ch) for ch in '123']", "[1, 2, 3]")


def test_ListComprehensionParallel():
    interpreter_test(
        "[a * b for a in [1, 2, 3] also for b in [1, 2, 3]]", "[1, 4, 9]"
    )


def test_ListComprehensionProduct():
    interpreter_test(
        "[a * b for a in [1, 2, 3] for b in [1, 2, 3]]",
        "[1, 2, 3, 2, 4, 6, 3, 6, 9]",
    )


def test_SetComprehensionSimple():
    interpreter_test("<<x * 2 for x in range(5)>>", "<<0, 2, 4, 6, 8>>")


def test_SetComprehensionKeysMap():
    interpreter_test(
        "<<x for x in keys <<<'a' => 12, 'b' => 13>>> >>", "<<'a', 'b'>>"
    )


def test_SetComprehensionValuesMap():
    interpreter_test(
        "<<x for x in values <<<'a' => 12, 'b' => 13>>> >>", "<<12, 13>>"
    )


def test_SetComprehensionEntriesMap():
    interpreter_test(
        "<<x for x in entries <<<'a' => 12, 'b' => 13>>> >>",
        "<<['a', 12], ['b', 13]>>",
    )


def test_SetComprehensionWithCondition():
    interpreter_test("<<x * 2 for x in range(5) if x % 2 == 1>>", "<<2, 6>>")


def test_SetComprehensionString():
    interpreter_test("<<int(ch) for ch in '12312'>>", "<<1, 2, 3>>")


def test_SetComprehensionParallel():
    interpreter_test(
        "<<a * b for a in [1, 2, 3] also for b in [1, 2, 3]>>", "<<1, 4, 9>>"
    )


def test_SetComprehensionProduct():
    interpreter_test(
        "<<a * b for a in [1, 2, 3] for b in [1, 2, 3]>>",
        "<<1, 2, 3, 4, 6, 9>>",
    )


def test_MapComprehensionSimple():
    interpreter_test(
        "<<<a => 2 * a for a in range(5)>>>",
        "<<<0 => 0, 1 => 2, 2 => 4, 3 => 6, 4 => 8>>>",
    )


def test_MapComprehensionSimple2():
    interpreter_test(
        "<<<'x' + a => 2 * a for a in range(5)>>>",
        "<<<'x0' => 0, 'x1' => 2, 'x2' => 4, 'x3' => 6, 'x4' => 8>>>",
    )


def test_MapComprehensionValuesMap():
    interpreter_test(
        "<<<x[0] => x[1] for x in values "
        "<<<'a' => ['u', 12], 'b' => ['v', 13]>>> >>>",
        "<<<'u' => 12, 'v' => 13>>>",
    )


def test_MapComprehensionEntriesMap():
    interpreter_test(
        "<<<x[0] => x[1][1] for x in entries "
        "<<<'a' => ['u', 12], 'b' => ['v', 13]>>> >>>",
        "<<<'a' => 12, 'b' => 13>>>",
    )


def test_MapComprehensionWithCondition():
    interpreter_test(
        "<<<a => 2 * a for a in range(5) if 2 * a < 6>>>",
        "<<<0 => 0, 1 => 2, 2 => 4>>>",
    )


def test_FuncRange1():
    interpreter_test("range()", "[]")


def test_FuncRange2():
    interpreter_test("range(10)", "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]")


def test_FuncRange3():
    interpreter_test("range(5, 10)", "[5, 6, 7, 8, 9]")


def test_FuncRange4():
    interpreter_test("range(10, 5, -1)", "[10, 9, 8, 7, 6]")


def test_FuncRange5():
    interpreter_test("range(5, 10, -1)", "[]")


def test_FuncSubstr1():
    interpreter_test("substr('abcdef', 3)", "'def'")


def test_FuncSubstr2():
    interpreter_test("substr('abcdef', 3, 4)", "'d'")


def test_FuncSubstr3():
    interpreter_test("substr('abcdef', 5)", "'f'")


def test_FuncSubstr4():
    interpreter_test("substr('abcdef', 6)", "''")


def test_FuncSublist1():
    interpreter_test("sublist([1, 2, 3, 4], 2)", "[3, 4]")


def test_FuncSublist2():
    interpreter_test("sublist([1, 2, 3, 4], 2, 3)", "[3]")


def test_FuncSublist3():
    interpreter_test("sublist([1, 2, 3, 4], 3)", "[4]")


def test_FuncSublist4():
    interpreter_test("sublist([1, 2, 3, 4], 4)", "[]")


def test_FuncFindStr1():
    interpreter_test("find('abcd', 'b')", "1")


def test_FuncFindStr2():
    interpreter_test("find('abcd', 'e')", "-1")


def test_FuncFindList1():
    interpreter_test("find([1, 2, 3], 2)", "1")


def test_FuncFindList2():
    interpreter_test("find([1, 2, 3], 4)", "-1")


def test_FuncFindListWithKey1():
    interpreter_test(
        "find([[1, 'a'], [2, 'b'], [3, 'c']], 2, fn(x) x[0])", "1"
    )


def test_FuncFindListWithKey2():
    interpreter_test(
        "find([[1, 'a'], [2, 'b'], [3, 'c']], 4, fn(x) x[0])", "-1"
    )


def test_FuncSet():
    interpreter_test("set([1, 2, 3, 3, 4, 5])", "<<1, 2, 3, 4, 5>>")


def test_FuncMap():
    interpreter_test(
        "map([[1, 'a'], [2, 'b'], [3, 'c'], [3, 'd'], [4, 'e'], [5, 'f']])",
        "<<<1 => 'a', 2 => 'b', 3 => 'd', 4 => 'e', 5 => 'f'>>>",
    )


def test_FuncSubstitute():
    interpreter_test("substitute('abcdef', 3, 'x')", "'abcxef'")


def test_FuncRandom():
    interpreter_test(
        "require Random; Random->set_seed(1); Random->random(10)", "2"
    )


def test_FuncSqrt():
    interpreter_test("require Math; Math->sqrt(4)", "2.0")


def test_BlockFuncOrdering():
    interpreter_test(
        "def a = fn(y) do def b = fn(x) 2 * c(x); "
        "def c = fn(x) 3 + x; b(y); end; a(12)",
        "30",
    )


def test_BlockFuncOrderingGlobal():
    interpreter_test(
        "def b = fn(x) 2 * c(x); def c = fn(x) 3 + x; b(12)", "30"
    )


def test_EmptyListLiteral():
    interpreter_test(
        "def f(x, y) do def r = []; append(r, x); "
        "append(r, y); return r; end; f(1, 2); f(2, 3);",
        "[2, 3]",
    )


def test_NoneEmptyListLiteral():
    interpreter_test(
        "def f(x, y) do def r = [1]; append(r, x); "
        "append(r, y); return r; end; f(1, 2); f(2, 3);",
        "[1, 2, 3]",
    )


def test_FuncType1():
    interpreter_test("type(4)", "'int'")


def test_FuncType2():
    interpreter_test("type(4.0)", "'decimal'")


def test_FuncType3():
    interpreter_test("type('a')", "'string'")


def test_FuncType4():
    interpreter_test("type(//a//)", "'pattern'")


def test_FuncType5():
    interpreter_test("type([1])", "'list'")


def test_FuncType6():
    interpreter_test("type(<<1>>)", "'set'")


def test_FuncType7():
    interpreter_test("type(<<<1 => 2>>>)", "'map'")


def test_FuncType8():
    interpreter_test("type(fn(x) x)", "'func'")


def test_FuncType9():
    interpreter_test("type(TRUE)", "'boolean'")


def test_FuncType10():
    interpreter_test("type(date())", "'date'")


def test_ParseSimpleReturn():
    interpreter_test("parse('return x + 1')", "(add x, 1)")


def test_ParseSimpleBlockReturn():
    interpreter_test("parse('do return x + 1; end')", "(add x, 1)")


def test_ParseBlockReturn():
    interpreter_test(
        "parse('do def x = 1; return x + 1; end')",
        "(block (def x = 1), (add x, 1))",
    )


def test_ParseBlockEarlyReturn():
    interpreter_test(
        "parse('do return x + 1; def x = 1; end')",
        "(block (return (add x, 1)), (def x = 1))",
    )


def test_ParseBareBlockReturn():
    interpreter_test(
        "parse('def x = 1; return x + 1;')", "(block (def x = 1), (add x, 1))"
    )


def test_ParseBareBlockEarlyReturn():
    interpreter_test(
        "parse('return x + 1; def x = 1')",
        "(block (return (add x, 1)), (def x = 1))",
    )


def test_ParseLambdaReturn():
    interpreter_test(
        "parse('def fun(x) return x + 1')",
        "(def fun = (lambda x, (add x, 1)))",
    )


def test_ParseLambdaBlockReturn():
    interpreter_test(
        "parse('def fun(x) do x = x * 2; return x + 1; end')",
        "(def fun = (lambda x, (block (x = (mul x, 2)), (add x, 1))))",
    )


def test_ParseLambdaBlockEarlyReturn():
    interpreter_test(
        "parse('def fun(x) do return x + 1; x = x * 2; end')",
        "(def fun = (lambda x, (block (return (add x, 1)), "
        "(x = (mul x, 2)))))",
    )


def test_SpreadInListLiteral():
    interpreter_test("[1, ...[2, 3, 4], 5]", "[1, 2, 3, 4, 5]")


def test_SpreadInListLiteralWithIdentifier():
    interpreter_test("def a = [2, 3, 4]; [1, ...a, 5]", "[1, 2, 3, 4, 5]")


def test_SpreadInFuncallBasic():
    interpreter_test("def f(a, b, c) [a, b, c]; f(1, ...[2, 3])", "[1, 2, 3]")


def test_SpreadInFuncallMap():
    interpreter_test(
        "def f(a, b, c) [a, b, c]; f(...<<<'c' => 3, 'a' => 1, 'b' => 2>>>)",
        "[1, 2, 3]",
    )


def test_SpreadInFuncall():
    interpreter_test(
        "def f(args...) args...; f(1, ...[2, 3, 4], 5)", "[1, 2, 3, 4, 5]"
    )


def test_SpreadInFuncallWithIdentifier():
    interpreter_test(
        "def f(args...) args...; def a = [2, 3, 4]; f(1, ...a, 5)",
        "[1, 2, 3, 4, 5]",
    )


def test_TestOneArg():
    interpreter_test("(fn(a) a)(12)", "12")


def test_TestTwoArgs():
    interpreter_test("(fn(a, b) [a, b])(1, 2)", "[1, 2]")


def test_TestTwoArgsKeywords1():
    interpreter_test("(fn(a, b) [a, b])(a = 1,  b=2)", "[1, 2]")


def test_TestTwoArgsKeywords2():
    interpreter_test("(fn(a, b) [a, b])(b = 2,  a=1)", "[1, 2]")


def test_TestTwoArgsKeywords3():
    interpreter_test("(fn(a, b) [a, b])(1,  b=2)", "[1, 2]")


def test_TestTwoArgsKeywords4():
    interpreter_test("(fn(a, b) [a, b])(2,  a=1)", "[1, 2]")


def test_TestRestArg():
    interpreter_test("(fn(a...) a...)(1, 2)", "[1, 2]")


def test_TestMixed1():
    interpreter_test("(fn(a, b, c...) [a, b, c...])(1, 2)", "[1, 2, []]")


def test_TestMixed2():
    interpreter_test("(fn(a, b, c...) [a, b, c...])(1, 2, 3)", "[1, 2, [3]]")


def test_TestMixed3():
    interpreter_test(
        "(fn(a, b, c...) [a, b, c...])(1, 2, 3, 4)", "[1, 2, [3, 4]]"
    )


def test_TestMixedWithDefaults1():
    interpreter_test("(fn(a=1, b=2, c...) [a, b, c...])()", "[1, 2, []]")


def test_TestMixedWithDefaults2():
    interpreter_test("(fn(a=1, b=2, c...) [a, b, c...])(1)", "[1, 2, []]")


def test_TestMixedWithDefaults3():
    interpreter_test("(fn(a=1, b=2, c...) [a, b, c...])(1, 2)", "[1, 2, []]")


def test_TestMixedWithDefaults4():
    interpreter_test("(fn(a=1, b=2, c...) [a, b, c...])(a=11)", "[11, 2, []]")


def test_TestMixedWithDefaults5():
    interpreter_test("(fn(a=1, b=2, c...) [a, b, c...])(b=12)", "[1, 12, []]")


def test_TestMixedWithDefaults6():
    interpreter_test(
        "(fn(a=1, b=2, c...) [a, b, c...])(1, 3, 4, b=12)", "[1, 12, [3, 4]]"
    )


def test_DefDestructure1():
    interpreter_test("def [a, b] = [1, 2]; [a, b]", "[1, 2]")


def test_DefDestructure2():
    interpreter_test("def [a] = [1, 2]; a", "1")


def test_DefDestructure3():
    interpreter_test("def [a, b, c] = <<1, 2, 3>>; c", "3")


def test_DefDestructure4():
    interpreter_test("def [a, b, c] = [1, 2]", "NULL")


def test_AssignDestructure1():
    interpreter_test("def a = 1; def b = 1; [a, b] = [1, 2]; [a, b]", "[1, 2]")


def test_AssignDestructure2():
    interpreter_test("def a = 1; [a] = [2, 3]; a", "2")


def test_SwapUsingDestructure():
    interpreter_test("def a = 1; def b = 2; [a, b] = [b, a]; [a, b]", "[2, 1]")


def test_All():
    interpreter_test("all([2, 4, 6], fn(x) x % 2 == 0)", "TRUE")


def test_Methods1():
    interpreter_test("'abcdef'!>starts_with('abc')", "TRUE")


def test_Methods2():
    interpreter_test("' xy '!>trim()", "'xy'")


def test_Methods3():
    interpreter_test("require List; [1, 2, 3]!>List->reverse()", "[3, 2, 1]")


def test_Methods4():
    interpreter_test("[2, 4, 6] !> all(fn(x) x % 2 == 0)", "TRUE")


def test_Methods5():
    interpreter_test("12 !> max(2)", "12")


def test_Methods6():
    interpreter_test(
        "require List; [1, 2, 3] !> List->reverse() !> join(sep = '-')",
        "'3-2-1'",
    )


def test_WhileStringTest():
    interpreter_test(
        "def s = '012'; while s !> starts_with('0') "
        "do s = s !> substr(1); end;",
        "'12'",
    )


def test_NumConv1():
    interpreter_test("int('-5')", "-5")


# interpreter_test_exception("NumConv2", "int('-5.5')")


def test_NumConv3():
    interpreter_test("int(-5.0)", "-5")


def test_NumConv4():
    interpreter_test("int(-5)", "-5")


def test_NumConv5():
    interpreter_test("decimal('-5')", "-5.0")


def test_NumConv6():
    interpreter_test("decimal('-5.5')", "-5.5")


def test_NumConv7():
    interpreter_test("decimal(-5.0)", "-5.0")


def test_NumConv8():
    interpreter_test("decimal(-5)", "-5.0")


def test_TestDoFinally1():
    interpreter_test(
        "def a = 1; def b = 1; do a += 1; finally b += 2; end; [a, b]",
        "[2, 3]",
    )


def test_TestDoFinally2():
    interpreter_test(
        "def a = 1; def f(x) a = x + 1; def b = 1; do f(3); "
        "finally b += 2; end; [a, b]",
        "[4, 3]",
    )


def test_DerefProperty():
    interpreter_test("def a = <<<'x' => 1, 'y' => 2>>>; a->y", "2")


def test_MapLiteralImplicitString():
    interpreter_test("<<<x => 1, y => 2>>>", "<<<'x' => 1, 'y' => 2>>>")


def test_PipelineLambda():
    interpreter_test("[1, 2, 3] !> (fn(lst) lst[2])()", "3")


def test_IfThenElifThenElse():
    interpreter_test(
        "if 1 == 2 then 3 elif 1 == 3 then 4 elif 1 == 1 then 5 else 6", "5"
    )


def test_ForDestructuringListList():
    interpreter_test(
        "def a = 0; for [x, y, z] in [[1, 2, 3], [4, 5, 6]] "
        "do a += x + y + z; end; a;",
        "21",
    )


def test_ForDestructuringListSet():
    interpreter_test(
        "def a = 0; for [x, y, z] in [<<1, 2, 3>>, <<4, 5, 6>>] "
        "do a += x + y + z; end; a;",
        "21",
    )


def test_ForDestructuringSetList():
    interpreter_test(
        "def a = 0; for [x, y, z] in <<[1, 2, 3], [4, 5, 6]>> "
        "do a += x + y + z; end; a;",
        "21",
    )


def test_ForDestructuringSetSet():
    interpreter_test(
        "def a = 0; for [x, y, z] in << <<1, 2, 3>>, <<4, 5, 6>> >> "
        "do a += x + y + z; end; a;",
        "21",
    )


def test_MapEquality1():
    interpreter_test("<<<a => 1, b => 2>>> == <<<b => 2, a => 1>>>", "TRUE")


def test_MapEquality2():
    interpreter_test("<<<a => 1, b => 1>>> == <<<b => 2, a => 1>>>", "FALSE")


def test_MapEquality3():
    interpreter_test("<<<a => 1, c => 2>>> == <<<b => 2, a => 1>>>", "FALSE")


def test_MapAsInt():
    interpreter_test("int(<<<a => 12>>>)", "1")


def test_MapAsBool1():
    interpreter_test("boolean(<<<a => 12>>>)", "TRUE")


def test_MapAsBool2():
    interpreter_test("boolean(<<<>>>)", "FALSE")


def test_ObjectBasics1():
    interpreter_test(
        "def o = object(); o->a = 12; o->b = fn(x) 2 * x; o->a", "12"
    )


def test_ObjectBasics2():
    interpreter_test(
        "def o = object(); o->a = 12; o->b = fn(x) 2 * x; o",
        "<*a=12, b=<#lambda>*>",
    )


def test_ObjectLiteral():
    interpreter_test("def o = <*a = 2, b=3, c=2*3*>; o->c", "6")


def test_test_for_map_values():
    interpreter_test(
        "def result = []; def obj = <<<a=>1, b=>2, c=>3>>>; "
        "for o in values obj do append(result, o) end; result;",
        "[1, 2, 3]",
    )


def test_TestForMapDefault():
    interpreter_test(
        "def result = []; def obj = <<<a=>1, b=>2, c=>3>>>; "
        "for o in obj do append(result, o); end; result;",
        "[1, 2, 3]",
    )


def test_TestForMapKeys():
    interpreter_test(
        "def result = []; def obj = <<<a=>1, b=>2, c=>3>>>; "
        "for o in keys obj do append(result, o); end; result;",
        "['a', 'b', 'c']",
    )


def test_TestForMapEntries():
    interpreter_test(
        "def result = []; def obj = <<<a=>1, b=>2, c=>3>>>; "
        "for o in entries obj do append(result, o); end; result;",
        "[['a', 1], ['b', 2], ['c', 3]]",
    )


def test_TestForObjectValues():
    interpreter_test(
        "def result = []; def obj = <*a=1, b=2, c=3*>; "
        "for o in values obj append(result, o); result;",
        "[1, 2, 3]",
    )


def test_TestForObjectDefault():
    interpreter_test(
        "def result = []; def obj = <*a=1, b=2, c=3*>; "
        "for o in obj append(result, o); result;",
        "[1, 2, 3]",
    )


def test_TestForObjectKeys():
    interpreter_test(
        "def result = []; def obj = <*a=1, b=2, c=3*>; "
        "for o in keys obj append(result, o); result;",
        "['a', 'b', 'c']",
    )


def test_TestForObjectEntries():
    interpreter_test(
        "def result = []; def obj = <*a=1, b=2, c=3*>; "
        "for o in entries obj append(result, o); result;",
        "[['a', 1], ['b', 2], ['c', 3]]",
    )


def test_MapDefaultValue():
    interpreter_test("def m = <<<'a' => 1>>>; m['b', 0]", "0")


def test_MapIncrementDefaultValue():
    interpreter_test("def m = <<<>>>; m['a', 0] += 1; m['a']", "1")
