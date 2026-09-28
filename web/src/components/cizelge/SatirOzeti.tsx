import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { fark, sayi, type CounterView, type Row } from "@/lib/cizelge";

/**
 * Kişinin özet sayaçları — ızgaranın SOLUNDAKİ panelde, her sayaç ayrı gri kutuda.
 * Kutu üstte küçük etiket (G, N, S, HF…), altta değer. Kutular birbirinden ayrı
 * durur ki 5-6 sayaç yan yanayken hangi sayının hangi etikete ait olduğu karışmasın.
 *
 * Hangi sayacın görüneceğini "Görünür sayaçlar" ekranı belirler (haftalık ve aylık
 * ayrı ayarlanır); değerler görünen dönemi ölçer.
 */
export function SatirOzeti({ satir, sayaclar }: { satir: Row; sayaclar: CounterView[] }) {
  const gorunen = sayaclar.filter((c) => c.visible);
  if (gorunen.length === 0) return null;

  return (
    <div className="flex items-stretch gap-1 px-2 py-1">
      {gorunen.map((c) => (
        <Kutu key={c.key} sayac={c} deger={satir.counters?.[c.key] ?? null} />
      ))}
    </div>
  );
}

function Kutu({ sayac, deger }: { sayac: CounterView; deger: number | null }) {
  // Hedefe fark tek işaretli sayaç: eksikse kırmızı (DESIGN §2 — sessiz başarı).
  const hedefFarki = sayac.key === "HF";
  const eksik = hedefFarki && deger !== null && deger < 0;
  const metin =
    deger === null ? "—"
    : hedefFarki ? fark(deger)
    : sayac.key === "S" ? sayi(deger)
    : String(deger);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className="flex min-w-[38px] flex-col items-center justify-center rounded-sm px-1.5 py-0.5"
          style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
        >
          <span
            className="leading-none text-muted-foreground"
            style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
          >
            {sayac.badge}
          </span>
          <span
            className={"leading-tight tabular-nums " + (eksik ? "text-danger" : "")}
            style={{ fontWeight: 600 }}
          >
            {metin}
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent>{sayac.label}</TooltipContent>
    </Tooltip>
  );
}
