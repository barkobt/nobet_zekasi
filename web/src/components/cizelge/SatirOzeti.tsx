import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { fark, sayi, type CounterView, type Row } from "@/lib/cizelge";

/**
 * Satır sonundaki sayaçlar. Hangi sayacın görüneceğini "Görünür sayaçlar"
 * ekranı belirler (veritabanı); G · N · S her zaman görünür, geri kalanı
 * yalnız "Detayları göster" açıkken.
 *
 * Değerler GÖRÜNEN DÖNEMİ ölçer: haftalık görünümde o hafta, aylıkta o ay.
 */
export function SatirOzeti({
  satir, sayaclar, detaylar,
}: {
  satir: Row;
  sayaclar: CounterView[];
  detaylar: boolean;
}) {
  const gorunen = sayaclar.filter((c) => c.visible && (detaylar || c.always_shown));

  return (
    <div className="flex items-center justify-end gap-2.5 px-3 tabular-nums">
      {gorunen.map((c) => (
        <Sayac key={c.key} sayac={c} deger={satir.counters?.[c.key] ?? null} />
      ))}
    </div>
  );
}

function Sayac({ sayac, deger }: { sayac: CounterView; deger: number | null }) {
  // Hedefe fark tek işaretli sayaç: eksikse kırmızı (DESIGN §2 — sessiz başarı).
  const hedefFarki = sayac.key === "HF";
  const metin = deger === null
    ? "—"
    : hedefFarki ? fark(deger)
    : sayac.key === "S" ? sayi(deger)
    : String(deger);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="flex items-baseline gap-1">
          <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            {sayac.badge}
          </span>
          <span
            className={
              hedefFarki && deger !== null && deger < 0
                ? "font-medium text-danger"
                : "font-medium"
            }
          >
            {metin}
          </span>
        </span>
      </TooltipTrigger>
      <TooltipContent>{sayac.label}</TooltipContent>
    </Tooltip>
  );
}
