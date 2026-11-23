import { useId, useRef } from "react";
import { CircuitView } from "@/components/circuit-view";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DataTable, Empty, Panel, RequestState, Stats } from "@/components/workbench";
import { useInspector } from "@/contexts";
import { ApiError, post } from "@/lib/api";
import { useApiMutation } from "@/lib/workbench";
import type { ProofStep, ProveRequest, ProveResponse, TruthTableRequest, TruthTableResponse, XorGateResponse } from "@/types/api";

export const presets = [
  { label: "XOR", lhs: "ab'+a'b", rhs: "a^b" },
  { label: "Penyerapan", lhs: "a+a'b", rhs: "a+b" },
  { label: "De Morgan (OR)", lhs: "(a+b)'", rhs: "a'b'" },
  { label: "De Morgan (AND)", lhs: "(ab)'", rhs: "a'+b'" },
  { label: "Dualitas", lhs: "a(a'+b)", rhs: "ab" },
];

function parseError(error: Error | null) {
  return error instanceof ApiError && error.code === "EXPRESSION_PARSE_ERROR";
}

export function ProofSteps({ steps }: { steps: ProofStep[] }) {
  return <ol className="boolean-proof-steps">
    {steps.map((step, index) => <li key={index}><code>{step.expression}</code><p>{step.reason}</p></li>)}
  </ol>;
}

function TruthTable({ result }: { result: TruthTableResponse }) {
  return <div className="lab-stack">
    <Stats items={[
      { label: "Ekspresi normal", value: <code>{result.normalized}</code> },
      { label: "SOP kanonis", value: <code>{result.sop_canonical}</code> },
      { label: "Minterm", value: result.minterms.length ? result.minterms.join(", ") : "∅" },
    ]} />
    <Table aria-label="Tabel kebenaran ekspresi">
      <TableHeader><TableRow>
        {result.variables.map((variable) => <TableHead key={variable} scope="col">{variable}</TableHead>)}
        <TableHead scope="col">Keluaran</TableHead>
      </TableRow></TableHeader>
      <TableBody>{result.rows.map((row, index) => <TableRow key={index} data-output={row.output}>
        {row.inputs.map((bit, input) => <TableCell key={input}>{bit}</TableCell>)}
        <TableCell>{row.output}</TableCell>
      </TableRow>)}</TableBody>
    </Table>
    <CircuitView circuit={result.circuit} />
  </div>;
}

function ProofResult({ result, request }: { result: ProveResponse; request: ProveRequest | undefined }) {
  const counterexample = result.counterexample;
  return <div className="lab-stack">
    {request && <p><code>{request.lhs} = {request.rhs}</code></p>}
    <p className={result.equivalent ? "lab-match" : "lab-mismatch"}>{result.equivalent ? "Kedua ekspresi ekuivalen." : "Kedua ekspresi tidak ekuivalen."}</p>
    {counterexample && <p>Contoh penyangkal {result.variables.map((variable, index) => variable + "=" + counterexample.inputs[index]).join(", ")}.
      Kiri {counterexample.lhs}, kanan {counterexample.rhs}.</p>}
    <DataTable caption="Perbandingan tabel kebenaran" columns={result.table.columns} rows={result.table.rows} />
    {result.dual && <Stats items={[
      { label: "Dual kiri", value: <code>{result.dual.lhs}</code> },
      { label: "Dual kanan", value: <code>{result.dual.rhs}</code> },
      { label: "Ekuivalensi dual", value: result.dual.equivalent ? "Ekuivalen" : "Berbeda" },
    ]} />}
    {result.algebraic_proof && <ProofSteps steps={result.algebraic_proof} />}
  </div>;
}

