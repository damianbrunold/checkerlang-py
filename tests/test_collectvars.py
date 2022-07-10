import json

from ckl.functions import get_base_environment
from ckl.parser import parse_script


def get_freevars(node, environment):
    free_vars = []
    bound_vars = []
    additional_bound_vars = []
    node.collectVars(free_vars, bound_vars, additional_bound_vars)
    return [var for var in sorted(free_vars) if not environment.isDefined(var)]


def collectvars_test(code, expected):
    assert (
        get_freevars(parse_script(code, "{test}"), get_base_environment()) == expected
    )


def test_vars_simple():
    collectvars_test("abc is 0", ["abc"])


def test_vars_multi():
    collectvars_test("abc is 0 and bcd is not 0", ["abc","bcd"])


def test_vars_def():
    collectvars_test("def abc = 12; abc > 0 and bcd is not 0", ["bcd"])


def test_vars_def_with_varref():
    collectvars_test("def abc = bcd * 2; abc > 0 and bcd < 12", ["bcd"])


def test_func_def_and_use():
    collectvars_test("def dup = fn(x) 2 * x; abc > 0 and dup(bcd) < 12", ["abc","bcd"])


def test_lambda_call():
    collectvars_test("(fn(x) 2 * x)(abc)", ["abc"])


def test_lambda():
    collectvars_test("fn(x) 2 * x", [])


def test_list_comprehension():
    collectvars_test("[2*x for x in y]", ["y"])


def test_list_comprehension_with_condition():
    collectvars_test("[2*x for x in y if x < 12]", ["y"])


def test_cascaded_lambdas():
    collectvars_test("def a = fn(y) fn(x) y * x; a(abc)(2)", ["abc"])


def test_lambd_ordering():
    collectvars_test(
        "def a = fn(y) do def b = fn(x) 2 * c(x); def c = fn(x) d * x; end",
        ["d"]
    )


def test_lambda_ordering_with_free_call():
    collectvars_test(
        "def a = fn(y) do b(y); def b = fn(x) 2 * x; end;",
        ["b"]
    )


def test_lambda_ordering_global():
    collectvars_test("def b = fn(x) 2 * c(x); def c = fn(x) d * x", ["d"])


def test_predefined_functions():
    collectvars_test("lower(a) < 'a'", ["a"])
