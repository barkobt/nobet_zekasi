import type { components } from "@/lib/api-types";

export type Schedule = components["schemas"]["Schedule"];
export type DayHeader = components["schemas"]["DayHeader"];
export type ShiftHeader = components["schemas"]["ShiftHeader"];
export type Row = components["schemas"]["Row"];
export type Group = components["schemas"]["Group"];
export type Cell = components["schemas"]["Cell"];
export type SlotCoverage = components["schemas"]["SlotCoverage"];

/**
 * Görev rozetleri (DESIGN §5): kısaltma rozette, tam adı tooltip'te.
 * Hepsi TEK renk (--brand-soft) — rozet kategori ayırmaz, varlık bildirir.
 */
export const GOREV: Record<string, { kisa: string; tam: string }> = {
  TRIYAJ:   { kisa: "TRY", tam: "Triyaj" },
  AMBULANS: { kisa: "AMB", tam: "Ambulans görevi" },
  GOZLEM:   { kisa: "GÖZ", tam: "Gözlem alanı" },
};

export const IZIN_ADI: Record<string, string> = {
  yillik_izin:   "Yıllık izin",
  rapor:         "Rapor",
  ucretsiz_izin: "Ücretsiz izin",
  diger:         "İzinli",
};

/** DESIGN §7: sayı biçimi 4.158 */
export const sayi = (n: number) =>
  new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 1 }).format(n);

/** Satır sonu farkı: +12 / −8 (DESIGN §6). Eksi işareti U+2212, tire değil. */
export const fark = (n: number) =>
  n === 0 ? "0" : n > 0 ? `+${sayi(n)}` : `−${sayi(Math.abs(n))}`;
