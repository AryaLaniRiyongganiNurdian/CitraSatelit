import { useState } from "react";
import { ChartRenderer } from "@/components/chart-renderer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Choice, NumberField, Panel, Preview, Stats } from "@/components/workbench";
import { formatNumber } from "@/lib/workbench";
import type { BandMode, ImageMeta, MetaResponse, ShareInfo, SplitRequest, SplitResponse } from "@/types/api";
import { ReconMetricsView } from "./reconstruction";

const bandModes: { value: BandMode; label: string }[] = [
  { value: "gray", label: "Keabuan" }, { value: "rgb", label: "RGB" },
  { value: "band", label: "Satu band" }, { value: "ms13", label: "13 band multispektral" },
];
const bands = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"];

export function ShareControls({ image, meta, defaults, busy, onSplit }: {
  image: ImageMeta | null; meta: MetaResponse | undefined; defaults?: SplitRequest; busy: boolean;
  onSplit: (request: SplitRequest) => void;
}) {
  const [bandMode, setBandMode] = useState<BandMode>(defaults?.band_mode ?? "gray");
  const [bandIndex, setBandIndex] = useState(defaults?.band_index ?? 3);
  const effectiveMode = !image?.has_ms && (bandMode === "band" || bandMode === "ms13") ? "gray" : bandMode;
  const allBands = meta?.band_names.length ? meta.band_names : bands;

  return <form className="lab-stack" onSubmit={(event) => {
    event.preventDefault();
    if (!image) return;
    const input = new FormData(event.currentTarget);
    const seed = input.get("seed");
    onSplit({
      image_id: image.id, n: Number(input.get("shares")), band_mode: effectiveMode,
      band_index: effectiveMode === "band" ? bandIndex : null,
      seed: seed === "" ? null : Number(seed),
    });
  }}>
    <div className="lab-fields">
      <NumberField label="Jumlah share" name="shares" defaultValue={defaults?.n ?? 3} min={2} max={meta?.limits.max_shares ?? 8} required />
      <Choice label="Mode band" value={effectiveMode} onChange={setBandMode}
        options={bandModes.map((option) => ({ ...option, disabled: !image?.has_ms && (option.value === "band" || option.value === "ms13") }))} />
      {effectiveMode === "band" && <Choice label="Indeks band" value={bandIndex} onChange={setBandIndex}
        options={allBands.map((label, value) => ({ value, label: value + " · " + label }))} />}
      <NumberField label="Seed" name="seed" defaultValue={defaults ? defaults.seed ?? "" : 42}
        placeholder="Bawaan server" min={0} max={Number.MAX_SAFE_INTEGER} />
    </div>
    <div className="lab-actions">
      <Button type="submit" disabled={!image || busy}>Bagi citra</Button>
      {!image && <small className="dim">Pilih citra sumber untuk memulai.</small>}
    </div>
  </form>;
}

function ShareCard({ share }: { share: ShareInfo }) {
  const [show, setShow] = useState(false);
  const label = "Share " + (share.index + 1);
  return <article className="lab-item">
    <Preview data={share.preview} label={label} />
    <Stats items={[
      { label: "Entropi", value: formatNumber(share.entropy_bits) + " bit" },
      { label: "χ²", value: formatNumber(share.chi2.stat) },
      { label: "Derajat bebas", value: formatNumber(share.chi2.df) },
      { label: "p-value", value: formatNumber(share.chi2.p_value) },
    ]} />
    <Badge variant="outline">{share.chi2.uniform_at_alpha_0_05 ? "Keseragaman tidak ditolak" : "Keseragaman ditolak"}</Badge>
    <Button size="sm" type="button" variant="outline" aria-expanded={show}
      onClick={() => setShow((current) => !current)}>{show ? "Tutup histogram" : "Lihat histogram"}</Button>
    {show && <ChartRenderer spec={{ kind: "bar", title: "Histogram " + label, x: share.histogram.map((_, index) => index),
      x_label: "Intensitas", series: [{ name: "Jumlah", y: share.histogram }] }} />}
  </article>;
}

export function ShareGallery({ data, image }: { data: SplitResponse; image: ImageMeta }) {
  return <Panel title="Galeri share" id="galeri-share">
    <div className="lab-preview-grid">
      <Preview data={data.original_preview} label={"Citra sumber · " + image.id} />
      <div className="lab-summary lab-stack">
        <Stats items={[
          { label: "Skema XOR", value: "(" + data.n + ", " + data.n + ")" },
          { label: "Tipe data", value: data.dtype },
          { label: "Seed", value: formatNumber(data.seed) },
        ]} />
        <ReconMetricsView metrics={data.reconstruction} />
      </div>
    </div>
    <div className="lab-grid">{data.shares.map((share) => <ShareCard key={share.index} share={share} />)}</div>
  </Panel>;
}
