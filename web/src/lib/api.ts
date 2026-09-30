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
  // Gövde varsa content-type ŞART: proxy yalnız var olan başlığı iletiyor, FastAPI
  // başlıksız JSON gövdesini okumuyor ve 422 dönüyor. Çağıran açıkça verdiyse ona dokunma.
  const headers = new Headers(init?.headers);
  if (init?.body !== undefined && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  const res = await fetch(`/api${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    const govde = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${govde || res.statusText}`);
  }
  // 204 (taslak silme gibi) gövdesizdir. res.json() boş gövdede hata fırlatıyor,
  // mutasyon başarısız sayılıyor ve onSuccess'teki yenileme hiç çalışmıyordu:
  // satır sunucuda silinmiş ama ekranda F5'e kadar duruyordu.
  const metin = await res.text();
  return (metin ? JSON.parse(metin) : undefined) as T;
}
