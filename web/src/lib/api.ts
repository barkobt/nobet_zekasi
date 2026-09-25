/** Tek fetch sarmalayıcı. Tarayıcı hep aynı origin'e gider; proxy Railway'e iletir. */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    const govde = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${govde || res.statusText}`);
  }
  return res.json() as Promise<T>;
}
