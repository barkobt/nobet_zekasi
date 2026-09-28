import { CircleDot, Pin } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  GOREV, IZIN_ADI, IZIN_KISA, istekMetni, sayi, type Cell, type CellRequest,
} from "@/lib/cizelge";

/**
 * Bir kişinin bir günü (DESIGN §6):
 *   Gündüz G → --surface zemin + --brand metin
 *   Gece   N → --brand zemin + beyaz metin
 *   İzin     → --bg zemin + --text-muted, desen yok
 *
 * "Detayları göster" açıkken hücrenin üstünde vardiya saati yazar (9,5s / 14,5s).
 * İstek varsa sağ üstte küçük bir işaret durur; tooltip türü, gücü ve
 * karşılanıp karşılanmadığını söyler.
 */
export function Hucre({
  cell, absence, request, saatGoster, dar,
}: {
  cell?: Cell;
  absence?: string;
  request?: CellRequest;
  saatGoster?: boolean;
  /** Aylık görünüm: dar hücre, yalnız harf; görevler tooltip'te. */
  dar?: boolean;
}) {
  // source='manuel' ya da kilitli: kullanıcı yazmış, solver dokunmuyor.
  const elle = cell !== undefined && (cell.source === "manuel" || cell.is_locked === true);

  if (absence) {
    const tam = IZIN_ADI[absence] ?? "İzinli";
    return (
      <Sarmal request={request} elle={elle}>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex h-full items-center justify-center">
              <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                {dar ? (IZIN_KISA[absence] ?? "İ") : tam}
              </span>
            </div>
          </TooltipTrigger>
          <TooltipContent>{tam}</TooltipContent>
        </Tooltip>
      </Sarmal>
    );
  }

  if (!cell) return <Sarmal request={request}><div className="h-full" /></Sarmal>;

  const gece = cell.shift_label === "N";
  const gorevler = cell.tasks ?? [];

  const rozet = (
    <span
      className={
        "flex size-6 items-center justify-center rounded-sm border font-semibold " +
        (gece ? "bg-brand text-white border-brand" : "bg-card text-brand border-border")
      }
      style={{ fontSize: "var(--text-xs)" }}
    >
      {cell.shift_label}
    </span>
  );

  // Aylık görünümde hücre dar: yalnız harf, görevler tooltip'te.
  if (dar) {
    return (
      <Sarmal request={request} elle={elle}>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex h-full items-center justify-center">{rozet}</div>
          </TooltipTrigger>
          <TooltipContent>
            {(gece ? "Gece" : "Gündüz") + " · " + sayi(cell.hours ?? 0) + " sa"}
            {gorevler.length > 0 &&
              " · " + gorevler.map((k) => GOREV[k]?.tam ?? k).join(", ")}
          </TooltipContent>
        </Tooltip>
      </Sarmal>
    );
  }

  return (
    <Sarmal request={request} elle={elle}>
      <div className="flex h-full flex-col items-center justify-center gap-0.5 py-1">
        {saatGoster && (
          <span
            className="leading-none text-muted-foreground tabular-nums"
            style={{ fontSize: "var(--text-xs)" }}
          >
            {sayi(cell.hours ?? 0)}s
          </span>
        )}
        <span title={gece ? "Gece" : "Gündüz"}>{rozet}</span>

        {gorevler.length > 0 && (
          <div className="flex flex-wrap justify-center gap-0.5">
            {gorevler.map((kod) => (
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
    </Sarmal>
  );
}

/**
 * Hücrenin köşe işaretleri: sağ üstte istek, sol altta "elle yazıldı".
 * İkisi de yoksa hiçbir sarmalayıcı eklenmez.
 */
function Sarmal({
  request, elle, children,
}: {
  request?: CellRequest;
  elle?: boolean;
  children: React.ReactNode;
}) {
  if (!request && !elle) return <>{children}</>;
  return (
    <div className="relative h-full">
      {children}
      {elle && (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="absolute bottom-0.5 left-0.5 leading-none">
              <Pin
                size={10}
                strokeWidth={2}
                className="text-muted-foreground"
                aria-label="Elle yazıldı — solver değiştirmez"
              />
            </span>
          </TooltipTrigger>
          <TooltipContent>Elle yazıldı — solver bu hücreyi değiştirmez.</TooltipContent>
        </Tooltip>
      )}
      {request && (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="absolute right-0.5 top-0.5 leading-none">
            <CircleDot
              size={11}
              strokeWidth={2}
              className={request.met ? "text-muted-foreground" : "text-warn"}
              aria-label={istekMetni(request)}
            />
          </span>
        </TooltipTrigger>
        <TooltipContent>
          {istekMetni(request)}
          {request.note ? ` — ${request.note}` : ""}
        </TooltipContent>
      </Tooltip>
      )}
    </div>
  );
}
