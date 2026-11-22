from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from numbers import Integral


class ExpressionError(ValueError):
    """An invalid Boolean expression or assignment."""


@dataclass(frozen=True)
class _Node:
    op: str
    children: tuple[_Node, ...] = ()
    label: str = ""


_OPERATORS = {"+": "or", "^": "xor", ".": "and"}
_PRECEDENCE = {"or": 1, "xor": 2, "and": 3, "not": 4, "input": 5}
_SYMBOLS = {"or": "+", "xor": "^", "and": ""}


class _Parser:
    def __init__(self, expression: str):
        aliases = str.maketrans({"*": ".", "~": "!", "\u2295": "^"})
        self.source = "".join(expression.split()).translate(aliases)
        self.index = 0

    def peek(self) -> str:
        return self.source[self.index:self.index + 1]

    def expression(self, minimum: int = 1) -> _Node:
        left = self.unary()
        while True:
            token = self.peek()
            op = _OPERATORS.get(token)
            implicit = token.isalpha() or token in ("(", "!", "0", "1")
            if implicit:
                op = "and"
            if op is None or _PRECEDENCE[op] < minimum:
                return left
            if not implicit:
                self.index += 1
            right = self.expression(_PRECEDENCE[op] + 1)
            left = _Node(op, (left, right))

    def unary(self) -> _Node:
        token = self.peek()
        self.index += 1
        if token == "!":
            return _Node("not", (self.unary(),))
        if token == "(":
            node = self.expression()
            if self.peek() != ")":
                raise ExpressionError("expected closing parenthesis")
            self.index += 1
        elif token.isalpha() or token in ("0", "1"):
            node = _Node("input", label=token)
        else:
            raise ExpressionError(f"expected an operand, got {token or 'end of expression'!r}")

        while self.peek() == "'":
            self.index += 1
            node = _Node("not", (node,))
        return node


def _variables(node: _Node) -> set[str]:
    variables = set()
    pending = [node]
    while pending:
        current = pending.pop()
        if current.op == "input" and current.label.isalpha():
            variables.add(current.label)
        pending.extend(current.children)
    return variables


def _ordered_variables(found: set[str], variables=None) -> tuple[str, ...]:
    names = tuple(sorted(found)) if variables is None else tuple(variables)
    if len(names) > 6:
        raise ExpressionError("at most six variables are supported")
    if any(not isinstance(name, str) or len(name) != 1 or not name.isalpha() for name in names):
        raise ExpressionError("variables must be single letters")
    if len(set(names)) != len(names) or not found.issubset(names):
        raise ExpressionError("variables must be unique and contain all expression variables")
    return names


def parse_expr(expression: str) -> _Node:
    """Parse one expression with the precedence NOT, AND, XOR, OR."""
    if not isinstance(expression, str):
        raise ExpressionError("expression must be a string")
    parser = _Parser(expression)
    node = parser.expression()
    if parser.peek():
        raise ExpressionError(f"unexpected token {parser.peek()!r}")
    _ordered_variables(_variables(node))
    return node


def _tree(expression) -> _Node:
    return expression if isinstance(expression, _Node) else parse_expr(expression)


def _evaluate(node: _Node, values) -> int:
    if node.op == "input":
        if node.label in ("0", "1"):
            return int(node.label)
        if node.label not in values or values[node.label] not in (0, 1):
            raise ExpressionError(f"expected a bit for variable {node.label!r}")
        return int(values[node.label])
    if node.op == "not":
        return 1 - _evaluate(node.children[0], values)

    left, right = (_evaluate(child, values) for child in node.children)
    if node.op == "and":
        return left & right
    if node.op == "xor":
        return left ^ right
    return left | right


def eval_expr(expression, values) -> int:
    """Evaluate an expression string or a parsed expression for one assignment."""
    return _evaluate(_tree(expression), values)


def _format(node: _Node, minimum: int = 0) -> str:
    precedence = _PRECEDENCE[node.op]
    if node.op == "input":
        return node.label
    if node.op == "not":
        text = _format(node.children[0], precedence) + "'"
    else:
        text = _SYMBOLS[node.op].join(_format(child, precedence) for child in node.children)
    return f"({text})" if precedence < minimum else text


