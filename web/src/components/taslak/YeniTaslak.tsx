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
import { AralikSecici, gunMetni } from "./AralikSecici";

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

/** ISO 8601 hafta numarası — önerilen ad için. */
function haftaNo(d: Date): number {
  const p = gunEkle(haftaBasi(d), 3);
  const ilk = gunEkle(haftaBasi(new Date(Date.UTC(p.getUTCFullYear(), 0, 4))), 3);
  return 1 + Math.round((p.getTime() - ilk.getTime()) / (7 * 86400000));
}

/** "5–11 Eki 2026" ya da ay değişiyorsa "28 Eyl – 4 Eki 2026". */
function gunAraligi(bas: string, bitis: string): string {
  const b = new Date(bas + "T00:00:00Z");
  const s = new Date(bitis + "T00:00:00Z");
  return b.getUTCMonth() === s.getUTCMonth()
    ? `${b.getUTCDate()}–${gunMetni(bitis)}`
    : `${gunMetni(bas)} – ${gunMetni(bitis)}`;
}

/** Hızlı seçenekler: her biri [başlangıç, KAPSAYICI bitiş] döndürür. */
const HIZLI: { ad: string; hesapla: () => [Date, Date] }[] = [
  { ad: "Bu hafta",     hesapla: () => { const b = haftaBasi(new Date(), 0); return [b, gunEkle(b, 6)]; } },
  { ad: "Gelecek hafta",hesapla: () => { const b = haftaBasi(new Date(), 1); return [b, gunEkle(b, 6)]; } },
  { ad: "Bu ay",        hesapla: () => { const b = ayBasi(new Date(), 0); return [b, gunEkle(ayBasi(new Date(), 1), -1)]; } },
  { ad: "Gelecek ay",   hesapla: () => { const b = ayBasi(new Date(), 1); return [b, gunEkle(ayBasi(new Date(), 2), -1)]; } },
];

// "Referans haftadan kopyala" kalktı: o taslak arşivde, kopyalamak eski bir
// haftayı yeni döneme yaymaktan başka bir şey yapmıyordu.
const BASLANGIC_VERISI = [
  { deger: "bos",         ad: "Boş başla",
    not: "Solver sıfırdan üretir" },
  { deger: "yayinlanmis", ad: "Yayınlanmış atamalardan yükle",
    not: "Aynı aralıktaki yayınlanmış çizelgeden doldurur; çözerken başlangıç ipucu olarak kullanılır, sonuç kaynaktan kötüye gitmez" },
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

  // Önerilen ad seçilen döneme göre: tam takvim ayı → "Ekim 2026",
  // Pazartesi başlayan 7 gün → "Hafta 41 · 5–11 Eki 2026", başka → tarih aralığı.
  const onerilenAd = () => {
    const b = new Date(bas + "T00:00:00Z");
    const s2 = new Date(bitis + "T00:00:00Z");
    const gun = Math.round((+s2 - +b) / 86400000) + 1;
    const ayinSonu = gunEkle(ayBasi(b, 1), -1);
    if (b.getUTCDate() === 1 && iso(s2) === iso(ayinSonu)) {
      return `${AY_ADI[b.getUTCMonth()]} ${b.getUTCFullYear()}`;
    }
    if (gun === 7 && b.getUTCDay() === 1) {
      return `Hafta ${haftaNo(b)} · ${gunAraligi(bas, bitis)}`;
    }
    return gunAraligi(bas, bitis);
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
            <AralikSecici
              bas={bas}
              bitis={bitis}
              onSec={(b2, s2) => { setBas(b2); setBitis(s2); }}
            />
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
