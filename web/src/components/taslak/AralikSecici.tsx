"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { AY_ADI, AY_KISA, ayBasi, gunEkle, haftaBasi, iso } from "@/lib/donem";

/**
 * Türkçe, PAZARTESİ başlayan takvim. Tarayıcının yerleşik <input type="date">
 * kutusu yerine: o kutu makinenin diline göre 10/05/2026 gibi ABD biçimi
 * gösteriyordu ve hangi günün hafta sonu olduğu görünmüyordu.
 *
 * Seçim: bir güne tıkla = başlangıç, ikinciye = bitiş. Hafta satırının solundaki
 * numaraya tıklamak o haftanın Pazartesi–Pazar'ını birden seçer.
 */
const GUN_BASLIK = ["Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pz"];

export const gunMetni = (i: string) => {
  const d = new Date(i + "T00:00:00Z");
  return `${d.getUTCDate()} ${AY_KISA[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

/** ISO 8601 hafta numarası. */
function haftaNo(d: Date): number {
  const p = gunEkle(haftaBasi(d), 3);
  const ilk = gunEkle(haftaBasi(new Date(Date.UTC(p.getUTCFullYear(), 0, 4))), 3);
  return 1 + Math.round((p.getTime() - ilk.getTime()) / (7 * 86400000));
}

export function AralikSecici({
  bas, bitis, onSec,
}: {
  bas: string;
  bitis: string;
  /** [başlangıç, KAPSAYICI bitiş] */
  onSec: (bas: string, bitis: string) => void;
}) {
  const [acik, setAcik] = useState(false);
  const [ay, setAy] = useState(() => ayBasi(new Date(bas + "T00:00:00Z")));
  // Yarım seçim: ilk tıklamadan sonra ikinciyi bekliyoruz.
  const [yarim, setYarim] = useState<string | null>(null);

  function gunSec(g: string) {
    if (yarim === null) {
      setYarim(g);
      return;
    }
    const [a, b] = yarim <= g ? [yarim, g] : [g, yarim];
    onSec(a, b);
    setYarim(null);
    setAcik(false);
  }

  function haftaSec(pzt: Date) {
    onSec(iso(pzt), iso(gunEkle(pzt, 6)));
    setYarim(null);
    setAcik(false);
  }

  // Görünen ayın ızgarası: ayın ilk gününün haftasının Pazartesi'sinden 6 hafta.
  const ilkPzt = haftaBasi(ay);
  const haftalar = Array.from({ length: 6 }, (_, h) =>
    Array.from({ length: 7 }, (_, g) => gunEkle(ilkPzt, h * 7 + g)),
  );

  const secimBas = yarim ?? bas;
  const secimSon = yarim ?? bitis;

  return (
    <Popover open={acik} onOpenChange={(a) => { setAcik(a); if (!a) setYarim(null); }}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="h-9 w-full justify-start font-normal">
          {gunMetni(bas)} – {gunMetni(bitis)}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-auto p-3" align="start">
        <div className="mb-2 flex items-center justify-between gap-2">
          <Button variant="ghost" size="icon" aria-label="Önceki ay"
                  onClick={() => setAy(ayBasi(ay, -1))}>
            <ChevronLeft size={16} strokeWidth={1.75} />
          </Button>
          <span className="font-medium">
            {AY_ADI[ay.getUTCMonth()]} {ay.getUTCFullYear()}
          </span>
          <Button variant="ghost" size="icon" aria-label="Sonraki ay"
                  onClick={() => setAy(ayBasi(ay, 1))}>
            <ChevronRight size={16} strokeWidth={1.75} />
          </Button>
        </div>

        <table className="border-collapse" style={{ fontSize: "var(--text-xs)" }}>
          <thead>
            <tr>
              <th className="w-8 pb-1 text-muted-foreground" style={{ fontWeight: 500 }}>Hf</th>
              {GUN_BASLIK.map((g) => (
                <th key={g} className="w-9 pb-1 text-muted-foreground" style={{ fontWeight: 500 }}>
                  {g}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {haftalar.map((hafta) => (
              <tr key={iso(hafta[0])}>
                <td className="p-0">
                  <button
                    type="button"
                    onClick={() => haftaSec(hafta[0])}
                    aria-label={`${haftaNo(hafta[0])}. haftayı seç`}
                    className="h-8 w-8 rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
                  >
                    {haftaNo(hafta[0])}
                  </button>
                </td>
                {hafta.map((g) => {
                  const i = iso(g);
                  const ayDisi = g.getUTCMonth() !== ay.getUTCMonth();
                  const icinde = i >= secimBas && i <= secimSon;
                  const ucta = i === secimBas || i === secimSon;
                  const haftaSonu = g.getUTCDay() === 0 || g.getUTCDay() === 6;
                  return (
                    <td key={i} className="p-0">
                      <button
                        type="button"
                        onClick={() => gunSec(i)}
                        aria-label={gunMetni(i)}
                        className={
                          "h-8 w-9 tabular-nums transition-colors " +
                          (ucta ? "font-semibold " : "") +
                          (ayDisi ? "text-muted-foreground/50 " : "") +
                          (!icinde && haftaSonu && !ayDisi ? "text-muted-foreground " : "") +
                          (ucta
                            ? "bg-brand text-white "
                            : icinde
                              ? "bg-brand-soft "
                              : "hover:bg-accent ")
                        }
                        style={ucta ? undefined : { borderRadius: 2 }}
                      >
                        {g.getUTCDate()}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        <p className="mt-2 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          {yarim
            ? `Başlangıç ${gunMetni(yarim)} — bitiş gününü seçin.`
            : "Bir güne tıklayın (başlangıç), sonra ikinci güne. Hafta numarasına tıklamak Pzt–Paz seçer."}
        </p>
      </PopoverContent>
    </Popover>
  );
}
