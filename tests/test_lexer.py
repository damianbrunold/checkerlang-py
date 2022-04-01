from ckl.lexer import Lexer


def test_simple():
    assert (
        str(Lexer.init("1_6_V04 not empty", "-"))
        == "[1_6_V04 (identifier), not (keyword), empty (identifier)] @ 0"
    )


def test_quotes():
    assert (
        str(Lexer.init("a \"double\" b 'single' c"))
        == "[a (identifier), double (string), b (identifier), "
        "single (string), c (identifier)] @ 0"
    )


def test_num_escapes():
    assert str(Lexer.init("\x58Y\x5a")) == "[XYZ (identifier)] @ 0"


def test_pattern():
    assert str(Lexer.init("//abc//")) == "[//abc// (pattern)] @ 0"


def test_in():
    assert (
        str(Lexer.init("feld1 in ['a', 'bb', 'ccc']"))
        == "[feld1 (identifier), in (keyword), [ (interpunction), "
        "a (string), , (interpunction), bb (string), , (interpunction), "
        "ccc (string), ] (interpunction)] @ 0"
    )


def test_complex():
    assert (
        str(
            Lexer.init(
                "(felda beginnt mit 'D12') oder (feldb <= 1.3*(feldc-feldd/2))"
            )
        )
        == "[( (interpunction), felda (identifier), beginnt (identifier), "
        "mit (identifier), D12 (string), ) (interpunction), "
        "oder (identifier), ( (interpunction), feldb (identifier), "
        "<= (operator), 1.3 (decimal), * (operator), ( (interpunction), "
        "feldc (identifier), - (operator), feldd (identifier), / (operator), "
        "2 (int), ) (interpunction), ) (interpunction)] @ 0"
    )


def test_compare():
    assert (
        str(Lexer.init("1>2 d"))
        == "[1 (int), > (operator), 2 (int), d (identifier)] @ 0"
    )


def test_non_zero():
    assert (
        str(Lexer.init("non_zero('12', '3')"))
        == "[non_zero (identifier), ( (interpunction), 12 (string), "
        ", (interpunction), 3 (string), ) (interpunction)] @ 0"
    )


def test_set_literal():
    assert (
        str(Lexer.init("a in <<1, 2, 3>>"))
        == "[a (identifier), in (keyword), << (interpunction), 1 (int), "
        ", (interpunction), 2 (int), , (interpunction), 3 (int), "
        ">> (interpunction)] @ 0"
    )


def test_map_literal():
    assert (
        str(Lexer.init("def m = <<<1 => 100, 2=>200 >>>"))
        == "[def (keyword), m (identifier), = (operator), "
        "<<< (interpunction), 1 (int), => (interpunction), "
        "100 (int), , (interpunction), 2 (int), => (interpunction), "
        "200 (int), >>> (interpunction)] @ 0"
    )


def test_list():
    assert (
        str(Lexer.init("a in [1, 2, 3]"))
        == "[a (identifier), in (keyword), [ (interpunction), 1 (int), "
        ", (interpunction), 2 (int), , (interpunction), 3 (int), "
        "] (interpunction)] @ 0"
    )


def test_list_add_int():
    assert (
        str(Lexer.init("[1, 2, 3] + 4"))
        == "[[ (interpunction), 1 (int), , (interpunction), 2 (int), "
        ", (interpunction), 3 (int), ] (interpunction), + (operator), "
        "4 (int)] @ 0"
    )


def test_spread_operator_identifier():
    assert (
        str(Lexer.init("...a")) == "[... (interpunction), a (identifier)] @ 0"
    )


def test_spread_operator_list():
    assert (
        str(Lexer.init("...[1, 2]"))
        == "[... (interpunction), [ (interpunction), 1 (int), "
        ", (interpunction), 2 (int), ] (interpunction)] @ 0"
    )


def test_spread_operator_funcall():
    assert (
        str(Lexer.init("f(a, ...b, c)"))
        == "[f (identifier), ( (interpunction), a (identifier), "
        ", (interpunction), ... (interpunction), b (identifier), "
        ", (interpunction), c (identifier), ) (interpunction)] @ 0"
    )


def test_invoke_operator():
    assert (
        str(Lexer.init("a!>b"))
        == "[a (identifier), !> (operator), b (identifier)] @ 0"
    )


def test_string_literal_with_newline():
    assert str(Lexer.init("'one\\ntwo'")) == "[one\\ntwo (string)] @ 0"


def test_deref_property():
    assert (
        str(Lexer.init("a->b ->c -> d"))
        == "[a (identifier), -> (operator), b (identifier), "
        "-> (operator), c (identifier), -> (operator), "
        "d (identifier)] @ 0"
    )


def test_if_then_elif_else_keywords():
    assert (
        str(Lexer.init("if a then b elif c then d else e"))
        == "[if (keyword), a (identifier), then (keyword), "
        "b (identifier), elif (keyword), c (identifier), "
        "then (keyword), d (identifier), else (keyword), "
        "e (identifier)] @ 0"
    )