export function ExpressionWorkbench({ expressions, onChange }: {
  expressions: ProveRequest; onChange: (values: ProveRequest) => void;
}) {
  const { setLatest } = useInspector();
  const [lhsId, rhsId, hintId] = [useId(), useId(), useId()];
  const lhsInput = useRef<HTMLInputElement>(null);
  const rhsInput = useRef<HTMLInputElement>(null);
  const activeField = useRef<keyof ProveRequest>("lhs");
  const evaluate = useApiMutation((body: TruthTableRequest) => post<TruthTableResponse, TruthTableRequest>("/boolean/truth-table", body), {
    failure: "Tabel kebenaran gagal dihitung.", success: "Tabel kebenaran siap.",
    onSuccess: (result) => setLatest("boolean", result.inspector),
  });
  const prove = useApiMutation((body: ProveRequest) => post<ProveResponse, ProveRequest>("/boolean/prove", body), {
    failure: "Pembuktian gagal.", success: "Uji ekuivalensi selesai.",
    onSuccess: (result) => setLatest("boolean", result.inspector),
  });
  const evaluationError = evaluate.variables?.expression === expressions.lhs.trim() ? evaluate.error : null;
  const proofError = prove.variables?.lhs === expressions.lhs.trim() && prove.variables.rhs === expressions.rhs.trim() ? prove.error : null;
  const invalidLhs = parseError(evaluationError);
  const invalidPair = parseError(proofError);

  function insert(symbol: string) {
    const field = activeField.current;
    const input = field === "lhs" ? lhsInput.current : rhsInput.current;
    const value = expressions[field];
    const start = input?.selectionStart ?? value.length;
    const end = input?.selectionEnd ?? start;
    onChange({ ...expressions, [field]: value.slice(0, start) + symbol + value.slice(end) });
    requestAnimationFrame(() => { input?.focus(); input?.setSelectionRange(start + symbol.length, start + symbol.length); });
  }

  return <Panel title="Editor ekspresi" id="ekspresi">
    <div className="lab-actions" aria-label="Preset ekspresi">
      {presets.map(({ label, lhs, rhs }) => <Button key={label} size="sm" variant="outline" type="button"
        onClick={() => onChange({ lhs, rhs })}>{label}</Button>)}
    </div>
    <form className="lab-stack" onSubmit={(event) => {
      event.preventDefault();
      if (expressions.lhs.trim()) evaluate.run({ expression: expressions.lhs.trim() });
    }}>
      <div className="lab-fields">
        <div className="lab-field">
          <label htmlFor={lhsId}>Ekspresi kiri</label>
          <Input id={lhsId} value={expressions.lhs} ref={lhsInput} autoComplete="off" spellCheck={false}
            aria-describedby={hintId} aria-invalid={invalidLhs || invalidPair} onFocus={() => { activeField.current = "lhs"; }}
            onChange={(event) => onChange({ ...expressions, lhs: event.currentTarget.value })} />
        </div>
        <div className="lab-field">
          <label htmlFor={rhsId}>Ekspresi kanan</label>
          <Input id={rhsId} value={expressions.rhs} ref={rhsInput} autoComplete="off" spellCheck={false}
            aria-describedby={hintId} aria-invalid={invalidPair} onFocus={() => { activeField.current = "rhs"; }}
            onChange={(event) => onChange({ ...expressions, rhs: event.currentTarget.value })} />
        </div>
      </div>
      <p id={hintId} className="dim">Gunakan huruf tunggal, tanda kurung, perkalian berdampingan untuk AND, serta simbol berikut.</p>
      <div className="lab-actions">
        {[["'", "NOT"], ["+", "OR"], ["^", "XOR"]].map(([symbol, label]) =>
          <Button key={label} type="button" size="sm" variant="outline" aria-label={"Sisipkan " + label}
            onClick={() => { if (symbol) insert(symbol); }}>{symbol} {label}</Button>)}
      </div>
      <div className="lab-actions">
        <Button type="submit" disabled={!expressions.lhs.trim() || evaluate.isPending}>Hitung tabel kebenaran</Button>
        <Button type="button" variant="outline" disabled={!expressions.lhs.trim() || !expressions.rhs.trim() || prove.isPending}
          onClick={() => prove.run({ lhs: expressions.lhs.trim(), rhs: expressions.rhs.trim() })}>Uji ekuivalensi dan dualitas</Button>
      </div>
    </form>
    {(invalidLhs || invalidPair) && <p className="lab-inline-error" role="alert">
      Periksa operator, pasangan tanda kurung, dan batas enam variabel pada ekspresi.
    </p>}
    <RequestState pending={evaluate.isPending} error={evaluationError} empty="Hitung ekspresi kiri untuk melihat tabel dan rangkaian.">
      {evaluate.data && <TruthTable result={evaluate.data} />}
    </RequestState>
    {(prove.data || prove.isPending || proofError) && <RequestState pending={prove.isPending} error={proofError} empty={null}>
      {prove.data && <ProofResult result={prove.data} request={prove.variables} />}
    </RequestState>}
  </Panel>;
}

export function XorGateDemo() {
  const { setLatest } = useInspector();
  const gate = useApiMutation((request: Record<string, never>) => post<XorGateResponse, Record<string, never>>("/boolean/xor-gate", request), {
    failure: "Demo gerbang XOR gagal.", success: "Gerbang XOR terverifikasi.",
    onSuccess: (result) => setLatest("boolean", result.inspector),
  });
  return <Panel title="Demo gerbang XOR" id="gerbang">
    <div className="lab-actions"><Button variant="outline" type="button" disabled={gate.isPending}
      onClick={() => gate.run({})}>Tampilkan gerbang XOR</Button></div>
    <RequestState pending={gate.isPending} error={gate.error} empty="Tampilkan definisi, tabel dan rangkaian XOR dari backend.">
      {gate.data && <>
        <p><code>{gate.data.definition}</code></p>
        {gate.data.verified ? <p className="lab-match">Definisi terverifikasi.</p> : <Empty>Definisi belum terverifikasi.</Empty>}
        <DataTable columns={gate.data.table.columns} rows={gate.data.table.rows} caption="Tabel gerbang XOR" />
        <CircuitView circuit={gate.data.circuit} />
      </>}
    </RequestState>
  </Panel>;
}
