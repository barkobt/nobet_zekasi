import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { GOREV, IZIN_ADI, type Cell } from "@/lib/cizelge";

/**
 * Bir kişinin bir günü (DESIGN §6):
 *   Gündüz G → --surface zemin + --brand metin
 *   Gece   N → --brand zemin + beyaz metin
 *   İzin     → --bg zemin + --text-muted, desen yok
 * Saat aralığı YAZILMAZ: vardiyalar sabit.
 */
export function Hucre({ cell, absence }: { cell?: Cell; absence?: string }) {
  if (absence) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          {IZIN_ADI[absence] ?? "İzinli"}
        </span>
      </div>
    );
  }

  if (!cell) return <div className="h-full" />;

  const gece = cell.shift_label === "N";

  return (
    <div className="flex h-full flex-col items-center justify-center gap-1 py-1">
      <span
        className={
          "flex size-6 items-center justify-center rounded-sm border font-semibold " +
          (gece ? "bg-brand text-white border-brand" : "bg-card text-brand border-border")
        }
        style={{ fontSize: "var(--text-xs)" }}
        title={gece ? "Gece" : "Gündüz"}
      >
        {cell.shift_label}
      </span>

      {(cell.tasks ?? []).length > 0 && (
        <div className="flex flex-wrap justify-center gap-0.5">
          {(cell.tasks ?? []).map((kod) => (
            <Tooltip key={kod}>
              <TooltipTrigger asChild>
                <Badge
                  variant="secondary"
                  className="h-5 rounded-sm px-1 font-normal"
                  style={{ fontSize: "var(--text-xs)" }}
                >
                  {GOREV[kod]?.kisa ?? kod}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>{GOREV[kod]?.tam ?? kod}</TooltipContent>
            </Tooltip>
          ))}
        </div>
      )}
    </div>
  );
}
