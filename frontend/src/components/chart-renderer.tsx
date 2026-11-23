import { Fragment, useId, type CSSProperties } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis } from "recharts";
import { Empty } from "@/components/workbench";
import { formatNumber } from "@/lib/workbench";
import type { ChartSeries, ChartSpec } from "@/types/api";

const colors = ["var(--cobalt)", "var(--foreground)", "var(--muted-foreground)"];
const colorsFor = (index: number) => colors[index % colors.length];
const tooltipStyle = { background: "var(--popover)", border: "1px solid var(--border)", color: "var(--foreground)" };
const axisStyle = { fill: "var(--muted-foreground)", fontSize: 11 };
const axisLabelStyle = { fill: "var(--foreground)", fontSize: 12 };

function Heatmap({ spec, titleId }: { spec: ChartSpec; titleId: string }) {
  const rows = spec.z ?? [];
  const count = Math.max(spec.x_labels?.length ?? 0, ...rows.map((row) => row.length));
  if (!rows.length || !count) return <Empty>Belum ada data grafik.</Empty>;

  const columns = Array.from({ length: count }, (_, i) => spec.x_labels?.[i] ?? String(i + 1));
  const max = rows.reduce((highest, row) => row.reduce((value, cell) => Math.max(value, Math.abs(cell)), highest), 0);
  const style = { "--matrix-columns": count } as CSSProperties;

  return <>
    {spec.x_label && <p className="mono dim lab-axis-name">{spec.x_label}</p>}
    <div className="lab-matrix-scroll" tabIndex={0} aria-label="Gulir matriks">
      <div className="lab-matrix" role="table" aria-labelledby={titleId} style={style}>
        <div role="row" className="lab-matrix-row">
          <span aria-hidden>{spec.y_label}</span>
          {columns.map((label, col) => <span key={col} role="columnheader">{label}</span>)}
        </div>
        {rows.map((row, index) => {
          const label = spec.y_labels?.[index] ?? String(index + 1);
          return <div role="row" className="lab-matrix-row" key={index}>
            <span role="rowheader">{label}</span>
            {columns.map((column, col) => {
              const value = row[col];
              const ratio = value === undefined || max === 0 ? 0 : Math.abs(value) / max;
              return <span key={col} role="cell" className="lab-matrix-cell" title={label + " / " + column}
                style={{ background: "color-mix(in srgb, var(--cobalt) " + (ratio * 100) + "%, var(--background))",
                  color: ratio >= 0.62 ? "var(--primary-foreground)" : undefined }}>{formatNumber(value)}</span>;
            })}
          </div>;
        })}
      </div>
    </div>
  </>;
}

function points(series: ChartSeries, indices?: (string | number)[]) {
  return series.y.map((y, index) => ({ x: series.x?.[index] ?? indices?.[index] ?? index + 1, y }));
}

export function ChartRenderer({ spec }: { spec: ChartSpec }) {
  const titleId = useId();
  const series = (spec.series ?? []).filter((item) => item.y.length);
  if (spec.kind === "heatmap") return <figure className="lab-chart">
    <figcaption id={titleId}>{spec.title}</figcaption><Heatmap spec={spec} titleId={titleId} />
  </figure>;
  if (!series.length) return <figure className="lab-chart">
    <figcaption id={titleId}>{spec.title}</figcaption><Empty>Belum ada data grafik.</Empty>
  </figure>;

  const values = series.map((item) => points(item, spec.x));
  const xValues = [...new Set(values.flatMap((rows) => rows.map((row) => row.x)))];
  const yValues = values.flatMap((rows) => rows.map((row) => row.y));
  const numericX = xValues.every((value) => typeof value === "number");
  const logX = numericX && Boolean(spec.log_x) && xValues.every((value) => Number(value) > 0);
  const logY = Boolean(spec.log_y) && yValues.every((value) => value > 0);
  const xLabel = spec.x_label ? { value: spec.x_label, position: "insideBottom" as const, offset: -4, style: axisLabelStyle } : undefined;
  const yLabel = spec.y_label ? { value: spec.y_label, angle: -90, position: "insideLeft" as const, style: axisLabelStyle } : undefined;
  const margin = { left: 8, right: 20, top: 12, bottom: spec.x_label ? 18 : 8 };
  const tick = (value: number | string) => typeof value === "number" ? formatNumber(value) : value;
  const xAxisType = spec.kind === "scatter" && numericX || spec.kind === "line" && numericX ? "number" : "category";

  const xAxis = <XAxis dataKey="x" type={xAxisType} tick={axisStyle} tickFormatter={tick} label={xLabel}
    scale={logX && xAxisType === "number" ? "log" : "auto"}
    domain={xAxisType === "number" ? ["dataMin", "dataMax"] : undefined} />;
  const yAxis = <YAxis dataKey={spec.kind === "scatter" ? "y" : undefined} type="number" tick={axisStyle}
    tickFormatter={tick} label={yLabel} scale={logY ? "log" : "auto"} domain={logY ? ["dataMin", "dataMax"] : undefined} />;
  const hover = <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "var(--foreground)" }} />;
  const legend = series.length > 1 ? <Legend verticalAlign="top" /> : null;

  let chart;
  if (spec.kind === "scatter") {
    chart = <ScatterChart margin={margin}>
      <CartesianGrid stroke="var(--border)" />{xAxis}{yAxis}{hover}{legend}
      {series.map((item, index) => <Scatter key={index} name={item.name} data={values[index]} fill={colorsFor(index)}
        isAnimationActive={false} />)}
    </ScatterChart>;
  } else {
    const joined = new Map(xValues.map((x) => [x, { x } as Record<string, number | string>]));
    values.forEach((rows, index) => rows.forEach(({ x, y }) => {
      const row = joined.get(x);
      if (row) row["y" + index] = y;
    }));
    const data = [...joined.values()];
    if (xAxisType === "number") data.sort((a, b) => Number(a.x) - Number(b.x));
    const Chart = spec.kind === "bar" ? BarChart : LineChart;
    chart = <Chart data={data} margin={margin}>
      <CartesianGrid stroke="var(--border)" vertical={false} />{xAxis}{yAxis}{hover}{legend}
      {series.map((item, index) => <Fragment key={index}>
        {spec.kind === "bar"
          ? <Bar name={item.name} dataKey={"y" + index} fill={colorsFor(index)} isAnimationActive={false} />
          : <Line name={item.name} dataKey={"y" + index} stroke={colorsFor(index)} strokeWidth={2}
            dot={item.y.length <= 24} strokeDasharray={index > 2 ? "5 3" : undefined} isAnimationActive={false} />}
      </Fragment>)}
    </Chart>;
  }

  return <figure className="lab-chart">
    <figcaption id={titleId}>{spec.title}</figcaption>
    <div className="lab-chart-plot" role="group" aria-labelledby={titleId}>
      <ResponsiveContainer width="100%" height={248} minWidth={0}>{chart}</ResponsiveContainer>
    </div>
  </figure>;
}
