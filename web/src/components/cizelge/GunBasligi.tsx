import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { DayHeader } from "@/lib/cizelge";

/**
 * DESIGN §6: gün adı + tarih + iki küçük sayaç (G x/y, N x/y) — KİŞİ sayısı, saat değil.
 * Sayaç yalnızca genel mevcudu gösterir. Eksikse --danger, tamsa --text-muted.
 * TAM olan yeşile boyanmaz (DESIGN §2: sessiz başarı, gürültülü sorun).
 * Slot kırılımı (triyaj, sayım, ekip lideri, ambulans, gözlem) tooltip'te.
 */
export function GunBasligi({ gun }: { gun: DayHeader }) {
  return (
    <div className="flex flex-col items-center gap-1 px-1 py-2">
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {gun.weekday}
      </span>
      <span className="font-medium" style={{ fontSize: "var(--text-xs)" }}>
        {gun.label}
      </span>

      <div className="flex gap-1.5">
        {gun.shifts.map((v) => {
          const eksik = v.assigned < v.required;
          return (
            <Tooltip key={v.code}>
              <TooltipTrigger asChild>
                <span
                  className={eksik ? "text-danger font-semibold" : "text-muted-foreground"}
                  style={{ fontSize: "var(--text-xs)" }}
                >
                  {v.label} {v.assigned}/{v.required}
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <div className="min-w-[160px]">
                  <div className="mb-1 font-medium">
                    {v.label === "N" ? "Gece" : "Gündüz"} · genel mevcut {v.assigned}/{v.required}
                  </div>
                  {(v.slots ?? []).map((s) => {
                    const slotEksik = s.assigned < s.required;
                    // C-009: ambulans çıkınca alanda kimse kalmıyorsa bu da bir ihlal,
                    // sayaç tam olsa bile. Yalnız renkle değil metinle de bildiriliyor.
                    const alanBosalir = s.remaining_after_ambulance === 0;
                    return (
                      <div key={s.slot_code} className="flex flex-col">
                        <div className="flex justify-between gap-4">
                          <span>{s.label}</span>
                          <span className={slotEksik ? "text-danger font-semibold" : ""}>
                            {s.assigned}/{s.required}
                            {s.qualified != null && (
                              <span className="opacity-70"> · yetkin {s.qualified}</span>
                            )}
                          </span>
                        </div>
                        {s.remaining_after_ambulance != null && (
                          <span
                            className={alanBosalir ? "text-danger font-semibold" : "opacity-70"}
                            style={{ fontSize: "var(--text-xs)" }}
                          >
                            {alanBosalir
                              ? "ambulans çıkınca kimse kalmıyor"
                              : `ambulans sonrası ${s.remaining_after_ambulance} kalıyor`}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
