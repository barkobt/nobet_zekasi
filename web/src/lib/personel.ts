import type { components } from "@/lib/api-types";

export type PersonRow = components["schemas"]["PersonRow"];
export type PersonDetail = components["schemas"]["PersonDetail"];
export type Role = components["schemas"]["Role"];

export const CALISMA_TIPI: { deger: PersonRow["shift_eligibility"]; ad: string }[] = [
  { deger: "gunduz_gece", ad: "Gündüz + Gece" },
  { deger: "sadece_gunduz", ad: "Yalnız gündüz" },
  { deger: "sadece_gece", ad: "Yalnız gece" },
];

export const IZIN_TURU = [
  { deger: "yillik_izin", ad: "Yıllık izin" },
  { deger: "rapor", ad: "Rapor" },
  { deger: "ucretsiz_izin", ad: "Ücretsiz izin" },
  { deger: "diger", ad: "Diğer" },
] as const;

export const MUSAITLIK_TURU = [
  { deger: "off_talebi", ad: "İzin talebi" },
  { deger: "acilis_tercihi", ad: "Açılış tercihi" },
  { deger: "kapanis_tercihi", ad: "Kapanış tercihi" },
] as const;

const KISA_AY = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];

/** DESIGN §7: "21 Eyl 2026" */
export const tarih = (iso: string) => {
  const d = new Date(iso + "T00:00:00Z");
  return `${d.getUTCDate()} ${KISA_AY[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

export const bugun = () => new Date().toISOString().slice(0, 10);