def truth_table(expression, variables=None) -> dict:
    """Return rows in binary order with the first variable as the most significant bit."""
    node = _tree(expression)
    names = _ordered_variables(_variables(node), variables)
    rows = [
        {"inputs": list(bits), "output": _evaluate(node, dict(zip(names, bits)))}
        for bits in product((0, 1), repeat=len(names))
    ]
    return {"normalized": _format(node), "variables": list(names), "rows": rows}


def minterms(expression, variables=None) -> list[int]:
    return [index for index, row in enumerate(truth_table(expression, variables)["rows"]) if row["output"]]


def _product_term(names, bits) -> str:
    return "".join(name if bit else name + "'" for name, bit in zip(names, bits) if bit is not None) or "1"


def sop_canonical(expression, variables=None) -> str:
    table = truth_table(expression, variables)
    terms = [
        _product_term(table["variables"], row["inputs"])
        for row in table["rows"]
        if row["output"]
    ]
    return "+".join(terms) or "0"


def equivalent(lhs, rhs) -> bool:
    left, right = _tree(lhs), _tree(rhs)
    names = _ordered_variables(_variables(left) | _variables(right))
    for bits in product((0, 1), repeat=len(names)):
        values = dict(zip(names, bits))
        if _evaluate(left, values) != _evaluate(right, values):
            return False
    return True


def _dual(node: _Node) -> _Node:
    if node.op == "input":
        return _Node("input", label={"0": "1", "1": "0"}.get(node.label, node.label))

    children = tuple(_dual(child) for child in node.children)
    if node.op == "xor":
        # Complementing both inputs leaves XOR unchanged, so its dual is XNOR.
        return _Node("not", (_Node("xor", children),))
    return _Node({"and": "or", "or": "and", "not": "not"}[node.op], children)


def dual_expr(expression) -> str:
    return _format(_dual(_tree(expression)))


def to_circuit(expression) -> dict:
    """Build the Circuit DAG, using labelled input nodes for variables and constants."""
    nodes = []
    edges = []
    inputs = {}

    def visit(node: _Node) -> str:
        if node.op == "input" and node.label in inputs:
            return inputs[node.label]

        sources = [visit(child) for child in node.children]
        node_id = f"n{len(nodes)}"
        nodes.append({"id": node_id, "type": node.op, "label": node.label or node.op.upper()})
        edges.extend({"from": source, "to": node_id} for source in sources)
        if node.op == "input":
            inputs[node.label] = node_id
        return node_id

    output_id = visit(_tree(expression))
    return {"nodes": nodes, "edges": edges, "output_id": output_id}


def _prime_implicants(terms: set[int]) -> set[tuple[int, int]]:
    # A pair contains fixed bits and a mask of positions that can vary.
    layer = {(term, 0) for term in terms}
    primes = set()
    while layer:
        merged = set()
        next_layer = set()
        for first, second in combinations(layer, 2):
            left, mask = first
            right, other_mask = second
            difference = left ^ right
            if mask == other_mask and difference and difference.bit_count() == 1:
                merged.update((first, second))
                next_layer.add((left & ~difference, mask | difference))
        primes.update(layer - merged)
        layer = next_layer
    return primes


def _implicant_group(implicant, names, terms, coordinates) -> dict:
    fixed, mask = implicant
    bit_values = [
        None if mask & (1 << shift) else (fixed >> shift) & 1
        for shift in range(len(names) - 1, -1, -1)
    ]
    cells = sorted(term for term in terms if term & ~mask == fixed)
    positions = [coordinates[cell] for cell in cells]
    wraps = any(max(axis) - min(axis) + 1 > len(set(axis)) for axis in zip(*positions))
    return {
        "cells": cells,
        "cells_rc": positions,
        "term": _product_term(names, bit_values),
        "size": len(cells),
        "wraps": wraps,
    }


def _select_implicants(groups, terms) -> list[dict]:
    cells = [set(group["cells"]) for group in groups]
    selected = set()
    for term in terms:
        candidates = [index for index, covered in enumerate(cells) if term in covered]
        if len(candidates) == 1:
            selected.add(candidates[0])

    uncovered = terms.difference(*(cells[index] for index in selected))
    while uncovered:
        # Prefer greater new coverage, then larger groups, then expression order.
        index = min(
            (index for index in range(len(groups)) if index not in selected),
            key=lambda index: (-len(uncovered & cells[index]), -len(cells[index]), groups[index]["term"]),
        )
        selected.add(index)
        uncovered -= cells[index]
    return [groups[index] for index in sorted(selected)]


