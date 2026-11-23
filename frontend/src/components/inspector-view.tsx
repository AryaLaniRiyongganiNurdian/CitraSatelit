import { useId, useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";
import { ChartRenderer } from "@/components/chart-renderer";
import { DataTable, Empty } from "@/components/workbench";
import type { Inspector } from "@/types/api";
import "./inspector.css";

function Formula({ latex, label }: { latex: string; label: string }) {
  const html = useMemo(() => katex.renderToString(latex, {
    displayMode: true, throwOnError: false, trust: false,
  }), [latex]);
  return <figure className="inspector-formula">
    <figcaption className="mono dim">{label}</figcaption>
    <div dangerouslySetInnerHTML={{ __html: html }} />
  </figure>;
}

export function InspectorView({ inspector }: { inspector: Inspector }) {
  const headingId = useId();
  return <div className="inspector-view" aria-labelledby={headingId}>
    <h3 id={headingId}>{inspector.title}</h3>
    {inspector.steps.length === 0 && <Empty>Payload ini belum memiliki langkah perhitungan.</Empty>}
    {inspector.steps.map((step, index) => {
      const values = Object.entries(step.values);
      return <details className="inspector-step" key={step.id} open={index === 0}>
        <summary><span>{step.title}</span><code>{step.id}</code></summary>
        <div className="inspector-step-body">
          {step.explanation && <p>{step.explanation}</p>}
          {step.latex_template && <Formula latex={step.latex_template} label="Rumus" />}
          {step.latex_substituted && <Formula latex={step.latex_substituted} label="Substitusi nilai" />}
          {values.length > 0 && <DataTable caption="Nilai langkah" columns={["Besaran", "Nilai"]} rows={values} />}
          {step.table && <DataTable columns={step.table.columns} rows={step.table.rows} caption={step.table.caption} />}
          {step.chart && <ChartRenderer spec={step.chart} />}
        </div>
      </details>;
    })}
  </div>;
}
