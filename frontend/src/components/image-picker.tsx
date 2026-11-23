import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Upload } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Choice, RequestState } from "@/components/workbench";
import { get, postForm } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import { classLabel, useApiMutation, useMeta } from "@/lib/workbench";
import type { ClassName, ImageMeta, ImagesListResponse } from "@/types/api";

const pageSize = 25;

export function validateImageUpload(file: Pick<File, "name" | "size">) {
  const extension = file.name.match(/\.([^.]+)$/)?.[1]?.toLowerCase();
  const tiff = extension === "tif" || extension === "tiff";
  if (!tiff && extension !== "jpg" && extension !== "jpeg" && extension !== "png") {
    return "Pilih berkas JPG, PNG, TIF, atau TIFF.";
  }
  const limit = tiff ? 5 : 2;
  return file.size > limit * 1024 ** 2 ? "Maksimum " + limit + " MB untuk format ini." : null;
}

export function ImagePicker({ value, onSelect }: { value: ImageMeta | null; onSelect: (image: ImageMeta) => void }) {
  const { data: meta } = useMeta();
  const [filter, setFilter] = useState<ClassName | "all">("all");
  const [offset, setOffset] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const params = { gallery_only: true, cls: filter === "all" ? undefined : filter, limit: pageSize, offset };
  const images = useQuery({
    queryKey: ["images", params],
    queryFn: ({ signal }) => get<ImagesListResponse>("/images", params, signal),
  });
  useQueryError("image-picker", "Galeri EuroSAT tidak dapat dimuat.", images.error);
  const upload = useApiMutation((form: FormData) => postForm<ImageMeta>("/images/upload", form), {
    onSuccess: onSelect, success: "Citra berhasil diunggah.", failure: "Citra gagal diunggah.",
  });

  function handleFile(file: File) {
    const issue = validateImageUpload(file);
    setUploadError(issue);
    if (issue) {
      toast.error("Format atau ukuran citra tidak valid.", { description: issue });
      return;
    }
    const form = new FormData();
    form.append("file", file);
    upload.run(form);
  }

  return <div className="lab-stack">
    <Choice<ClassName | "all"> label="Filter kelas" value={filter}
      options={[{ value: "all", label: "Semua kelas" }, ...(meta?.classes ?? []).map((cls) => ({ value: cls, label: classLabel(meta, cls) }))]}
      onChange={(cls) => { setFilter(cls); setOffset(0); }} />
    <div className="lab-image-upload">
      <label className="mono" aria-disabled={upload.isPending}>
        <Upload size={16} aria-hidden /> Unggah citra
        <Input type="file" className="sr-only" accept=".jpg,.jpeg,.png,.tif,.tiff" disabled={upload.isPending}
          onChange={(event) => {
            const file = event.currentTarget.files?.[0];
            event.currentTarget.value = "";
            if (file) handleFile(file);
          }} />
      </label>
      <small className="dim">JPG/PNG maks. 2 MB · TIFF maks. 5 MB</small>
      {uploadError && <p className="lab-inline-error" role="alert">{uploadError}</p>}
      {(upload.isPending || upload.error) && <RequestState pending={upload.isPending} error={upload.error} empty={null} loading="Mengunggah citra" />}
    </div>
    {value && <div className="lab-selection">
      <img src={value.thumb_url} alt="" className="pixelated" width={48} height={48} />
      <div><strong>{value.id}</strong><small>{classLabel(meta, value.cls)}</small></div>
      {value.has_ms && <Badge variant="outline">MS</Badge>}
    </div>}
    <RequestState pending={images.isPending} error={images.error} empty="Galeri untuk filter ini kosong." loading="Memuat galeri EuroSAT">
      {images.data?.items.length ? <>
        <div className="lab-gallery" aria-label="Galeri EuroSAT">
          {images.data.items.map((image) => <button type="button" key={image.id} aria-pressed={value?.id === image.id}
            aria-label={image.id + " · " + classLabel(meta, image.cls)} title={image.id} onClick={() => onSelect(image)}>
            <img src={image.thumb_url} alt="" loading="lazy" width={64} height={64} className="pixelated" />
            {image.has_ms && <Badge className="lab-ms">MS</Badge>}
            <span>{image.id}</span>
          </button>)}
        </div>
        <div className="lab-pagination">
          <Button type="button" variant="outline" size="icon-sm" aria-label="Halaman galeri sebelumnya" disabled={!offset}
            onClick={() => setOffset((current) => Math.max(0, current - pageSize))}><ChevronLeft aria-hidden /></Button>
          <span className="mono">{offset + 1}–{offset + images.data.items.length} / {images.data.total}</span>
          <Button type="button" variant="outline" size="icon-sm" aria-label="Halaman galeri berikutnya"
            disabled={offset + pageSize >= images.data.total}
            onClick={() => setOffset((current) => current + pageSize)}><ChevronRight aria-hidden /></Button>
        </div>
      </> : undefined}
    </RequestState>
  </div>;
}
