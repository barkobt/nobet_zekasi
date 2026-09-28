import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { DayHeader, ShiftHeader } from "@/lib/cizelge";

/**
 * DESIGN §6: gün adı + tarih + iki sayaç (G x/y, N x/y) — KİŞİ sayısı.
 * Sayaç yalnız genel mevcudu gösterir; eksikse --danger, tamsa --text-muted.
 * Tam olan yeşile boyanmaz (DESIGN §2: sessiz başarı, gürültülü sorun).
 *
 * Tooltip her vardiya için AYRI açılır: G'nin üstünde gündüz, N'nin üstünde gece.
 */
export function GunBasligi({ gun, dar }: { gun: DayHeader; dar?: boolean }) {
  // Aylık görünümde 31 sütun var: gün adı ve tarih tek satıra iner, sayaçlar
  // alt alta. Tooltip aynı kalır — detay hep orada.
  return (
    <div className={"flex flex-col items-center px-1 py-2 " + (dar ? "gap-0.5" : "gap-1")}>
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {dar ? gun.weekday.slice(0, 1) : gun.weekday}
      </span>
      <span className="font-medium tabular-nums" style={{ fontSize: "var(--text-xs)" }}>
        {dar ? gun.label.split(" ")[0] : gun.label}
      </span>

      <div className={dar ? "flex flex-col items-center" : "flex gap-1.5"}>
        {gun.shifts.map((v) => (
          <Tooltip key={v.code}>
            <TooltipTrigger asChild>
              <span
                className={
                  v.assigned < v.required
                    ? "text-danger font-semibold cursor-default"
                    : "text-muted-foreground cursor-default"
                }
                style={{ fontSize: "var(--text-xs)" }}
              >
                {v.label} {v.assigned}/{v.required}
              </span>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="p-0">
              <VardiyaOzeti gun={gun} vardiya={v} />
            </TooltipContent>
          </Tooltip>
        ))}
      </div>
    </div>
  );
}

/** Tooltip içeriği. Az kelime, az sayı, kırmızı yalnız eksik satırda. */
function VardiyaOzeti({ gun, vardiya }: { gun: DayHeader; vardiya: ShiftHeader }) {
  const vardiyaAdi = vardiya.label === "N" ? "Gece" : "Gündüz";
  const kisiEksik = vardiya.assigned < vardiya.required;

  return (
    <div className="min-w-[210px] py-2" style={{ fontSize: "var(--text-xs)" }}>
      <div className="px-3 pb-2 font-medium">
        {gun.weekday} {gun.label} · {vardiyaAdi}
      </div>

      <Satir ad="Kişi" atanan={vardiya.assigned} gereken={vardiya.required} eksik={kisiEksik} />

      {(vardiya.slots ?? []).length > 0 && (
        <>
          <div className="my-1.5 border-t opacity-40" />
          {(vardiya.slots ?? []).map((s) => (
            <Satir
              key={s.slot_code}
              ad={s.label}
              atanan={s.assigned}
              gereken={s.required}
              eksik={s.assigned < s.required}
            />
          ))}
        </>
      )}

      {(vardiya.flags ?? []).length > 0 && (
        <>
          <div className="my-1.5 border-t opacity-40" />
          <div className="flex flex-wrap gap-x-3 px-3">
            {(vardiya.flags ?? []).map((f) => (
              <span key={f.label} className={f.present ? "" : "text-danger font-medium"}>
                {f.label} {f.present ? "✓" : "✗"}
              </span>
            ))}
          </div>
        </>
      )}

      {/* Tek istisna açıklama: ambulans çıkınca alan boşalıyorsa */}
      {vardiya.empty_area && (
        <>
          <div className="my-1.5 border-t opacity-40" />
          <p className="px-3 text-danger">
            Ambulans çıkınca {vardiya.empty_area} boş kalıyor.
          </p>
        </>
      )}
    </div>
  );
}

function Satir({
  ad, atanan, gereken, eksik,
}: { ad: string; atanan: number; gereken: number; eksik: boolean }) {
  return (
    <div className={"flex items-baseline gap-2 px-3 " + (eksik ? "text-danger font-medium" : "")}>
      <span className="flex-1">{ad}</span>
      <span className="tabular-nums">
        {atanan} / {gereken}
      </span>
      {/* Eksik miktarı kelimeyle: "1 eksik". Tamsa hiçbir şey yazılmaz. */}
      <span className="w-[52px] text-right">{eksik ? `${gereken - atanan} eksik` : ""}</span>
    </div>
  );
}
