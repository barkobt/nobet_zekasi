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
const KISA_AY = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];

export const ayEtiketi = (iso: string) => {
  const d = new Date(iso + "T00:00:00Z");
  return `${AY_ADI[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
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