def _gray_labels(width: int) -> list[str]:
    return [f"{index ^ (index >> 1):0{width}b}" for index in range(1 << width)]


def kmap(variables, minterms) -> dict:
    """Arrange 2-4 variables in Gray order and simplify their on-set."""
    if isinstance(variables, Integral):
        if not 2 <= variables <= 4:
            raise ExpressionError("K-Maps require two to four variables")
        variables = "abcd"[:variables]
    names = _ordered_variables(set(), variables)
    if not 2 <= len(names) <= 4:
        raise ExpressionError("K-Maps require two to four variables")

    terms = set()
    for term in minterms:
        if not isinstance(term, Integral) or not 0 <= term < 1 << len(names):
            raise ExpressionError("minterms must be within the K-Map")
        terms.add(int(term))

    row_width = len(names) // 2
    rows = _gray_labels(row_width)
    columns = _gray_labels(len(names) - row_width)
    cells = [[int(row + column, 2) for column in columns] for row in rows]
    coordinates = {
        term: [row, col] for row, line in enumerate(cells) for col, term in enumerate(line)
    }
    groups = sorted(
        (_implicant_group(prime, names, terms, coordinates) for prime in _prime_implicants(terms)),
        key=lambda group: group["term"],
    )
    selected = _select_implicants(groups, terms)

    return {
        "variables": list(names),
        "row_vars": list(names[:row_width]),
        "col_vars": list(names[row_width:]),
        "row_labels": rows,
        "col_labels": columns,
        "grid": [[int(term in terms) for term in line] for line in cells],
        "cell_minterm": cells,
        "prime_implicants": groups,
        "selected": selected,
        "simplified": " + ".join(group["term"] for group in selected) or "0",
    }


XOR_DEFINITION = "ab'+a'b"


def _proof(*steps) -> list[dict[str, str]]:
    return [{"expression": expression, "reason": reason} for expression, reason in steps]


LAW_PROOFS = {
    "a+a'b=a+b": _proof(
        ("a+a'b", "Ekspresi awal."),
        ("(a+a')(a+b)", "Hukum distributif."),
        ("1(a+b)", "Komplemen a+a' bernilai 1."),
        ("a+b", "Identitas perkalian."),
    ),
    "a(a'+b)=ab": _proof(
        ("a(a'+b)", "Ekspresi awal."),
        ("aa'+ab", "Hukum distributif."),
        ("0+ab", "Komplemen aa' bernilai 0."),
        ("ab", "Identitas penjumlahan."),
    ),
    "(a+b)'=a'b'": _proof(
        ("(a+b)'", "Ekspresi awal."),
        ("a'b'", "Komplemen unik. Hasil kali (a+b)a'b' bernilai 0, dan jumlah "
         "(a+b)+a'b' = (a+b+a')(a+b+b') bernilai 1."),
    ),
    "(ab)'=a'+b'": _proof(
        ("(ab)'", "Ekspresi awal."),
        ("a'+b'", "Komplemen unik. Hasil kali ab(a'+b') bernilai 0, dan jumlah "
         "ab+(a'+b') = (a+a'+b')(b+a'+b') bernilai 1."),
    ),
    "a+ab=a": _proof(
        ("a+ab", "Ekspresi awal."),
        ("a(1+b)", "Faktorkan a."),
        ("a1", "Hukum dominasi."),
        ("a", "Identitas perkalian."),
    ),
    "a(a+b)=a": _proof(
        ("a(a+b)", "Ekspresi awal."),
        ("aa+ab", "Hukum distributif."),
        ("a+ab", "Idempotensi."),
        ("a", "Penyerapan penjumlahan."),
    ),
    "a\u2295b=(a+b)(ab)'": _proof(
        ("a\u2295b", "Ekspresi awal."),
        (XOR_DEFINITION, "Definisi XOR."),
        ("aa'+ab'+ba'+bb'", "Tambahkan suku nol aa' dan bb', lalu gunakan komutativitas."),
        ("(a+b)(a'+b')", "Faktorkan dengan hukum distributif."),
        ("(a+b)(ab)'", "Gunakan hukum De Morgan."),
    ),
    "a\u2295b=ab'+a'b": _proof(
        ("a\u2295b", "Ekspresi awal."),
        (XOR_DEFINITION, "Definisi XOR."),
    ),
}
