import type { components } from "@/lib/api-types";

export type PersonRow = components["schemas"]["PersonRow"];
export type PersonDetail = components["schemas"]["PersonDetail"];
export type Role = components["schemas"]["Role"];
export type StaffCompetency = components["schemas"]["StaffCompetency"];
export type AvailabilityRule = components["schemas"]["AvailabilityRule"];

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

/** İstek türleri. Eski adlar (off_talebi vb.) migration 020 ile kalktı. */
export const ISTEK_TURU = [
  { deger: "BOS_GUN", ad: "Boş gün" },
  { deger: "SADECE_GUNDUZ", ad: "Sadece gündüz" },
  { deger: "SADECE_GECE", ad: "Sadece gece" },
] as const;

/** İsteğin gücü: Kesin katı kuraldır, Mümkünse cezalandırılan tercihtir. */
export const ISTEK_GUCU = [
  { deger: "MUMKUNSE", ad: "Mümkünse" },
  { deger: "KESIN", ad: "Kesin" },
] as const;

const KISA_AY = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];

/** DESIGN §7: "21 Eyl 2026" */
export const tarih = (iso: string) => {
  const d = new Date(iso + "T00:00:00Z");
  return `${d.getUTCDate()} ${KISA_AY[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

export const bugun = () => new Date().toISOString().slice(0, 10);

/** Avatar baş harfleri: "Ahmet Baran Bozkurt" → "AB" (ilk ve son kelime). */
export const basHarf = (ad: string) => {
  const p = ad.split(" ").filter(Boolean);
  if (p.length === 0) return "";
  const ilk = p[0][0] ?? "";
  const son = p.length > 1 ? (p[p.length - 1][0] ?? "") : "";
  return (ilk + son).toLocaleUpperCase("tr");
};
