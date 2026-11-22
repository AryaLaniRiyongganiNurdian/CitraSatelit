from collections import defaultdict
from graphlib import TopologicalSorter
from itertools import pairwise, product

import pytest

from src.core import boolean_lab as lab


@pytest.mark.parametrize("expression,inputs,expected", [
    ("a+b^c.d'", {"a": 1, "b": 1, "c": 1, "d": 0}, 1),
    ("a+b^c.d'", {"a": 0, "b": 1, "c": 1, "d": 1}, 1),
    ("(a+b)^c", {"a": 1, "b": 0, "c": 1}, 0),
    ("ab'", {"a": 1, "b": 0}, 1),
    ("!ab", {"a": 1, "b": 0}, 0),
    ("~a' * 1", {"a": 1}, 1),
    ("!(a+b)'", {"a": 0, "b": 0}, 0),
    ("a\u2295b", {"a": 1, "b": 0}, 1),
    ("(a+b)(a'+b')", {"a": 0, "b": 1}, 1),
    ("(0+1)'", {}, 0),
])
def test_parser_precedence_and_notation(expression, inputs, expected):
    assert lab.eval_expr(lab.parse_expr(expression), inputs) == expected


@pytest.mark.parametrize("expression", [
    "", "   ", "()", "(a", "a)", "a+", "a..b", "'a", "a+^b", "!", "a( )", "a&b", "2", "a=b",
    "a+b+c+d+e+f+g",
])
def test_parse_errors_are_expression_errors(expression):
    with pytest.raises(lab.ExpressionError):
        lab.parse_expr(expression)


def test_xor_truth_table_minterms_and_canonical_sop():
    assert lab.XOR_DEFINITION == "ab'+a'b"
    table = lab.truth_table(lab.XOR_DEFINITION)
    assert table["variables"] == ["a", "b"]
    assert table["rows"] == [
        {"inputs": [0, 0], "output": 0},
        {"inputs": [0, 1], "output": 1},
        {"inputs": [1, 0], "output": 1},
        {"inputs": [1, 1], "output": 0},
    ]
    assert table["rows"] == lab.truth_table("a^b")["rows"]
    assert lab.minterms("a^b") == [1, 2]
    assert lab.sop_canonical("a^b") == "a'b+ab'"
    assert lab.sop_canonical("0") == "0"
    assert lab.sop_canonical("1") == "1"
    assert lab.equivalent(lab.XOR_DEFINITION, "a^b")


def test_truth_table_variable_order_and_limits():
    assert lab.minterms("a", variables="ba") == [1, 3]
    assert len(lab.truth_table("a+b+c+d+e+f")["rows"]) == 64
    with pytest.raises(lab.ExpressionError):
        lab.equivalent("a+b+c+d", "e+f+g")


@pytest.mark.parametrize("lhs,rhs", [
    ("a+a'b", "a+b"), ("(a+b)'", "a'b'"), ("(ab)'", "a'+b'"),
])
def test_slide_boolean_identities(lhs, rhs):
    assert lab.equivalent(lhs, rhs)


def test_dual_of_slide_identity_and_constant_swap():
    left, right = lab.dual_expr("a+a'b"), lab.dual_expr("a+b")
    assert (left, right) == ("a(a'+b)", "ab")
    assert lab.equivalent(left, right)
    assert lab.dual_expr("a+0") == "a1"
    assert lab.equivalent(lab.dual_expr("a^b"), "(a^b)'")
    assert lab.equivalent(lab.dual_expr(lab.dual_expr("a^b+c")), "a^b+c")
    assert not lab.equivalent("a+b", "ab")


@pytest.mark.parametrize("variables,terms,simplified", [
    ("ab", [0, 2], "b'"),
    ("abc", [0, 2, 4, 6], "c'"),
    ("abc", [1, 3, 4, 5], "a'c+ab'"),
    ("abc", [1, 3, 5, 7], "c"),
    ("xyz", [3, 5, 6, 7], "xy+xz+yz"),
    ("abcd", [0, 2, 8, 10], "b'd'"),
])
def test_kmap_slide_cases_round_trip(variables, terms, simplified):
    result = lab.kmap(variables, terms)
    assert result["variables"] == list(variables)
    assert result["simplified"].replace(" ", "") == simplified

    original = "+".join(
        "".join(variable if bit == "1" else variable + "'" for variable, bit in zip(
            variables, f"{index:0{len(variables)}b}",
        ))
        for index in terms
    )
    assert lab.equivalent(result["simplified"], original)
    assert lab.minterms(result["simplified"], variables) == terms
    assert set().union(*(set(group["cells"]) for group in result["selected"])) == set(terms)


