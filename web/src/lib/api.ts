/**
 * Sunucunun Türkçe açıklamasını (FastAPI `detail`) hata metninden çıkarır.
 * Kullanıcıya gösterilecek tek cümle burada: "API 409: {...}" bir sorumlu
 * hemşireye hiçbir şey anlatmaz. Açıklama yoksa null döner ve çağıran taraf
 * kendi genel mesajını kullanır.
 */
export function sunucuAciklamasi(hata: unknown): string | null {
  const metin = (hata as Error)?.message ?? "";
  const govde = metin.slice(metin.indexOf("{"));
  try {
    const d = JSON.parse(govde)?.detail;
    return typeof d === "string" ? d : null;
  } catch {
    return null;
  }
}

/** Tek fetch sarmalayıcı. Tarayıcı hep aynı origin'e gider; proxy Railway'e iletir. */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    const govde = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${govde || res.statusText}`);
  }
  return res.json() as Promise<T>;
}
