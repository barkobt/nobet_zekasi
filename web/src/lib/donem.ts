/** Dönem gezgini için ortak tarih yardımcıları. Hepsi UTC üzerinden çalışır. */

export const iso = (d: Date) => d.toISOString().slice(0, 10);

export const gunEkle = (d: Date, n: number) => {
  const y = new Date(d);
  y.setUTCDate(y.getUTCDate() + n);
  return y;
};

/** Pazartesi başlangıçlı hafta (ISO 8601). */
export function haftaBasi(temel: Date) {
  const d = new Date(Date.UTC(temel.getUTCFullYear(), temel.getUTCMonth(), temel.getUTCDate()));
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d;
}

export const ayBasi = (temel: Date, kaydir = 0) =>
  new Date(Date.UTC(temel.getUTCFullYear(), temel.getUTCMonth() + kaydir, 1));

export type Olcek = "hafta" | "ay";

/** Seçili ölçeğe göre [başlangıç, KAPSAYICI bitiş] döndürür. */
export function aralik(capa: Date, olcek: Olcek): [Date, Date] {
  if (olcek === "hafta") {
    const b = haftaBasi(capa);
    return [b, gunEkle(b, 6)];
  }
  const b = ayBasi(capa);
  return [b, gunEkle(ayBasi(capa, 1), -1)];
}

export const kaydir = (capa: Date, olcek: Olcek, yon: number) =>
  olcek === "hafta" ? gunEkle(capa, yon * 7) : ayBasi(capa, yon);

export const AY_ADI = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];
export const AY_KISA = [
  "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara",
];

/** ISO 8601 hafta numarası — üst bardaki "Hafta 45" için. */
export function haftaNo(temel: Date): number {
  // Perşembe'ye taşı: ISO haftası, yılın ilk Perşembe'sini içeren haftadır.
  const d = gunEkle(haftaBasi(temel), 3);
  const ilk = gunEkle(haftaBasi(new Date(Date.UTC(d.getUTCFullYear(), 0, 4))), 3);
  return 1 + Math.round((d.getTime() - ilk.getTime()) / (7 * 86400000));
}

/**
 * Üst bardaki dönem etiketi:
 *   hafta → "Hafta 45 · 2–8 Kas 2026"
 *   ay    → "Kasım 2026"
 */
export function donemEtiketi(capa: Date, olcek: Olcek): string {
  if (olcek === "ay") {
    const b = ayBasi(capa);
    return `${AY_ADI[b.getUTCMonth()]} ${b.getUTCFullYear()}`;
  }
  const [b, s] = aralik(capa, "hafta");
  const ayB = AY_KISA[b.getUTCMonth()];
  const ayS = AY_KISA[s.getUTCMonth()];
  const gunler =
    ayB === ayS
      ? `${b.getUTCDate()}–${s.getUTCDate()} ${ayS} ${s.getUTCFullYear()}`
      : `${b.getUTCDate()} ${ayB} – ${s.getUTCDate()} ${ayS} ${s.getUTCFullYear()}`;
  return `Hafta ${haftaNo(b)} · ${gunler}`;
}
