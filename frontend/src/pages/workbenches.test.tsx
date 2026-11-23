import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChartRenderer } from "@/components/chart-renderer";
import { ImagePicker } from "@/components/image-picker";
import { AppProviders } from "@/contexts";
import { useDebouncedApiQuery } from "@/lib/workbench";
import { SharingPage } from "@/pages/sharing";
import { ReconMetricsView } from "@/pages/sharing/reconstruction";
import type { ImageMeta, ReconMetrics, SplitResponse } from "@/types/api";

const source = {
  id: "Forest_3", cls: "Forest", split: "test", width: 2, height: 2, bands: 13,
  has_rgb: true, has_ms: true, in_gallery: true, is_upload: false, thumb_url: "/api/images/Forest_3/thumb",
} satisfies ImageMeta;
const image = { data_uri: "data:image/png;base64,AA==", width: 2, height: 2, kind: "gray", note: null };
const metrics = { identical: true, mse: 0, psnr_db: null, psnr_is_infinite: true, pixels_different: 0, max_abs_diff: 0 } satisfies ReconMetrics;
const split = {
  session_id: "expired", n: 3, band_mode: "gray", shape: [2, 2], dtype: "uint8", bits: 8, seed: 42,
  original_preview: image, reconstruction: metrics, inspector: { title: "Pembagian XOR", steps: [] },
  shares: [0, 1, 2].map((index) => ({
    index, preview: image, histogram: [2, 2], entropy_bits: 7.5,
    chi2: { stat: 4, df: 255, p_value: 0.5, uniform_at_alpha_0_05: true },
    download_urls: { png: "/share.png", npy: "/share.npy" },
  })),
} satisfies SplitResponse;

function renderLab(children: ReactNode) {
  return render(<AppProviders><MemoryRouter>{children}</MemoryRouter></AppProviders>);
}

