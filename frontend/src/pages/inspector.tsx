import { useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ImagePicker } from "@/components/image-picker";
import { InspectorView } from "@/components/inspector-view";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Choice, DataTable, Empty, NumberField, Panel, RequestState, Stats, Workbench, type Option } from "@/components/workbench";
import { useInspector, type InspectorSource } from "@/contexts";
import { post } from "@/lib/api";
import { useApiMutation, useMeta } from "@/lib/workbench";
import type { ImageMeta, PixelXorRequest, PixelXorResponse } from "@/types/api";

const sources = [
  { value: "cbir", label: "CBIR" }, { value: "sharing", label: "Berbagi Rahasia" },
  { value: "boolean", label: "Lab Boolean" }, { value: "inspector", label: "XOR piksel" },
] satisfies Option<InspectorSource>[];

function PixelControls({ image, busy, onSubmit }: {
  image: ImageMeta | null; busy: boolean; onSubmit: (request: PixelXorRequest) => void;
}) {
  const [channel, setChannel] = useState<PixelXorRequest["channel"]>("gray");
  const { data: meta } = useMeta();
  const options: Option<PixelXorRequest["channel"]>[] = [
    { value: "gray", label: "Keabuan" }, { value: "r", label: "Merah (R)" },
    { value: "g", label: "Hijau (G)" }, { value: "b", label: "Biru (B)" },
    ...(image?.has_ms ? (meta?.band_names ?? []).map((band, value) => ({ value, label: band })) : []),
  ];

  return <form className="lab-stack" onSubmit={(event) => {
    event.preventDefault();
    if (!image) return;
    const form = new FormData(event.currentTarget);
    const seed = form.get("seed");
    onSubmit({
      image_id: image.id, channel, x: Number(form.get("x")), y: Number(form.get("y")), n: Number(form.get("shares")),
      ...(seed ? { seed: Number(seed) } : {}),
    });
  }}>
    <div className="lab-fields">
      <NumberField label="Koordinat x" name="x" min={0} max={image ? image.width - 1 : undefined} defaultValue={0} required />
      <NumberField label="Koordinat y" name="y" min={0} max={image ? image.height - 1 : undefined} defaultValue={0} required />
      <Choice label="Kanal piksel" value={channel} onChange={setChannel} options={options} />
      <NumberField label="Jumlah share" name="shares" min={2} max={8} defaultValue={3} required />
      <NumberField label="Seed" name="seed" min={0} max={Number.MAX_SAFE_INTEGER} placeholder="Bawaan server" />
    </div>
    <div className="lab-actions">
      <Button type="submit" disabled={!image || busy}>Hitung XOR piksel</Button>
    </div>
  </form>;
}

function PixelExplorer({ children }: { children: ReactNode }) {
  const [image, setImage] = useState<ImageMeta | null>(null);
  const { setLatest } = useInspector();
  const compute = useApiMutation((body: PixelXorRequest) => post<PixelXorResponse, PixelXorRequest>("/inspector/pixel-xor", body), {
    failure: "XOR piksel gagal dihitung.", success: "Perhitungan XOR piksel selesai.",
    onSuccess: (data) => setLatest("inspector", data.inspector),
  });
  const current = compute.variables?.image_id === image?.id;
  const result = current ? compute.data : undefined;

  return <div className="lab-layout">
    <Panel title="Citra sumber"><ImagePicker value={image} onSelect={setImage} /></Panel>
    <div className="lab-stack">
      <Panel title="Demo XOR piksel">
        <PixelControls key={image?.id} image={image} busy={compute.isPending} onSubmit={compute.run} />
        <RequestState pending={current && compute.isPending} error={current ? compute.error : null}
          empty="Pilih citra dan koordinat untuk melihat nilai piksel dalam biner.">
          {result && <>
            <Stats items={[
              { label: "Nilai piksel", value: result.value },
              { label: "Biner", value: <code>{result.value_bin}</code> },
              { label: "Hasil XOR", value: result.reconstructed },
              { label: "Verifikasi", value: result.ok ? "Identik" : "Berbeda" },
            ]} />
            <DataTable caption="Share piksel" columns={["Share", "Nilai", "Biner"]}
              rows={result.shares.map((share) => [share.index + 1, share.value, share.bin])} />
          </>}
        </RequestState>
      </Panel>
      {children}
    </div>
  </div>;
}

export function InspectorPage() {
  const [params, setParams] = useSearchParams();
  const { latest, activeSource } = useInspector();
  const requested = params.get("source");
  const source = sources.find((option) => option.value === requested)?.value ?? activeSource ?? "cbir";
  const inspector = latest[source];
  const steps = <Panel title="Langkah perhitungan terakhir">
    {inspector ? <InspectorView inspector={inspector} /> : <>
      <Empty>{source === "inspector" ? "Jalankan demo untuk mengisi langkah dengan hasil XOR piksel." :
        "Belum ada hasil dari sumber ini pada sesi aktif. Jalankan komputasi di salah satu ruang kerja."}</Empty>
      {source !== "inspector" && <div className="lab-actions inspector-shortcuts">
        {sources.filter((option) => option.value !== "inspector").map((option) => <Button key={option.value} asChild variant="outline">
          <Link to={"/" + option.value}>Buka {option.label}</Link>
        </Button>)}
      </div>}
    </>}
  </Panel>;
  return <Workbench title="Inspektor Matematika" description="Telusuri rumus, substitusi angka, dan bukti dari komputasi terbaru pada sesi ini.">
    <Tabs value={source} onValueChange={(value) => setParams({ source: value }, { replace: true })}>
      <TabsList variant="line" aria-label="Sumber langkah perhitungan">
        {sources.map((option) => <TabsTrigger key={option.value} value={option.value}>{option.label}</TabsTrigger>)}
      </TabsList>
      <TabsContent key={source} value={source} className="inspector-sources">
        {source === "inspector" ? <PixelExplorer>{steps}</PixelExplorer> : steps}
      </TabsContent>
    </Tabs>
  </Workbench>;
}
