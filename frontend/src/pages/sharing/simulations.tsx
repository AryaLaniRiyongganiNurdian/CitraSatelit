import { useEffect, useState } from "react";
import { ChartRenderer } from "@/components/chart-renderer";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Choice, DataTable, NumberField, Panel, Preview, RequestState, Stats } from "@/components/workbench";
import { useSharing } from "@/contexts";
import { post } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import { formatNumber, formatPercent, isSessionNotFound, useDebouncedApiQuery, useInspectorResult } from "@/lib/workbench";
import type {
  BitflipRequest, BitflipResponse, ImageMeta, SecurityRequest, SecurityResponse, SplitResponse, TamperRequest, TamperResponse,
} from "@/types/api";
import { ReconMetricsView } from "./reconstruction";
import { useSharingOperation } from "./session";

const tamperModes = [
  { value: "pixel", label: "Satu piksel" }, { value: "bitflip", label: "Bit-flip acak" }, { value: "block", label: "Blok piksel" },
] satisfies { value: TamperRequest["mode"]; label: string }[];

export function TamperPanel({ session }: { session: SplitResponse }) {
  const [index, setIndex] = useState(session.shares[0]?.index ?? 0);
  const [mode, setMode] = useState<TamperRequest["mode"]>("pixel");
  const tamper = useSharingOperation<TamperResponse, TamperRequest>("/sharing/tamper", {
    sessionId: session.session_id, success: "Simulasi perubahan selesai.", failure: "Simulasi perubahan gagal.",
  });

  return <Panel title="Simulasi perubahan share" id="tamper">
    <form className="lab-stack" onSubmit={(event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const request: TamperRequest = { session_id: session.session_id, share_index: index, mode };
      if (mode === "bitflip") {
        request.p = Number(form.get("p"));
      } else {
        request.x = Number(form.get("x"));
        request.y = Number(form.get("y"));
      }
      const bit = form.get("bit");
      if (mode === "pixel" && bit !== null && bit !== "") request.bit = Number(bit);
      if (mode === "block") request.block_size = Number(form.get("size"));
      tamper.run(request);
    }}>
      <div className="lab-fields">
        <Choice label="Share yang diubah" value={index} onChange={setIndex}
          options={session.shares.map((share) => ({ value: share.index, label: "Share " + (share.index + 1) }))} />
        <Choice label="Jenis perubahan" value={mode} onChange={setMode} options={tamperModes} />
        {mode === "bitflip" ? <NumberField label="Peluang bit dibalik" name="p" min={0} max={1} step="any" defaultValue={0.01} required /> : <>
          <NumberField label="Koordinat x" name="x" min={0} max={(session.shape[1] ?? 1) - 1} defaultValue={0} required />
          <NumberField label="Koordinat y" name="y" min={0} max={(session.shape[0] ?? 1) - 1} defaultValue={0} required />
          {mode === "pixel"
            ? <NumberField key="bit" label="Indeks bit" name="bit" min={0} max={session.bits - 1} placeholder="Bit tertinggi" />
            : <NumberField key="size" label="Lebar blok (piksel)" name="size" min={1} defaultValue={4} required />}
        </>}
      </div>
      <div className="lab-actions"><Button type="submit" disabled={tamper.isPending}>Simulasikan perubahan</Button></div>
    </form>
    <RequestState pending={tamper.isPending} error={tamper.error} empty="Bandingkan tiga citra setelah simulasi.">
      {tamper.data && <>
        <div className="lab-preview-grid">
          <Preview data={tamper.data.tampered_share_preview} label={"Share " + (tamper.data.share_index + 1) + " terubah"} />
          <Preview data={tamper.data.reconstruct_preview} label="Hasil rekonstruksi terubah" />
          <Preview data={tamper.data.diff_preview} label="Selisih piksel" />
        </div>
        <Stats items={[{ label: "Elemen share berubah", value: formatNumber(tamper.data.changed_values) }]} />
        <ReconMetricsView metrics={tamper.data.metrics} />
      </>}
    </RequestState>
  </Panel>;
}

