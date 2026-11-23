import { useId } from "react";
import { Empty } from "@/components/workbench";
import type { Circuit, CircuitNode } from "@/types/api";
import "./circuit.css";

function layout(circuit: Circuit) {
  const byId = new Map(circuit.nodes.map((node) => [node.id, node]));
  const incoming = new Map<string, string[]>();
  const outgoing = new Map<string, string[]>();
  for (const { from, to } of circuit.edges) {
    if (!byId.has(from) || !byId.has(to)) continue;
    incoming.set(to, [...(incoming.get(to) ?? []), from]);
    outgoing.set(from, [...(outgoing.get(from) ?? []), to]);
  }
  const waiting = new Map(circuit.nodes.map((node) => [node.id, incoming.get(node.id)?.length ?? 0]));
  const ready = circuit.nodes.filter((node) => waiting.get(node.id) === 0).map((node) => node.id);
  const depths = new Map<string, number>();
  for (let index = 0; index < ready.length; index += 1) {
    const id = ready[index]!;
    const parents = incoming.get(id) ?? [];
    depths.set(id, parents.length ? Math.max(...parents.map((parent) => depths.get(parent) ?? 0)) + 1 : 0);
    for (const child of outgoing.get(id) ?? []) {
      const remaining = (waiting.get(child) ?? 0) - 1;
      waiting.set(child, remaining);
      if (remaining === 0) ready.push(child);
    }
  }
  if (ready.length !== circuit.nodes.length) return null;

  const layers = new Map<number, CircuitNode[]>();
  for (const node of circuit.nodes) {
    const depth = depths.get(node.id) ?? 0;
    layers.set(depth, [...(layers.get(depth) ?? []), node]);
  }
  const height = Math.max(116, ...Array.from(layers.values(), (layer) => layer.length * 68 + 30));
  const width = Math.max(220, layers.size * 142 + 38);
  const points = new Map<string, { x: number; y: number }>();
  for (const [depth, nodes] of layers) {
    nodes.forEach((node, index) => points.set(node.id, {
      x: 48 + depth * 142, y: height / 2 + (index - (nodes.length - 1) / 2) * 68,
    }));
  }
  return { points, width, height, incoming };
}

function Gate({ node }: { node: CircuitNode }) {
  if (node.type === "input") return <>
    <rect x={-27} y={-17} width={54} height={34} />
    <text y={4}>{node.label}</text>
  </>;
  return <>
    {node.type === "not" ? <>
      <path d="M-25 -17v34L18 0Z" /><circle cx={22} cy={0} r={4} />
    </> : node.type === "and"
      ? <path d="M-25 -18H2a18 18 0 1 1 0 36h-27Z" />
      : <>
        <path d="M-25 -18Q10 -21 26 0Q10 21 -25 18Q-11 0 -25 -18Z" />
        {node.type === "xor" && <path d="M-31 -18Q-17 0 -31 18" fill="none" />}
      </>}
    <text y={33}>{node.label}</text>
  </>;
}

export function CircuitView({ circuit }: { circuit: Circuit }) {
  const titleId = useId();
  const diagram = layout(circuit);
  if (!diagram || !circuit.nodes.length) return <Empty>Rangkaian belum dapat ditampilkan.</Empty>;
  const { points, width, height, incoming } = diagram;
  const output = points.get(circuit.output_id);
  if (!output) return <Empty>Keluaran rangkaian belum tersedia.</Empty>;
  const edgeCounts = new Map<string, number>();
  return <div className="circuit-scroll" tabIndex={0} aria-label="Gulir diagram rangkaian">
    <svg role="img" aria-labelledby={titleId} className="circuit-svg" width={width} height={height} viewBox={"0 0 " + width + " " + height}>
      <title id={titleId}>Rangkaian logika</title>
      {circuit.edges.map((edge, index) => {
        const from = points.get(edge.from);
        const to = points.get(edge.to);
        if (!from || !to) return null;
        const port = edgeCounts.get(edge.to) ?? 0;
        edgeCounts.set(edge.to, port + 1);
        const inputs = incoming.get(edge.to)?.length ?? 1;
        const y = to.y + 14 * ((port + 0.5) / inputs - 0.5);
        const middle = (from.x + to.x) / 2;
        return <path className="circuit-wire" key={index}
          d={"M" + (from.x + 27) + " " + from.y + "H" + middle + "V" + y + "H" + (to.x - 25)} />;
      })}
      {circuit.nodes.map((node) => {
        const point = points.get(node.id);
        return point && <g key={node.id} className="circuit-gate" transform={"translate(" + point.x + " " + point.y + ")"}>
          <Gate node={node} />
        </g>;
      })}
      <path className="circuit-wire" d={"M" + (output.x + 27) + " " + output.y + "h35"} />
      <circle className="circuit-output" cx={output.x + 62} cy={output.y} r={3} />
      <text className="circuit-output-label" x={output.x + 68} y={output.y + 4}>Q</text>
    </svg>
  </div>;
}
