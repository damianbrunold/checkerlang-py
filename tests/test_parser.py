import pytest

from ckl.errors import CklSyntaxError
from ckl.parser import parse_script

def test_simple():
    assert str(parse_script("eins")) == "eins"


def test_addition():
    assert str(parse_script("2 + 3")) == "(add 2, 3)"


def test_if():
    assert (
        str(parse_script("if 1>2 then TRUE else FALSE"))
        == "(if (greater 1, 2): TRUE else: FALSE)"
    )


def test_in():
    assert (
        str(parse_script("feld1 in ['a', 'bb', 'ccc']"))
        == "(feld1 in ['a', 'bb', 'ccc'])"
    )


def test_in_with_set():
    assert (
        str(parse_script("feld1 in <<'a', 'bb', 'ccc'>>"))
        == "(feld1 in <<'a', 'bb', 'ccc'>>)"
    )


def test_is_zero():
    assert str(parse_script("1 is zero")) == "(is_zero 1)"


def test_literal_map():
    assert (
        str(parse_script("<<<'a' => 1, 'bb' => -1, 'ccc' => 100>>>"))
        == "<<<'a' => 1, 'bb' => -1, 'ccc' => 100>>>"
    )


def test_literal_set():
    assert str(parse_script("<<1, 2, 2, 3>>")) == "<<1, 2, 2, 3>>"


def test_list_add_int():
    assert str(parse_script("[1, 2, 3] + 4")) == "(add [1, 2, 3], 4)"


def test_relop1():
    assert str(parse_script("a < b")) == "(less a, b)"


def test_relop2():
    assert str(parse_script("a < b < c")) == "((less a, b) and (less b, c))"


def test_relop3():
    assert (
        str(parse_script("a <= b < c == d"))
        == "((less_equals a, b) and (less b, c) and (equals c, d))"
    )


def test_non_zero_funcall():
    assert str(parse_script("non_zero('12', '3')")) == "(non_zero '12', '3')"


def test_too_many_tokens():
    with pytest.raises(CklSyntaxError):
        parse_script("1 + 1 1")


def test_not_enough_tokens():
    with pytest.raises(CklSyntaxError):
        parse_script("1 + ")


def test_missing_then():
    with pytest.raises(CklSyntaxError):
        parse_script("if 1 < 2 else FALSE")


def test_if_then_or_expr():
    assert (
        str(parse_script("if a == 1 then b in c or d == 9999"))
        == "(if (equals a, 1): ((b in c) or (equals d, 9999)) else: TRUE)"
    )


def test_if_then_elif():
    assert (
        str(
            parse_script(
                "if a == 1 then b elif c == 1 or d == 2 "
                "then b in c or d == 9999"
            )
        )
        == "(if (equals a, 1): b if ((equals c, 1) or (equals d, 2)): "
           "((b in c) or (equals d, 9999)) else: TRUE)"
    )


def test_missing_closing_parens():
    with pytest.raises(CklSyntaxError):
        parse_script("2 * (3 + 4( - 3")



def test_lambda():
    assert (
        str(parse_script("fn(a, b=3) string(a) * b(2, 3)"))
        == "(lambda a, b=3, (mul (string a), (b 2, 3)))"
    )


def test_while():
    assert (
        str(parse_script("while x > 0 do x = x - 1; end"))
        == "(while (greater x, 0) do (x = (sub x, 1)))"
    )


def test_spread_identifier():
    assert str(parse_script("f(a, ...b, c)")) == "(f a, ...b, c)"


def test_spread_list():
    assert str(parse_script("f(a, ...[1, 2], c)")) == "(f a, ...[1, 2], c)"


def test_def_destructure():
    assert str(parse_script("def [a, b] = [1, 2]")) == "(def [a,b] = [1, 2])"


def test_assign_destructure():
    assert str(parse_script("[a, b] = [1, 2]")) == "([a,b] = [1, 2])"


def test_pipeline():
    assert (
        str(parse_script('0 !> sprintf(fmt="part2: {0}") !> println()'))
        == "(println (sprintf 0, 'part2: {0}'))"
    )
