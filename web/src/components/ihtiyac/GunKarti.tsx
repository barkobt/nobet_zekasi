import type { DayHeader, ShiftHeader } from "@/lib/cizelge";

/**
 * Bir günün kartı (E-06 haftalık görünüm).
 * Orquest'in Demand ekranındaki gün kartı düzeni; saatlik eğri YOK — bizde
 * 2 vardiya var, basit yatay çubuk yeterli (DESIGN §1: az laf, çok iş).
 */
export function GunKarti({ gun }: { gun: DayHeader }) {
  return (
    <div className="rounded-lg border bg-card">
      <div className="flex items-baseline justify-between border-b px-3 py-2">
        <span className="font-medium">{gun.weekday}</span>
        <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          {gun.label}
        </span>
      </div>

      <div className="divide-y">
        {gun.shifts.map((v) => (
          <Vardiya key={v.code} vardiya={v} />
        ))}
      </div>
    </div>
  );
}

function Vardiya({ vardiya }: { vardiya: ShiftHeader }) {
  const gece = vardiya.label === "N";
  return (
    <div className="px-3 py-2.5">
      <div className="mb-2 flex items-baseline gap-2">
        <span
          className={
            "flex size-5 items-center justify-center rounded-sm border font-semibold " +
            (gece ? "bg-brand text-white border-brand" : "bg-card text-brand border-border")
          }
          style={{ fontSize: "var(--text-xs)" }}
        >
          {vardiya.label}
        </span>
        <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          {gece ? "Gece" : "Gündüz"}
        </span>
      </div>

      <Cubuk ad="Genel" atanan={vardiya.assigned} gereken={vardiya.required} />
      {(vardiya.slots ?? []).map((s) => (
        <Cubuk key={s.slot_code} ad={s.label} atanan={s.assigned} gereken={s.required} />
      ))}

      {/* Yetkiler ayrı ve küçük: sayı değil var/yok */}
      {(vardiya.flags ?? []).length > 0 && (
        <div
          className="mt-1.5 flex flex-wrap gap-x-2.5"
          style={{ fontSize: "var(--text-xs)" }}
        >
          {(vardiya.flags ?? []).map((f) => (
            <span
              key={f.label}
              className={f.present ? "text-muted-foreground" : "text-danger font-medium"}
            >
              {f.label} {f.present ? "✓" : "✗"}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Yatay çubuk: dolu kısım atanan, gereken çizgisi hedef. Eksikse --danger. */
function Cubuk({ ad, atanan, gereken }: { ad: string; atanan: number; gereken: number }) {
  const eksik = atanan < gereken;
  const oran = gereken > 0 ? Math.min(atanan / gereken, 1) : 0;
  const fazla = atanan > gereken;

  return (
    <div className="mb-1 flex items-center gap-2" style={{ fontSize: "var(--text-xs)" }}>
      <span className="w-[58px] shrink-0 text-muted-foreground">{ad}</span>
      <span className="relative h-1.5 flex-1 overflow-hidden rounded-sm bg-background">
        <span
          className={"absolute inset-y-0 left-0 rounded-sm " + (eksik ? "bg-danger" : "bg-brand")}
          style={{ width: `${oran * 100}%` }}
        />
      </span>
      <span
        className={"w-[42px] shrink-0 text-right tabular-nums " + (eksik ? "text-danger font-medium" : "")}
      >
        {atanan}/{gereken}
        {fazla && <span className="opacity-0">.</span>}
      </span>
    </div>
  );
}
