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
