import { render, screen, within, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./app";
import { AppProviders } from "./contexts";
import type { ExperimentResult, ExperimentSummary, ImageMeta, KMapResponse } from "./types/api";

vi.mock("@/components/magicui/number-ticker", () => ({ NumberTicker: () => null }));

const summary = [{ id: "C2", title: "Metode", description: "Uji", generated_at: null, has_results: true }] satisfies ExperimentSummary[];
const river = {
  id: "River_12", cls: "River", split: "test", width: 64, height: 64, bands: 3,
  has_rgb: true, has_ms: true, in_gallery: true, is_upload: false, thumb_url: "/api/images/River_12/thumb",
} satisfies ImageMeta;
const meta = { dataset: { n_total: 27000 }, classes: ["Forest", "River"], class_labels_id: { River: "Sungai" } };
const experiment = {
  id: "C2", title: "Metode", description: "Uji", generated_at: "2026-11-23T00:00:00Z",
  runtime_s: 1, params: {}, dataset: { n_images: 27000, n_queries: 500, note: "" },
  tables: [{ columns: ["Metode", "P@5", "Akurasi"], rows: [["rgb euclid", 0.72, 0.76], ["rgb chi2", 0.7432, 0.796]] }],
  charts: [], findings: [], analysis_md: "",
} satisfies ExperimentResult;
const kmap = {
  variables: ["a", "b", "c"], row_vars: ["a"], col_vars: ["b", "c"], row_labels: ["0", "1"], col_labels: ["00", "01", "11", "10"],
  grid: [[0, 0, 0, 0], [0, 0, 0, 0]], cell_minterm: [[0, 1, 3, 2], [4, 5, 7, 6]], prime_implicants: [],
  selected: [], simplified: "0", inspector: { title: "Peta Karnaugh", steps: [] },
} satisfies KMapResponse;

function app(path = "/") {
  return render(<AppProviders><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></AppProviders>);
}

function mockApi(overrides: Record<string, Response | Promise<Response>> = {}) {
  const data: Record<string, unknown> = {
    "/api/meta": meta,
    "/api/experiments": summary,
    "/api/experiments/C2": experiment,
    "/api/images": { total: 1, items: [river] },
    "/api/boolean/kmap": kmap,
  };
  const mock = vi.fn<typeof fetch>(async (input) => {
    const path = String(input).split("?")[0] ?? "";
    return overrides[path] ?? Response.json(data[path] ?? []);
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

beforeEach(() => { vi.spyOn(window, "scrollTo").mockImplementation(() => undefined); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Beranda dan navigasi", () => {
  beforeAll(async () => {
    // Keep the page assertions independent of the first Vite module transform.
    await Promise.all([
      import("./pages/home"),
      import("./pages/boolean"),
      import("./pages/experiments"),
      import("./pages/inspector"),
    ]);
  });

  it("menampilkan enam rute serta metrik dari meta dan hasil C2", async () => {
    const fetchMock = mockApi();
    app();
    const nav = within(screen.getByRole("navigation", { name: "Navigasi utama" }));
    expect(nav.getAllByRole("link")).toHaveLength(6);
    expect(nav.getByRole("link", { name: "Beranda" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByRole("heading", { name: /bumi, dalam fokus/i })).toBeVisible();
    expect(await screen.findByText("27.000")).toBeInTheDocument();
    expect(await screen.findByText("79,6%")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("/api/experiments/C2", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(screen.getByRole("heading", { name: /tiga langkah sederhana/i })).toBeVisible();

    fireEvent.change(screen.getByRole("textbox", { name: "Cari ID atau kelas citra" }), { target: { value: "River_12" } });
    fireEvent.click(screen.getByRole("button", { name: "Tampilkan" }));
    expect(await screen.findByRole("img", { name: "Citra EuroSAT River_12" })).toHaveAttribute("src", river.thumb_url);
    fireEvent.click(nav.getByRole("link", { name: "Lab Boolean" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Lab Boolean" })).toBeVisible();
    expect(nav.getByRole("link", { name: "Lab Boolean" })).toHaveAttribute("aria-current", "page");
  });

  it("menampilkan keadaan kosong dan toast ketika ringkasan gagal", async () => {
    const fetchMock = mockApi({
      "/api/meta": Response.json({ error: { code: "INTERNAL_ERROR", message: "Data sementara tidak tersedia." } }, { status: 500 }),
      "/api/experiments": Response.json([]),
      "/api/images": Response.json({ total: 0, items: [] }),
    });
    app();
    expect(await screen.findByText("Ringkasan dataset tidak dapat dimuat.")).toBeInTheDocument();
    expect(await screen.findByText("Galeri belum tersedia. Citra referensi tetap dapat dilihat.")).toBeVisible();
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/experiments/C2")).toBe(false);
  });

  it("menampilkan skeleton saat galeri dimuat dan memberi label yang tepat pada citra pengganti", async () => {
    let resume = () => {};
    const waiting = new Promise<void>((resolve) => { resume = resolve; });
    mockApi({
      "/api/meta": waiting.then(() => Response.json(meta)),
      "/api/images": waiting.then(() => Response.json({ total: 1, items: [river] })),
    });
    app();
    expect(await screen.findByLabelText("Memuat galeri EuroSAT")).toBeVisible();
    expect(screen.getByLabelText("Memuat citra terindeks")).toBeVisible();
    resume();

    await screen.findByText("79,6%");
    fireEvent.change(screen.getByRole("textbox", { name: "Cari ID atau kelas citra" }), { target: { value: "Sungai" } });
    fireEvent.click(screen.getByRole("button", { name: "Tampilkan" }));
    const image = await screen.findByRole("img", { name: "Citra EuroSAT River_12" });
    fireEvent.error(image);

    expect(screen.getByRole("img", { name: "Komposit satelit Delta Sungai Lena" })).toBeVisible();
    expect(screen.getByText("Citra EuroSAT tidak dapat dimuat. Menampilkan citra referensi.")).toBeVisible();
  });

  it("membuka Lab, Percobaan, dan Inspektor secara langsung", async () => {
    mockApi();
    const pages = [
      ["/boolean", "Lab Boolean"],
      ["/percobaan", "Percobaan"], ["/inspector", "Inspektor Matematika"],
    ] as const;
    for (const [path, title] of pages) {
      const entry = app(path);
      expect(await within(entry.container).findByRole("heading", { name: title, level: 1 })).toBeVisible();
      entry.unmount();
    }
  });
});
