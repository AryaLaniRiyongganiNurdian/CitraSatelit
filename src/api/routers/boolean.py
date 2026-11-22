from fastapi import APIRouter

from src.api import schemas as s
from src.api.errors import ApiError, RESPONSES
from src.api.inspector import explain
from src.core import boolean_lab as lab

router = APIRouter(prefix="/boolean", responses=RESPONSES)


def parse(expression):
    try:
        return lab.parse_expr(expression)
    except lab.ExpressionError as exc:
        raise ApiError("EXPRESSION_PARSE_ERROR", "Sintaks ekspresi Boolean tidak valid.") from exc


@router.post("/truth-table", response_model=s.TruthTableResponse, response_model_exclude_unset=True)
def truth(req: s.TruthTableRequest):
    expr = parse(req.expression)
    table = lab.truth_table(expr)
    return table | dict(minterms=lab.minterms(expr), sop_canonical=lab.sop_canonical(expr),
                        circuit=lab.to_circuit(expr), inspector=explain("Tabel kebenaran", "parse", "table", "sop"))


@router.post("/prove", response_model=s.ProveResponse, response_model_exclude_unset=True)
def prove(req: s.ProveRequest):
    lhs, rhs = parse(req.lhs), parse(req.rhs)
    left, right = lab.truth_table(lhs), lab.truth_table(rhs)
    variables = sorted(set(left["variables"]) | set(right["variables"]))
    if len(variables) > 6:
        raise ApiError("EXPRESSION_PARSE_ERROR", "Pembuktian mendukung maksimal enam variabel.")
    left_rows = lab.truth_table(lhs, variables)["rows"]
    right_rows = lab.truth_table(rhs, variables)["rows"]
    rows, counterexample = [], None
    for lrow, rrow in zip(left_rows, right_rows):
        a, b = lrow["output"], rrow["output"]
        rows.append([*lrow["inputs"], a, b])
        if a != b and counterexample is None:
            counterexample = dict(inputs=lrow["inputs"], lhs=a, rhs=b)
    key = f"{left['normalized']}={right['normalized']}".replace("^", "⊕")
    proof = lab.LAW_PROOFS.get(key)
    dl, dr = lab.dual_expr(lhs), lab.dual_expr(rhs)
    ids = ("table-proof", "algebraic", "dual") if proof else ("table-proof", "dual")
    table = dict(columns=[*variables, "Kiri", "Kanan"], rows=rows)
    return dict(equivalent=counterexample is None, variables=variables, table=table, counterexample=counterexample,
                algebraic_proof=proof, dual=dict(lhs=dl, rhs=dr, equivalent=lab.equivalent(dl, dr)),
                inspector=explain("Bukti Boolean", *ids, detail={"table-proof": {"table": table}}))


@router.post("/xor-gate", response_model=s.XorGateResponse, response_model_exclude_unset=True)
def xor_gate():
    rows = lab.truth_table("a^b")["rows"]
    table = dict(columns=["a", "b", "XOR"], rows=[[*row["inputs"], row["output"]] for row in rows])
    return dict(definition=lab.XOR_DEFINITION, table=table, circuit=lab.to_circuit(lab.XOR_DEFINITION),
                verified=lab.equivalent(lab.XOR_DEFINITION, "a^b"),
                inspector=explain("Gerbang XOR", "definition", "table", "circuit"))


@router.post("/kmap", response_model=s.KMapResponse, response_model_exclude_unset=True)
def kmap(req: s.KMapRequest):
    return lab.kmap(req.variables, req.minterms) | {"inspector": explain("Peta Karnaugh", "grid", "groups", "result")}