def test_kmap_matches_documented_layout_and_marks_wrapping_groups():
    three = lab.kmap(3, [1, 3, 4, 5])
    assert three["row_vars"] == ["a"]
    assert three["col_vars"] == ["b", "c"]
    assert three["row_labels"] == ["0", "1"]
    assert three["col_labels"] == ["00", "01", "11", "10"]
    assert three["grid"] == [[0, 1, 1, 0], [1, 1, 0, 0]]
    assert three["cell_minterm"] == [[0, 1, 3, 2], [4, 5, 7, 6]]
    assert len(three["prime_implicants"]) == 3
    assert all(not group["wraps"] for group in three["selected"])

    four = lab.kmap(4, [0, 2, 8, 10])
    assert four["row_vars"] == ["a", "b"]
    assert four["col_vars"] == ["c", "d"]
    assert four["row_labels"] == four["col_labels"] == ["00", "01", "11", "10"]
    assert four["selected"] == four["prime_implicants"]
    assert four["selected"][0] == {
        "term": "b'd'", "size": 4, "cells": [0, 2, 8, 10],
        "cells_rc": [[0, 0], [0, 3], [3, 0], [3, 3]], "wraps": True,
    }


def test_kmap_greedy_cover_when_there_are_no_essential_primes():
    terms = [0, 1, 2, 5, 6, 7]
    result = lab.kmap(3, terms)

    assert all(sum(term in group["cells"] for group in result["prime_implicants"]) > 1 for term in terms)
    assert result == lab.kmap(3, reversed(terms))
    assert lab.minterms(result["simplified"], "abc") == terms
    assert set().union(*(set(group["cells"]) for group in result["selected"])) == set(terms)


def test_kmap_constant_functions_and_invalid_inputs():
    assert lab.kmap(2, [])["simplified"] == "0"
    assert lab.kmap(4, range(16))["simplified"] == "1"
    for variables, terms in [(5, [0]), (2, [-1]), (3, [8])]:
        with pytest.raises(lab.ExpressionError):
            lab.kmap(variables, terms)


def test_law_catalog_contains_eight_identities_and_valid_proof_steps():
    identities = {
        "a+a'b=a+b", "a(a'+b)=ab", "(a+b)'=a'b'", "(ab)'=a'+b'",
        "a+ab=a", "a(a+b)=a", "a\u2295b=(a+b)(ab)'", "a\u2295b=ab'+a'b",
    }
    assert identities <= lab.LAW_PROOFS.keys()
    assert "a+0=a" not in lab.LAW_PROOFS
    for identity, steps in lab.LAW_PROOFS.items():
        lhs, rhs = identity.split("=")
        assert len(steps) >= 2
        assert steps[0]["expression"] == lhs
        assert steps[-1]["expression"] == rhs
        assert all(set(step) == {"expression", "reason"} and step["reason"] for step in steps)
        for first, second in pairwise(steps):
            assert lab.equivalent(first["expression"], second["expression"]), identity


def test_circuit_matches_schema_and_evaluates_as_directed_acyclic_graph():
    expression = "a(b+c')^d+0"
    circuit = lab.to_circuit(expression)
    assert set(circuit) == {"nodes", "edges", "output_id"}
    nodes = {node["id"]: node for node in circuit["nodes"]}
    assert len(nodes) == len(circuit["nodes"])
    assert circuit["output_id"] in nodes
    assert {node["type"] for node in nodes.values()} == {"input", "not", "and", "or", "xor"}
    assert all(set(node) == {"id", "type", "label"} for node in nodes.values())

    incoming = defaultdict(list)
    for edge in circuit["edges"]:
        assert set(edge) == {"from", "to"}
        assert edge["from"] in nodes and edge["to"] in nodes
        incoming[edge["to"]].append(edge["from"])
    order = list(TopologicalSorter({i: incoming[i] for i in nodes}).static_order())
    assert all(edge["from"] != circuit["output_id"] for edge in circuit["edges"])
    for bits in product((0, 1), repeat=4):
        inputs = dict(zip("abcd", bits))
        values = {}
        for i in order:
            node = nodes[i]
            kind = node["type"]
            args = [values[parent] for parent in incoming[i]]
            if kind == "input":
                label = node["label"]
                assert not args
                values[i] = int(label) if label in ("0", "1") else inputs[label]
            elif kind == "not":
                assert len(args) == 1
                values[i] = 1 - args[0]
            else:
                assert len(args) == 2
                left, right = args
                values[i] = {"and": left & right, "or": left | right, "xor": left ^ right}[kind]
        assert values[circuit["output_id"]] == lab.eval_expr(expression, inputs)
