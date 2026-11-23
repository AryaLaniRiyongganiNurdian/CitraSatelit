import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Choice, DataTable, Empty, Panel, Preview, RequestState } from "@/components/workbench";
import { get } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import type { ImageMeta, ImagesListResponse, Raid5Request, Raid5Response, ReuseKeyRequest, ReuseKeyResponse } from "@/types/api";
import { useSharingOperation } from "./session";

function Demos({ images, preferred }: { images: ImageMeta[]; preferred?: ImageMeta }) {
  const [firstId, setFirstId] = useState(preferred?.id ?? "");
  const [secondId, setSecondId] = useState("");
  const [thirdId, setThirdId] = useState("none");
  const [failedIndex, setFailedIndex] = useState(0);
  const reuse = useSharingOperation<ReuseKeyResponse, ReuseKeyRequest>("/sharing/attacks/reuse-key", {
    success: "Demo penggunaan ulang kunci selesai.", failure: "Demo penggunaan ulang kunci gagal.",
  });
  const raid = useSharingOperation<Raid5Response, Raid5Request>("/sharing/attacks/raid5", {
    success: "Demo paritas selesai.", failure: "Demo paritas gagal.",
  });

  const first = images.find((image) => image.id === firstId) ?? images[0];
  if (!first) return <Empty>Belum ada citra untuk demo.</Empty>;
  const sameShape = images.filter((image) => image.id !== first.id && image.width === first.width && image.height === first.height);
  const second = sameShape.find((image) => image.id === secondId) ?? sameShape[0];
  const remaining = sameShape.filter((image) => image.id !== second?.id);
  const third = remaining.find((image) => image.id === thirdId);
  const imageIds = [first.id, ...(second ? [second.id] : []), ...(third ? [third.id] : [])];
  const effectiveFailed = Math.min(failedIndex, imageIds.length - 1);
  const options = (items: ImageMeta[]) => items.map((image) => ({ label: image.id, value: image.id }));

  return <div className="lab-stack">
    <p className="dim">Demo menggunakan citra lokal dengan ukuran yang sama.</p>
    <div className="lab-fields">
      <Choice label="Citra pertama" value={first.id} options={options(images)} onChange={setFirstId} />
      {second && <Choice label="Citra kedua" value={second.id} options={options(sameShape)} onChange={setSecondId} />}
    </div>
    {!second && <Empty>Pilih citra pertama yang memiliki pasangan berukuran sama.</Empty>}
    <Tabs defaultValue="reuse">
      <TabsList aria-label="Demo XOR" variant="line">
        <TabsTrigger value="reuse">Penggunaan ulang kunci</TabsTrigger>
        <TabsTrigger value="raid">Paritas RAID-5</TabsTrigger>
      </TabsList>
      <TabsContent value="reuse" className="lab-stack">
        <div className="lab-actions">
          <Button type="button" disabled={!second || reuse.isPending} onClick={() => {
            if (second) reuse.run({ image_id_1: first.id, image_id_2: second.id });
          }}>Jalankan demo kunci</Button>
        </div>
        <RequestState pending={reuse.isPending} error={reuse.error} empty="Jalankan demo untuk membandingkan dua hasil XOR.">
          {reuse.data && <>
            <p>{reuse.data.identical ? "Kedua hasil XOR identik." : "Kedua hasil XOR berbeda."}</p>
            <DataTable columns={["C₁ ⊕ C₂", "M₁ ⊕ M₂", "Identik"]} rows={[[
              reuse.data.scalar_demo.c1_xor_c2, reuse.data.scalar_demo.m1_xor_m2, reuse.data.scalar_demo.equal,
            ]]} />
            <div className="lab-preview-grid">
              <Preview data={reuse.data.previews.i1} label="Citra pertama" />
              <Preview data={reuse.data.previews.i2} label="Citra kedua" />
              <Preview data={reuse.data.previews.i1_xor_i2} label="XOR citra sumber" />
              <Preview data={reuse.data.previews.c1} label="Citra tersandi pertama" />
              <Preview data={reuse.data.previews.c2} label="Citra tersandi kedua" />
              <Preview data={reuse.data.previews.c1_xor_c2} label="XOR citra tersandi" />
            </div>
          </>}
        </RequestState>
      </TabsContent>
      <TabsContent value="raid" className="lab-stack">
        <div className="lab-fields">
          <Choice label="Citra ketiga (opsional)" value={third?.id ?? "none"} disabled={!remaining.length}
            options={[{ value: "none", label: "Dua blok data" }, ...options(remaining)]} onChange={setThirdId} />
          <Choice label="Blok hilang" value={effectiveFailed}
            options={imageIds.map((imageId, value) => ({ value, label: "Blok " + (value + 1) + " · " + imageId }))} onChange={setFailedIndex} />
        </div>
        <div className="lab-actions">
          <Button type="button" disabled={imageIds.length < 2 || raid.isPending}
            onClick={() => raid.run({ image_ids: imageIds, failed_index: effectiveFailed })}>Pulihkan blok</Button>
        </div>
        <RequestState pending={raid.isPending} error={raid.error} empty="Pilih blok yang hilang untuk menguji pemulihan.">
          {raid.data && <>
            <p>{raid.data.identical ? "Blok pulih identik dengan aslinya." : "Blok pulih berbeda dari aslinya."} {raid.data.limitation}</p>
            <DataTable columns={["Data", "Paritas", "Blok contoh hilang", "Pulih", "Identik"]}
              rows={[[raid.data.scalar_demo.d.join(" · "), raid.data.scalar_demo.p, raid.data.scalar_demo.failed_index + 1,
                raid.data.scalar_demo.recovered, raid.data.scalar_demo.ok]]} />
            <div className="lab-preview-grid">
              {raid.data.previews.disks.map((disk, index) => <Preview key={index} data={disk} label={"Blok data " + (index + 1)} />)}
              <Preview data={raid.data.previews.parity} label="Paritas" />
              <Preview data={raid.data.previews.recovered} label="Blok hasil pemulihan" />
            </div>
          </>}
        </RequestState>
      </TabsContent>
    </Tabs>
  </div>;
}

const params = { gallery_only: true, limit: 250 };

export function AttackTabs({ image }: { image: ImageMeta | null }) {
  const gallery = useQuery({
    queryKey: ["images", params], queryFn: ({ signal }) => get<ImagesListResponse>("/images", params, signal),
  });
  useQueryError("sharing-gallery", "Citra demo tidak dapat dimuat.", gallery.error);
  const available = (gallery.data?.items ?? []).filter((item) => item.has_rgb || item.has_ms);
  const allImages = image && (image.has_rgb || image.has_ms) && !available.some((item) => item.id === image.id)
    ? [image, ...available] : available;
  return <Panel title="Demo sifat XOR" id="demo-xor">
    <RequestState pending={gallery.isPending} error={gallery.error} empty="Galeri untuk demo masih kosong." loading="Memuat citra demo">
      {allImages.length ? <Demos key={image?.id} images={allImages} preferred={image ?? undefined} /> : undefined}
    </RequestState>
  </Panel>;
}
