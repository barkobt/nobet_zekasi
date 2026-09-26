import type { components } from "@/lib/api-types";

export type Draft = components["schemas"]["Draft"];
export type SolverRun = components["schemas"]["SolverRun"];
export type DiagnosticGroup = components["schemas"]["DiagnosticGroup"];
export type SolveAccepted = components["schemas"]["SolveAccepted"];

export const AY_ADI = [
  "Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
  "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık",
];

/** DESIGN §7: tarih biçimi "21 Eyl 2026" */
export const KISA_AY = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];

/**
 * Taslağın aralığını insan diliyle yazar. period_end DIŞLAYICIdır, son gün bir eksik.
 *   tam ay        → "Ekim 2026"
 *   tek gün       → "23 Eyl 2026"
 *   aynı ay içi   → "21–27 Eyl 2026"
 *   ay aşan       → "28 Eyl – 4 Eki 2026"
 */
export const aralikEtiketi = (basIso: string, bitisIso: string) => {
  const b = new Date(basIso + "T00:00:00Z");
  const s = new Date(bitisIso + "T00:00:00Z");
  s.setUTCDate(s.getUTCDate() - 1); // dışlayıcı → kapsayıcı son gün

  const sonrakiAy = new Date(Date.UTC(b.getUTCFullYear(), b.getUTCMonth() + 1, 1));
  const bitisDis = new Date(bitisIso + "T00:00:00Z");
  if (b.getUTCDate() === 1 && bitisDis.getTime() === sonrakiAy.getTime())
    return `${AY_ADI[b.getUTCMonth()]} ${b.getUTCFullYear()}`;

  if (b.getTime() === s.getTime())
    return `${b.getUTCDate()} ${KISA_AY[b.getUTCMonth()]} ${b.getUTCFullYear()}`;

  if (b.getUTCMonth() === s.getUTCMonth() && b.getUTCFullYear() === s.getUTCFullYear())
    return `${b.getUTCDate()}–${s.getUTCDate()} ${KISA_AY[s.getUTCMonth()]} ${s.getUTCFullYear()}`;

  return `${b.getUTCDate()} ${KISA_AY[b.getUTCMonth()]} – ${s.getUTCDate()} ${KISA_AY[s.getUTCMonth()]} ${s.getUTCFullYear()}`;
};

export const tarih = (iso: string) => {
  const d = new Date(iso + "T00:00:00Z");
  return `${d.getUTCDate()} ${KISA_AY[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

export const sayi = (n: number) =>
  new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 1 }).format(n);

export const DURUM_ADI: Record<string, string> = {
  taslak: "Taslak",
  yayinlandi: "Yayınlandı",
  arsiv: "Arşiv",
};

/**
 * Koşu durumunun rengi. DESIGN §2: yeşil yok, "sessiz başarı".
 * Çalışıyor nötr, çözülemedi/hata kırmızı, geri kalan nötr.
 */
export const kosuRengi = (status: string) =>
  status === "INFEASIBLE" || status === "HATA" ? "text-danger" : "text-muted-foreground";
