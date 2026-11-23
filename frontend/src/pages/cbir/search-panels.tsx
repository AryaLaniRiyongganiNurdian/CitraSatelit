import { useState } from "react";
import { ChartRenderer } from "@/components/chart-renderer";
import { Choice, DataTable, Empty, Stats } from "@/components/workbench";
import { classLabel, formatDistance, formatPercent, formatNumber } from "@/lib/workbench";
import type { ChannelStats, FeaturesResponse, MetaResponse, SearchResponse } from "@/types/api";

function ChannelDetails({ channel }: { channel: ChannelStats }) {
  const m = channel.moments;
  const mgf = channel.mgf;
  return <div className="lab-stack">
    <ChartRenderer spec={{ kind: "bar", title: "Histogram " + channel.name,
      x: channel.counts.map((_, bin) => bin), x_label: "Bin", y_label: "Jumlah",
      series: [{ name: "Jumlah piksel", y: channel.counts }] }} />
    <DataTable caption="Momen dan MLE kanal" columns={["Rata-rata", "Variansi", "Simpangan baku", "Kemencengan", "Kurtosis", "μ MLE", "σ² MLE"]}
      rows={[[m.mean, m.variance, m.std, m.skewness, m.kurtosis, channel.mle.mu_hat, channel.mle.sigma2_hat]]} />
    {m.degenerate && <small className="dim">Kanal memiliki variansi nol atau mendekati nol.</small>}
    <ChartRenderer spec={{ kind: "line", title: "Fungsi pembangkit momen (MGF)", x: mgf.t,
      x_label: "t", y_label: "M(t)", series: [{ name: channel.name, y: mgf.m }] }} />
    <DataTable columns={["Momen", "Selisih hingga", "Nilai eksak"]}
      rows={[[1, mgf.m1_fd, mgf.m1_exact], [2, mgf.m2_fd, mgf.m2_exact]]} />
    <small className="dim">{mgf.scale_note}</small>
  </div>;
}

export function QueryPanel({ features }: { features: FeaturesResponse }) {
  const [selectedChannel, setSelectedChannel] = useState(0);
  const channel = features.channels[selectedChannel] ?? features.channels[0];
  const momentTable = features.inspector.steps.find((step) => step.id === "moment-table")?.table;
  return <div className="lab-stack">
    <Stats items={[
      { label: "Citra", value: features.image.id },
      { label: "Mode", value: features.mode },
      { label: "Dimensi", value: formatNumber(features.dim) },
      { label: "Ekstraksi", value: formatNumber(features.elapsed_ms) + " ms" },
    ]} />
    {channel ? <>
      <Choice label="Kanal fitur" value={features.channels.indexOf(channel)}
        options={features.channels.map((item, index) => ({ value: index, label: item.name }))} onChange={setSelectedChannel} />
      <ChannelDetails channel={channel} />
    </> : momentTable
      ? <DataTable columns={momentTable.columns} rows={momentTable.rows} caption={momentTable.caption} />
      : <DataTable columns={["Indeks", "Nilai"]} rows={features.vector_head.map((value, index) => [index, value])}
        caption="Komponen awal vektor fitur" />}
  </div>;
}

export function ResultGrid({ result, meta }: { result: SearchResponse; meta: MetaResponse | undefined }) {
  return <div className="lab-stack">
    <Stats items={[
      { label: "Citra kueri", value: result.query.id },
      { label: "Mode dan metrik", value: result.mode + " · " + result.metric },
      { label: "Precision@" + result.k, value: formatPercent(result.precision_at_k) },
      { label: "Basis pencarian", value: formatNumber(result.db_size) + " citra" },
      { label: "Waktu pencarian", value: formatNumber(result.elapsed_ms.search) + " ms" },
    ]} />
    {result.hits.length ? <div className="lab-result-grid">
      {result.hits.map((hit) => <article className="lab-result" key={hit.id}>
        <img src={hit.thumb_url} alt={hit.id} width={64} height={64} className="pixelated" loading="lazy" />
        <p className="mono">#{hit.rank} · {hit.id}</p>
        <p>{classLabel(meta, hit.cls)}</p>
        <p className="mono">Jarak {formatDistance(hit.distance)}</p>
        {hit.same_class !== null && <span className={hit.same_class ? "lab-match" : "lab-mismatch"}>
          {hit.same_class ? "✓ Kelas sama" : "× Kelas berbeda"}
        </span>}
      </article>)}
    </div> : <Empty>Basis pencarian belum mengembalikan citra serupa.</Empty>}
    {result.precision_at_k === null && <small className="dim">Precision@k tersedia untuk citra dengan kelas yang diketahui.</small>}
  </div>;
}
