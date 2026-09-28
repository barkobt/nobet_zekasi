import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { DayHeader, ShiftHeader } from "@/lib/cizelge";

/**
 * DESIGN §6: gün adı + tarih + iki sayaç (G x/y, N x/y) — KİŞİ sayısı.
 * Sayaç yalnız genel mevcudu gösterir; eksikse --danger, tamsa --text-muted.
 * Tam olan yeşile boyanmaz (DESIGN §2: sessiz başarı, gürültülü sorun).
 *
 * Tooltip her vardiya için AYRI açılır: G'nin üstünde gündüz, N'nin üstünde gece.
 */
/**
 * Aylık görünümde iki harfli gün adı. Tek harf belirsiz: Pazartesi/Pazar ikisi de
 * "P", Çarşamba/Cuma/Cumartesi ikisi de "C".
 */
const GUN_IKI_HARF: Record<string, string> = {
  Pzt: "Pt", Sal: "Sa", Çar: "Ça", Per: "Pe", Cum: "Cu", Cmt: "Ct", Paz: "Pz",
};

export function GunBasligi({ gun, dar }: { gun: DayHeader; dar?: boolean }) {
  // Aylık görünümde 31 sütun yan yana: G 5/5 · N 5/5 sığmıyor, dikey yığılınca
  // okunmuyordu. Üç satır: gün adı · gün numarası · tek durum hapı.
  // Kaç kişi eksik olduğu hapta, hangi vardiyada olduğu tooltip'te.
  if (dar) {
    const eksik = gun.shifts.reduce(
      (t, v) => t + Math.max(0, v.required - v.assigned), 0,
    );
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex cursor-default flex-col items-center gap-0.5 px-0.5 py-2">
            <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {GUN_IKI_HARF[gun.weekday] ?? gun.weekday.slice(0, 2)}
            </span>
            <span className="font-medium tabular-nums" style={{ fontSize: "var(--text-xs)" }}>
              {gun.label.split(" ")[0]}
            </span>
            <span
              className={
                "rounded-sm px-1 leading-none tabular-nums " +
                (eksik > 0 ? "text-danger font-semibold" : "text-muted-foreground")
              }
              style={{
                fontSize: "var(--text-xs)",
                background: eksik > 0 ? "var(--danger-soft)" : "transparent",
              }}
            >
              {eksik > 0 ? `−${eksik}` : "✓"}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="p-0">
          <div className="py-1">
            {gun.shifts.map((v) => (
              <VardiyaOzeti key={v.code} gun={gun} vardiya={v} />
            ))}
            {gun.shifts.length === 0 && (
              <p className="px-3 py-2 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                Bu gün için ihtiyaç tanımlı değil.
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    );
  }

  return (
    <div className="flex flex-col items-center gap-1 px-1 py-2">
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {gun.weekday}
      </span>
      <span className="font-medium tabular-nums" style={{ fontSize: "var(--text-xs)" }}>
        {gun.label}
      </span>

      <div className="flex gap-1.5">
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
