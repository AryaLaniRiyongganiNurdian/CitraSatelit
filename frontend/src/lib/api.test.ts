import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, get, post, postForm } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("klien API", () => {
  it("meneruskan parameter, termasuk nilai falsy dan sinyal abort", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json({ total: 0 }));
    vi.stubGlobal("fetch", fetchMock);
    const { signal } = new AbortController();

    await expect(get<{ total: number }>("/images", { gallery_only: false, offset: 0, cls: undefined }, signal))
      .resolves.toEqual({ total: 0 });
    expect(fetchMock).toHaveBeenCalledWith("/api/images?gallery_only=false&offset=0", { signal });
  });

  it("mengirim JSON dan multipart sesuai metode", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async () => Response.json({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await post("/boolean/truth-table", { expression: "a^b" });
    const form = new FormData();
    form.append("file", new Blob(["gambar"]), "citra.png");
    await postForm("/images/upload", form);

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/boolean/truth-table", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: '{"expression":"a^b"}', signal: undefined,
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/images/upload", { method: "POST", body: form, signal: undefined });
  });

  it("mempertahankan galat baku dan membungkus respons non-JSON", async () => {
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json({
        error: { code: "IMAGE_NOT_FOUND", message: "Citra tidak ditemukan.", details: { id: "Forest_0" } },
      }, { status: 404 }))
      .mockResolvedValueOnce(new Response("rusak", { status: 502, statusText: "Bad Gateway" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(get("/images/Forest_0")).rejects.toMatchObject({
      code: "IMAGE_NOT_FOUND", message: "Citra tidak ditemukan.", details: { id: "Forest_0" },
    });
    await expect(get("/meta")).rejects.toEqual(new ApiError("INTERNAL_ERROR", "Bad Gateway"));
  });
});
