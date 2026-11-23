import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChartRenderer } from "@/components/chart-renderer";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, Empty, Panel, RequestState, Stats, Workbench } from "@/components/workbench";
import { get } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import { formatNumber } from "@/lib/workbench";
import type { ExperimentId, ExperimentResult, ExperimentSummary } from "@/types/api";
import "./experiments.css";

function inlineMarkdown(line: string) {
  return line.split(/(\x60[^\x60]+\x60|\*\*[^*]+\*\*|\*[^*]+\*)/g).map((piece, index) => {
    if (piece.startsWith("`") && piece.endsWith("`")) return <code key={index}>{piece.slice(1, -1)}</code>;
    if (piece.startsWith("**") && piece.endsWith("**")) return <strong key={index}>{piece.slice(2, -2)}</strong>;
    if (piece.startsWith("*") && piece.endsWith("*") && piece.length > 2) return <em key={index}>{piece.slice(1, -1)}</em>;
    return piece;
  });
}

function Analysis({ markdown }: { markdown: string }) {
  const sections = markdown.trim().split(/\r?\n(?:[ \t]*\r?\n)+/);
  const bullet = /^[-+*]\s+/;
  const numbered = /^\d+[.)]\s+/;
  if (!markdown.trim()) return <Empty>Analisis tertulis belum tersedia.</Empty>;
  return <div className="experiment-analysis">
    {sections.map((section, index) => {
      const lines = section.split(/\r?\n/);
      if (lines.every((line) => bullet.test(line))) return <ul key={index}>
        {lines.map((line, item) => <li key={item}>{inlineMarkdown(line.replace(bullet, ""))}</li>)}
      </ul>;
      if (lines.every((line) => numbered.test(line))) return <ol key={index} start={parseInt(lines[0] ?? "1", 10)}>
        {lines.map((line, item) => <li key={item}>{inlineMarkdown(line.replace(numbered, ""))}</li>)}
      </ol>;
      const heading = lines[0]?.match(/^#{1,6}\s+(.+)$/)?.[1];
      return heading ? <div key={index}>
        <h3>{inlineMarkdown(heading)}</h3>
        {lines.length > 1 && <p>{inlineMarkdown(lines.slice(1).join("\n"))}</p>}
      </div> : <p key={index}>{inlineMarkdown(lines.join("\n"))}</p>;
    })}
  </div>;
}

export function ExperimentRenderer({ result }: { result: ExperimentResult }) {
  const date = new Date(result.generated_at);
  const formattedDate = Number.isNaN(date.getTime()) ? result.generated_at :
    new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(date);
  return <div className="lab-stack">
    <Panel title={result.title}>
      <p>{result.description}</p>
      <Stats items={[
        { label: "Citra", value: formatNumber(result.dataset.n_images) },
        { label: "Kueri", value: formatNumber(result.dataset.n_queries) },
        { label: "Waktu hitung", value: formatNumber(result.runtime_s) + " detik" },
        { label: "Dibuat", value: <time dateTime={result.generated_at}>{formattedDate}</time> },
      ]} />
      {result.dataset.note && <p className="dim">{result.dataset.note}</p>}
      {Object.keys(result.params).length > 0 && <details className="experiment-params">
        <summary>Parameter percobaan</summary><pre>{JSON.stringify(result.params, null, 2)}</pre>
      </details>}
    </Panel>
    {result.findings.length > 0 && <Panel title="Temuan">
      <ul className="experiment-findings">{result.findings.map((finding, index) => <li key={index}>{finding}</li>)}</ul>
    </Panel>}
    {result.tables.length > 0 && <Panel title="Tabel pengukuran">
      {result.tables.map((table, index) => <DataTable key={index} columns={table.columns} rows={table.rows}
        caption={table.caption} />)}
    </Panel>}
    {result.charts.length > 0 && <Panel title="Grafik pengukuran">
      <div className="experiment-charts">
        {result.charts.map((chart, index) => <ChartRenderer key={index} spec={chart} />)}
      </div>
    </Panel>}
    <Panel title="Analisis"><Analysis markdown={result.analysis_md} /></Panel>
  </div>;
}

function ExperimentDetail({ summary }: { summary: ExperimentSummary }) {
  const detail = useQuery({
    queryKey: ["experiment", summary.id],
    enabled: summary.has_results,
    queryFn: ({ signal }) => get<ExperimentResult>("/experiments/" + summary.id, undefined, signal),
  });
  useQueryError("experiment-" + summary.id, "Hasil percobaan gagal dimuat.", detail.error);
  if (!summary.has_results) return <Panel title={summary.title}>
    <p>{summary.description}</p><Empty>Hasil percobaan ini belum dihitung.</Empty>
  </Panel>;
  return <RequestState pending={detail.isPending} error={detail.error} empty="Hasil percobaan belum tersedia."
    loading={"Memuat percobaan " + summary.id}>
    {detail.data && <ExperimentRenderer result={detail.data} />}
  </RequestState>;
}

export function ExperimentsPage() {
  const [choice, setChoice] = useState<ExperimentId>();
  const summaries = useQuery({
    queryKey: ["experiments"], queryFn: ({ signal }) => get<ExperimentSummary[]>("/experiments", undefined, signal),
  });
  useQueryError("experiments", "Daftar percobaan gagal dimuat.", summaries.error);
  const items = summaries.data ?? [];
  const active = items.find((item) => item.id === choice) ?? items.find((item) => item.has_results) ?? items[0];
  return <Workbench title="Percobaan" description="Bandingkan hasil pengukuran CBIR, galat bit-flip, kerahasiaan share, dan kompleksitas pencarian.">
    <RequestState pending={summaries.isPending} error={summaries.error} empty="Belum ada percobaan yang terdaftar."
      loading="Memuat daftar percobaan">
      {active && <Tabs value={active.id} onValueChange={(id) => {
        const item = items.find((option) => option.id === id);
        if (item) setChoice(item.id);
      }}>
        <TabsList aria-label="Daftar percobaan" variant="line">
          {items.map((item) => <TabsTrigger key={item.id} value={item.id} title={item.title}>{item.id}</TabsTrigger>)}
        </TabsList>
        <TabsContent value={active.id} key={active.id}><ExperimentDetail summary={active} /></TabsContent>
      </Tabs>}
    </RequestState>
  </Workbench>;
}