function mockApi() {
  let splits = 0;
  const mock = vi.fn<typeof fetch>(async (input) => {
    const url = String(input).split("?")[0];
    if (url === "/api/images") return Response.json({ total: 1, items: [source] });
    if (url === "/api/images/upload") return Response.json({ ...source, id: "up_demo", is_upload: true });
    if (url === "/api/meta") return Response.json({ classes: ["Forest"], class_labels_id: { Forest: "Hutan" }, band_names: [], limits: { max_shares: 8 } });
    if (url === "/api/sharing/split") return Response.json({ ...split, session_id: splits++ === 0 ? "expired" : "restored" });
    if (url === "/api/sharing/reconstruct") {
      if (splits === 1) return Response.json({ error: { code: "SESSION_NOT_FOUND", message: "Sesi kedaluwarsa." } }, { status: 404 });
      return Response.json({ preview: image, metrics, is_complete: true, used_indices: [0, 1, 2], n_total: 3, entropy_bits: 1, inspector: split.inspector });
    }
    throw new Error("Endpoint tak terduga " + url);
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", class TestResizeObserver implements ResizeObserver {
    constructor(private readonly callback: ResizeObserverCallback) {}
    observe(target: Element) {
      const size = { inlineSize: 600, blockSize: 248 };
      this.callback([{
        target, contentRect: new DOMRect(0, 0, 600, 248), borderBoxSize: [size],
        contentBoxSize: [size], devicePixelContentBoxSize: [size],
      }], this);
    }
    unobserve() {}
    disconnect() {}
  });
});

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("Workbench M8.2", () => {
  it("menolak citra melebihi batas lokal dan mengirim TIFF yang valid", async () => {
    const api = mockApi();
    renderLab(<ImagePicker value={null} onSelect={() => undefined} />);
    const upload = screen.getByLabelText("Unggah citra");
    fireEvent.change(upload, { target: { files: [new File([new Uint8Array(2 * 1024 ** 2 + 1)], "besar.PNG")] } });
    expect(await screen.findByText(/Maksimum 2 MB/)).toBeVisible();
    expect(api.mock.calls.some(([url]) => url === "/api/images/upload")).toBe(false);
    fireEvent.change(upload, { target: { files: [new File([new Uint8Array(5 * 1024 ** 2 + 1)], "besar.tiff")] } });
    expect(await screen.findByText(/Maksimum 5 MB/)).toBeVisible();
    const allowed = new File([new Uint8Array(5 * 1024 ** 2)], "sampel.TIF");
    fireEvent.change(upload, { target: { files: [allowed] } });
    expect(await screen.findByText("Citra berhasil diunggah.")).toBeVisible();
    const call = api.mock.calls.find(([url]) => url === "/api/images/upload");
    expect(call?.[1]?.body).toBeInstanceOf(FormData);
    expect((call?.[1]?.body as FormData).get("file")).toEqual(allowed);
  });

  it("menampilkan PSNR tak hingga dan mempertahankan nilai nol", () => {
    render(<ReconMetricsView metrics={metrics} />);
    expect(screen.getByText("tak hingga")).toBeVisible();
    expect(screen.getByText("Identik")).toBeVisible();
    expect(screen.getAllByText("0")).toHaveLength(3);
  });

  it("membuat ulang sesi kedaluwarsa memakai parameter pembagian terakhir", async () => {
    const api = mockApi();
    renderLab(<SharingPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Forest_3/ }));
    fireEvent.click(screen.getByRole("button", { name: "Bagi citra" }));
    await screen.findByRole("slider", { name: "Peluang fokus" });
    fireEvent.click(await screen.findByRole("button", { name: "Rekonstruksi dari pilihan" }));
    expect(await screen.findByText("Sesi kedaluwarsa.")).toBeVisible();
    fireEvent.click(await screen.findByRole("button", { name: "Buat ulang sesi" }));
    await screen.findByRole("button", { name: "Rekonstruksi dari pilihan" });
    const bodies = api.mock.calls.filter(([url]) => url === "/api/sharing/split").map(([, request]) => request?.body);
    expect(bodies).toHaveLength(2);
    expect(bodies[0]).toBe(bodies[1]);
  });

  it("merender label sumbu dan semua angka heatmap 10×10, termasuk nol", () => {
    const labels = Array.from({ length: 10 }, (_, index) => "Kelas " + (index + 1));
    render(<ChartRenderer spec={{
      kind: "heatmap", title: "Matriks kebingungan", x_labels: labels, y_labels: labels,
      z: labels.map((_, row) => labels.map((__, col) => row === col ? 45 : 0)),
    }} />);
    const table = screen.getByRole("table", { name: "Matriks kebingungan" });
    expect(within(table).getAllByRole("columnheader")).toHaveLength(10);
    expect(within(table).getAllByRole("rowheader")).toHaveLength(10);
    expect(within(table).getAllByRole("cell")).toHaveLength(100);
    expect(within(table).getAllByText("0")).toHaveLength(90);
  });

  it.each(["bar", "line", "scatter"] as const)("merender judul dan status kosong grafik %s", (kind) => {
    render(<ChartRenderer spec={{ kind, title: "Uji grafik", x: [], series: [] }} />);
    expect(screen.getByText("Uji grafik")).toBeVisible();
    expect(screen.getByText("Belum ada data grafik.")).toBeVisible();
  });

  it.each([
    ["bar", ".recharts-bar-rectangle"], ["line", ".recharts-line-curve"], ["scatter", ".recharts-scatter-symbol"],
  ] as const)("merender seri data pada grafik %s", async (kind, selector) => {
    const chart = render(<ChartRenderer spec={{
      kind, title: "Data grafik", x: [1, 2, 3], series: [{ name: "Sampel", y: [2, 4, 5] }],
    }} />);
    expect(await screen.findByRole("group", { name: "Data grafik" })).toBeVisible();
    expect(chart.container.querySelector(selector)).toBeInTheDocument();
  });

  it("menunda permintaan 400 ms dan langsung membatalkan sinyal lama", async () => {
    vi.useFakeTimers();
    const signals: AbortSignal[] = [];
    function Probe() {
      const [value, setValue] = useState(1);
      useDebouncedApiQuery(["probe", value], true, (signal) => {
        signals.push(signal);
        return new Promise<never>(() => undefined);
      });
      return <button onClick={() => setValue(2)}>Ubah</button>;
    }
    renderLab(<Probe />);
    await act(() => vi.advanceTimersByTimeAsync(399));
    expect(signals).toHaveLength(0);
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(signals).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Ubah" }));
    expect(signals[0]?.aborted).toBe(true);
    await act(() => vi.advanceTimersByTimeAsync(400));
    expect(signals).toHaveLength(2);
  });
});
