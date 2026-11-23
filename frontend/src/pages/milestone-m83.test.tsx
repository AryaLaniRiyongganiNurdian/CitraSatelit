import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CircuitView } from "@/components/circuit-view";
import { InspectorDrawer } from "@/components/inspector-drawer";
import { InspectorView } from "@/components/inspector-view";
import { AppProviders, useInspector } from "@/contexts";
import { KMapWorkbench, groupRegions } from "@/pages/boolean/kmap";
import { ExperimentRenderer } from "@/pages/experiments";
import type { Circuit, ExperimentResult, Inspector, KMapResponse } from "@/types/api";

const inspector: Inspector = {
  title: "Bukti dari kueri",
  steps: [
    { id: "rumus", title: "Rumus", explanation: "Gunakan nilai aktual.", latex_template: String.raw`x^2`,
      latex_substituted: String.raw`2^2=4`, values: { hasil: 4 }, table: { columns: ["Bin"], rows: [[7]] }, chart: null },
    { id: "hasil", title: "Hasil", explanation: "Pangkat telah dihitung.", latex_template: null,
      latex_substituted: null, values: {}, table: null, chart: null },
  ],
};

afterEach(() => vi.unstubAllGlobals());

describe("Lab, Percobaan, dan Inspektor M8.3", () => {
  it("merender formula KaTeX, substitusi, nilai, tabel, dan ID langkah", () => {
    const { container } = render(<InspectorView inspector={inspector} />);
    const details = container.querySelectorAll("details");
    expect(details[0]).toHaveAttribute("open");
    expect(details[1]).not.toHaveAttribute("open");
    expect(container.querySelectorAll(".katex-display")).toHaveLength(2);
    expect(screen.getByText("rumus")).toBeVisible();
    expect(screen.getByText("Gunakan nilai aktual.")).toBeVisible();
    expect(within(screen.getByRole("table", { name: "Nilai langkah" })).getByText("4")).toBeVisible();
    expect(screen.getByRole("cell", { name: "7" })).toBeVisible();
  });

  it("membuka drawer dari konteks sambil tetap berada di rute workbench", async () => {
    function Probe() {
      const { setLatest } = useInspector();
      const location = useLocation();
      return <><span>{location.pathname}</span>
        <button type="button" onClick={() => setLatest("boolean", inspector)}>Simpan bukti</button>
        <InspectorDrawer source="boolean" />
      </>;
    }
    render(<AppProviders><MemoryRouter initialEntries={["/boolean"]}><Probe /></MemoryRouter></AppProviders>);
    fireEvent.click(screen.getByRole("button", { name: "Simpan bukti" }));
    fireEvent.click(screen.getByRole("button", { name: "Buka Math Inspector" }));
    const drawer = await screen.findByRole("dialog", { name: "Inspektor Matematika" });
    expect(await within(drawer).findByText("Bukti dari kueri")).toBeVisible();
    expect(within(drawer).getByRole("link", { name: "Buka halaman penuh" })).toHaveAttribute("href", "/inspector?source=boolean");
    expect(screen.getByText("/boolean")).toBeInTheDocument();
  });

  it("memisah satu implicant yang melipat kedua tepi menjadi empat wilayah", () => {
    expect(groupRegions([[0, 0], [0, 3], [3, 0], [3, 3]])).toEqual([
      { row: 0, column: 0, height: 1, width: 1 }, { row: 0, column: 3, height: 1, width: 1 },
      { row: 3, column: 0, height: 1, width: 1 }, { row: 3, column: 3, height: 1, width: 1 },
    ]);
  });

  it("mengirim minterm yang diklik dan menampilkan SOP dari backend", async () => {
    const request = vi.fn<typeof fetch>(async (_, init) => {
      const term = typeof init?.body === "string" && init.body.includes('"minterms":[1]');
      return Response.json({
        variables: ["a", "b", "c"], row_vars: ["a"], col_vars: ["b", "c"],
        row_labels: ["0", "1"], col_labels: ["00", "01", "11", "10"],
        grid: [[0, term ? 1 : 0, 0, 0], [0, 0, 0, 0]], cell_minterm: [[0, 1, 3, 2], [4, 5, 7, 6]],
        prime_implicants: [], selected: [], simplified: term ? "a'b'c" : "0", inspector,
      } satisfies KMapResponse);
    });
    vi.stubGlobal("fetch", request);
    render(<AppProviders><KMapWorkbench /></AppProviders>);
    fireEvent.click(await screen.findByRole("button", { name: "Minterm 1" }));
    expect(await screen.findByText("a'b'c")).toBeVisible();
    expect(screen.getByRole("button", { name: "Minterm 1" })).toHaveAttribute("aria-pressed", "true");
    expect(request.mock.calls.at(-1)?.[0]).toBe("/api/boolean/kmap");
  });

  it("merender rangkaian DAG meski gerbang datang sebelum node input", () => {
    const circuit = {
      nodes: [{ id: "y", label: "XOR", type: "xor" }, { id: "a", label: "a", type: "input" }, { id: "b", label: "b", type: "input" }],
      edges: [{ from: "a", to: "y" }, { from: "b", to: "y" }], output_id: "y",
    } satisfies Circuit;
    const { container } = render(<CircuitView circuit={circuit} />);
    expect(screen.getByRole("img", { name: "Rangkaian logika" })).toBeVisible();
    expect(container.querySelectorAll(".circuit-wire")).toHaveLength(3);
    expect(screen.getByText("XOR")).toBeInTheDocument();
  });

  it("merender hasil percobaan generik dari tabel, grafik, dan Markdown", () => {
    const result = {
      id: "C2", title: "Uji metode", description: "Perbandingan metode.", generated_at: "2026-11-23T06:00:00Z",
      runtime_s: 1.25, params: { k: 5 }, dataset: { n_images: 30, n_queries: 10, note: "Data uji" },
      tables: [{ caption: "Hasil tabel", columns: ["Metode"], rows: [["RGB"]] }],
      charts: [{ kind: "heatmap", title: "Confusion", x_labels: ["Hutan"], y_labels: ["Hutan"], z: [[8]] }],
      findings: ["RGB unggul pada sampel ini."], analysis_md: "## Ringkasan\n\n**Akurasi naik.**",
    } satisfies ExperimentResult;
    render(<ExperimentRenderer result={result} />);
    expect(screen.getByRole("table", { name: "Hasil tabel" })).toBeVisible();
    expect(screen.getByRole("table", { name: "Confusion" })).toBeVisible();
    expect(screen.getByText("RGB unggul pada sampel ini.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Ringkasan" })).toBeVisible();
    expect(screen.getByText("Akurasi naik.").tagName).toBe("STRONG");
  });
});
