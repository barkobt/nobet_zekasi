"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { AY_ADI, aralikEtiketi, type Draft } from "@/lib/taslak";

const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Pazartesi başlangıçlı hafta (ISO). */
function haftaBasi(temel: Date, kaydir = 0) {
  const d = new Date(Date.UTC(temel.getUTCFullYear(), temel.getUTCMonth(), temel.getUTCDate()));
  const gun = (d.getUTCDay() + 6) % 7;           // Pzt = 0
  d.setUTCDate(d.getUTCDate() - gun + kaydir * 7);
  return d;
}
const gunEkle = (d: Date, n: number) => {
  const y = new Date(d); y.setUTCDate(y.getUTCDate() + n); return y;
};
const ayBasi = (temel: Date, kaydir = 0) =>
  new Date(Date.UTC(temel.getUTCFullYear(), temel.getUTCMonth() + kaydir, 1));

/** Hızlı seçenekler: her biri [başlangıç, KAPSAYICI bitiş] döndürür. */
const HIZLI: { ad: string; hesapla: () => [Date, Date] }[] = [
  { ad: "Bu hafta",     hesapla: () => { const b = haftaBasi(new Date(), 0); return [b, gunEkle(b, 6)]; } },
  { ad: "Gelecek hafta",hesapla: () => { const b = haftaBasi(new Date(), 1); return [b, gunEkle(b, 6)]; } },
  { ad: "Bu ay",        hesapla: () => { const b = ayBasi(new Date(), 0); return [b, gunEkle(ayBasi(new Date(), 1), -1)]; } },
  { ad: "Gelecek ay",   hesapla: () => { const b = ayBasi(new Date(), 1); return [b, gunEkle(ayBasi(new Date(), 2), -1)]; } },
];

const BASLANGIC_VERISI = [
  { deger: "bos",         ad: "Boş başla",                    not: "Solver sıfırdan üretir" },
  { deger: "yayinlanmis", ad: "Yayınlanmış atamalardan yükle", not: "Aynı aralıktaki yayınlanmış çizelge" },
  { deger: "referans",    ad: "Referans haftadan kopyala",     not: "21–27 Eylül, hafta gününe göre" },
] as const;

export function YeniTaslak() {
  const [acik, setAcik] = useState(false);
  const [b, s] = HIZLI[1].hesapla();                       // varsayılan: gelecek hafta
  const [bas, setBas] = useState(iso(b));
  const [bitis, setBitis] = useState(iso(s));
  const [ad, setAd] = useState("");
  const [kaynak, setKaynak] = useState<string>("bos");
  const [kilitle, setKilitle] = useState(false);
  const qc = useQueryClient();

  const onerilenAd = () => {
    const d = new Date(bas + "T00:00:00Z");
    return `${AY_ADI[d.getUTCMonth()]} ${d.getUTCFullYear()} çizelgesi`;
  };

  const olustur = useMutation({
    mutationFn: () =>
      api<Draft>("/drafts", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          period_start: bas,
          period_end: bitis,              // KAPSAYICI; API dışlayıcıya çevirir
          name: ad.trim() || onerilenAd(),
          seed_from: kaynak,
          lock_seeded: kilitle,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["drafts"] });
      setAcik(false);
    },
  });

  const gunSayisi =
    Math.round((+new Date(bitis + "T00:00:00Z") - +new Date(bas + "T00:00:00Z")) / 86400000) + 1;
  const gecerli = gunSayisi > 0;

  return (
    <Dialog open={acik} onOpenChange={setAcik}>
      <DialogTrigger asChild>
        <Button>
          <Plus size={16} strokeWidth={1.75} />
          Yeni taslak
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle style={{ fontSize: "var(--text-base)" }}>Yeni taslak</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="ad" style={{ fontSize: "var(--text-xs)" }}>Ad</Label>
            <Input id="ad" value={ad} placeholder={onerilenAd()} onChange={(e) => setAd(e.target.value)} />
          </div>

          <div className="grid gap-2">
            <Label style={{ fontSize: "var(--text-xs)" }}>Dönem</Label>
            <div className="flex flex-wrap gap-1">
              {HIZLI.map((h) => (
                <Button
                  key={h.ad}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => { const [x, y] = h.hesapla(); setBas(iso(x)); setBitis(iso(y)); }}
                >
                  {h.ad}
                </Button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Input type="date" value={bas} onChange={(e) => setBas(e.target.value)} aria-label="Başlangıç" />
              <span className="text-muted-foreground">–</span>
              <Input type="date" value={bitis} onChange={(e) => setBitis(e.target.value)} aria-label="Bitiş" />
            </div>
            <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {gecerli ? `${aralikEtiketi(bas, iso(new Date(+new Date(bitis + "T00:00:00Z") + 86400000)))} · ${gunSayisi} gün`
                       : "Bitiş tarihi başlangıçtan önce olamaz."}
            </p>
          </div>

          <div className="grid gap-1.5">
            <Label style={{ fontSize: "var(--text-xs)" }}>Başlangıç verisi</Label>
            {BASLANGIC_VERISI.map((k) => (
              <label key={k.deger} className="flex cursor-pointer items-start gap-2">
                <input
                  type="radio"
                  name="kaynak"
                  className="mt-1 accent-brand"
                  checked={kaynak === k.deger}
                  onChange={() => setKaynak(k.deger)}
                />
                <span>
                  {k.ad}
                  <span className="block text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                    {k.not}
                  </span>
                </span>
              </label>
            ))}
          </div>

          {kaynak !== "bos" && (
            <label className="flex cursor-pointer items-start gap-2">
              <input
                type="checkbox"
                className="mt-1 accent-brand"
                checked={kilitle}
                onChange={(e) => setKilitle(e.target.checked)}
              />
              <span>
                Mevcut atamaları kilitle
                <span className="block text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  Solver bunlara dokunmaz
                </span>
              </span>
            </label>
          )}

          {olustur.isError && (
            <p className="text-danger" style={{ fontSize: "var(--text-xs)" }}>
              Taslak oluşturulamadı.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setAcik(false)}>İptal</Button>
          <Button onClick={() => olustur.mutate()} disabled={olustur.isPending || !gecerli}>
            {olustur.isPending ? "Oluşturuluyor…" : "Oluştur"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
