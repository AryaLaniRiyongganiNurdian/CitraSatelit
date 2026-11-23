import { useState, type CSSProperties } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Choice, DataTable, Empty, Loading, Panel } from "@/components/workbench";
import { post } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import { useInspectorResult } from "@/lib/workbench";
import type { KMapGroup, KMapRequest, KMapResponse } from "@/types/api";

function spans(indices: number[]) {
  const partitions: { start: number; size: number }[] = [];
  for (const index of [...new Set(indices)].sort((a, b) => a - b)) {
    const last = partitions.at(-1);
    if (last && index === last.start + last.size) last.size += 1;
    else partitions.push({ start: index, size: 1 });
  }
  return partitions;
}

export function groupRegions(cells: [number, number][]) {
  const rows = spans(cells.map(([row]) => row));
  const columns = spans(cells.map(([, column]) => column));
  return rows.flatMap((row) => columns.map((column) => ({
    row: row.start, column: column.start, height: row.size, width: column.size,
  })));
}

export function KMapView({ layout, minterms, groups, onToggle }: {
  layout: KMapResponse; minterms: number[]; groups: KMapGroup[]; onToggle: (minterm: number) => void;
}) {
  const style = { "--kmap-columns": layout.col_labels.length } as CSSProperties;
  return <>
    <div className="kmap-scroll">
      <div className="kmap-grid" role="group" aria-label="Peta Karnaugh dalam urutan Gray" style={style}>
        <div className="kmap-label kmap-axis" style={{ gridRow: 1, gridColumn: 1 }}>
          {layout.row_vars.join("")} / {layout.col_vars.join("")}
        </div>
        {layout.col_labels.map((label, column) =>
          <span key={column} className="kmap-label" style={{ gridRow: 1, gridColumn: column + 2 }}>{label}</span>)}
        {layout.row_labels.map((label, row) =>
          <span key={row} className="kmap-label" style={{ gridRow: row + 2, gridColumn: 1 }}>{label}</span>)}
        {layout.cell_minterm.flatMap((row, rowIndex) => row.map((minterm, column) => {
          const active = minterms.includes(minterm);
          return <button key={minterm} type="button" className="kmap-cell" style={{ gridRow: rowIndex + 2, gridColumn: column + 2 }}
            aria-label={"Minterm " + minterm} aria-pressed={active} onClick={() => onToggle(minterm)}>
            <span>m{minterm}</span><strong>{active ? 1 : 0}</strong>
          </button>;
        }))}
        {groups.flatMap((group, groupIndex) => groupRegions(group.cells_rc).map((region) =>
          <span key={groupIndex + "/" + region.row + "/" + region.column} aria-hidden="true" className="kmap-outline"
            data-tone={groupIndex % 6} data-wrap={group.wraps} style={{
              gridRow: (region.row + 2) + " / span " + region.height,
              gridColumn: (region.column + 2) + " / span " + region.width,
              margin: 3 + (groupIndex % 3) * 3,
            }} />,
        ))}
      </div>
    </div>
    {groups.length > 0 && <ul className="kmap-legend" aria-label="Grup terpilih">
      {groups.map((group, index) => <li key={group.term + ":" + index} data-tone={index % 6}>
        <code>{group.term}</code>
        <span>{group.cells.map((cell) => "m" + cell).join(", ")}{group.wraps ? " · Lipatan tepi" : ""}</span>
      </li>)}
    </ul>}
  </>;
}

export function KMapWorkbench() {
  const [variables, setVariables] = useState<KMapRequest["variables"]>(3);
  const [minterms, setMinterms] = useState<number[]>([]);
  const [edited, setEdited] = useState(false);
  const request: KMapRequest = { variables, minterms };
  const query = useQuery({
    queryKey: ["boolean", "kmap", request], placeholderData: keepPreviousData,
    queryFn: ({ signal }) => post<KMapResponse, KMapRequest>("/boolean/kmap", request, signal),
  });
  useQueryError("boolean-kmap", "Peta Karnaugh gagal dihitung.", query.error);
  const result = !query.isPlaceholderData ? query.data : undefined;
  useInspectorResult("boolean", edited ? result?.inspector : undefined, query.dataUpdatedAt);
  const layout = query.data?.variables.length === variables ? query.data : undefined;

  function configure(nextCount: KMapRequest["variables"], terms: number[]) {
    setEdited(true);
    setVariables(nextCount);
    setMinterms(terms);
  }

  return <Panel id="kmap" title="Peta Karnaugh">
    <Choice<KMapRequest["variables"]> label="Jumlah variabel" value={variables} options={[
      { value: 2, label: "2 variabel" }, { value: 3, label: "3 variabel" }, { value: 4, label: "4 variabel" },
    ]} onChange={(count) => configure(count, [])} />
    <div className="lab-actions">
      <Button type="button" size="sm" variant="outline" onClick={() => configure(3, [3, 5, 6, 7])}>Preset mayoritas</Button>
      <Button type="button" size="sm" variant="outline" onClick={() => configure(4, [0, 2, 8, 10])}>Preset lipatan tepi</Button>
      <Button type="button" size="sm" variant="ghost" onClick={() => configure(variables, [])}>Kosongkan minterm</Button>
    </div>
    <p className="dim">Klik sel untuk beralih antara 0 dan 1. Peta dihitung ulang dari minterm yang dipilih.</p>
    {layout && <KMapView layout={layout} minterms={minterms} groups={result?.selected ?? []} onToggle={(minterm) => {
      setEdited(true);
      setMinterms((current) => current.includes(minterm)
        ? current.filter((item) => item !== minterm) : [...current, minterm].sort((a, b) => a - b));
    }} />}
    {query.isFetching && <Loading label="Menghitung peta Karnaugh" />}
    {query.error && <div className="lab-actions">
      <Empty>{query.error.message}</Empty>
      <Button size="sm" type="button" variant="outline" onClick={() => { void query.refetch(); }}>Coba lagi</Button>
    </div>}
    {result && <div className="lab-stack">
      <div className="kmap-sop"><span className="mono dim">SOP minimal</span><output>{result.simplified}</output></div>
      {result.prime_implicants.length > 0 && <details>
        <summary>Lihat semua implikan prima ({result.prime_implicants.length})</summary>
        <DataTable columns={["Suku", "Minterm", "Lipatan tepi"]} rows={result.prime_implicants.map((group) => [
          group.term, group.cells.join(", "), group.wraps,
        ])} />
      </details>}
    </div>}
  </Panel>;
}