export function SecurityPanel({ session, image }: { session: SplitResponse; image: ImageMeta }) {
  const [includeCbir, setIncludeCbir] = useState(false);
  const security = useSharingOperation<SecurityResponse, SecurityRequest>("/sharing/security", {
    sessionId: session.session_id, success: "Uji keamanan selesai.", failure: "Uji keamanan gagal.",
  });
  return <Panel title="Uji keamanan share" id="keamanan">
    <p className="dim">Bandingkan entropi, keseragaman, dan kemiripan hasil rekonstruksi dari subset share.</p>
    <div className="lab-actions">
      <label className="lab-check">
        <input type="checkbox" checked={includeCbir} disabled={image.cls === null}
          onChange={(event) => setIncludeCbir(event.currentTarget.checked)} />
        Sertakan CBIR pada subset
      </label>
      <Button type="button" disabled={security.isPending}
        onClick={() => security.run({ session_id: session.session_id, run_cbir: includeCbir })}>Uji keamanan</Button>
    </div>
    <RequestState pending={security.isPending} error={security.error} empty="Jalankan pengujian untuk melihat perbandingan subset.">
      {security.data && <>
        <p>{security.data.theory.statement} Entropi acuan {formatNumber(security.data.theory.max_entropy_bits)} bit.</p>
        <DataTable columns={["Subset", "Share", "Entropi (bit)", "χ²", "p-value", "Pearson r", "MSE", "CBIR P@5", "Peluang acak", "Rahasia pulih"]}
          rows={security.data.subsets.map((row) => [
            row.label, row.subset.map((index) => index + 1).join(", "), row.entropy_bits, row.chi2.stat, row.chi2.p_value,
            row.pearson_r_with_original, row.mse_vs_original, formatPercent(row.cbir?.precision_at_k),
            formatPercent(row.cbir?.chance_level), row.reveals_secret,
          ])} />
      </>}
    </RequestState>
  </Panel>;
}

const probabilities = [0.0005, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1];

export function BitflipPanel({ session }: { session: SplitResponse }) {
  const [active, setActive] = useState(false);
  const [focus, setFocus] = useState(0.01);
  const [damaged, setDamaged] = useState(1);
  const [trials, setTrials] = useState(30);
  const { expireSession } = useSharing();
  const body: BitflipRequest = { session_id: session.session_id, p_list: [...new Set([...probabilities, focus])].sort((a, b) => a - b),
    corrupted_shares: damaged, p_focus: focus, trials };
  const simulation = useDebouncedApiQuery(["sharing", "bitflip", body], active,
    (signal) => post<BitflipResponse, BitflipRequest>("/sharing/bitflip", body, signal));
  useQueryError("sharing-bitflip", "Percobaan bit-flip gagal.", simulation.error);
  useInspectorResult("sharing", simulation.data?.inspector, simulation.dataUpdatedAt);
  useEffect(() => {
    if (isSessionNotFound(simulation.error)) expireSession(session.session_id);
  }, [expireSession, session.session_id, simulation.error]);
  const result = simulation.data;

  return <Panel title="Percobaan bit-flip" id="bitflip">
    <div className="lab-fields">
      <div className="lab-field" role="group" aria-label="Peluang fokus">
        <span className="mono dim">Peluang fokus · {formatPercent(focus)}</span>
        <Slider className="lab-slider" aria-label="Peluang fokus" min={0.0005} max={0.5} step={0.0005} value={[focus]}
          onValueChange={([value]) => { if (value !== undefined) setFocus(value); }} />
      </div>
      <div className="lab-field" role="group" aria-label="Share rusak">
        <span className="mono dim">Share rusak · {damaged}</span>
        <Slider className="lab-slider" aria-label="Share rusak" min={1} max={session.n} value={[damaged]}
          onValueChange={([value]) => { if (value !== undefined) setDamaged(value); }} />
      </div>
      <div className="lab-field" role="group" aria-label="Ulangan">
        <span className="mono dim">Ulangan · {trials}</span>
        <Slider className="lab-slider" aria-label="Ulangan" min={1} max={30} value={[trials]}
          onValueChange={([value]) => { if (value !== undefined) setTrials(value); }} />
      </div>
    </div>
    <div className="lab-actions"><Button type="button" disabled={simulation.waiting}
      onClick={() => { if (active) void simulation.refetch(); else setActive(true); }}>Jalankan percobaan bit-flip</Button></div>
    {active && <RequestState pending={simulation.waiting} error={simulation.error} empty="Belum ada sampel simulasi.">
      {result && <>
        <ChartRenderer spec={{ ...result.chart, x_label: "Peluang bit dibalik", y_label: "Proporsi galat" }} />
        <ChartRenderer spec={{ kind: "line", title: "Kurva teori · 8 bit dan 16 bit", x_label: "Peluang bit dibalik",
          y_label: "Proporsi galat", series: result.theory_curves.map((curve) => ({
            name: curve.bits + " bit", x: curve.p, y: curve.error,
          })) }} />
        <Stats items={[
          { label: "Peluang fokus", value: formatPercent(result.chebyshev.p_focus) },
          { label: "Rata-rata galat", value: formatNumber(result.chebyshev.mu) },
          { label: "Simpangan baku", value: formatNumber(result.chebyshev.sigma) },
        ]} />
        <DataTable caption="Batas Chebyshev" columns={["kσ", "Radius", "Batas teoritis", "Ekor empiris"]}
          rows={result.chebyshev.rows.map((row) => [row.k_sigma, row.r, formatPercent(row.bound), formatPercent(row.empirical_tail)])} />
        <ChartRenderer spec={{ kind: "line", title: "Posisi piksel salah pertama (geometrik)", x: result.geometric.k,
          series: [{ name: "Empiris", y: result.geometric.pmf_empirical }, { name: "Teori", y: result.geometric.pmf_theory }] }} />
      </>}
    </RequestState>}
  </Panel>;
}
