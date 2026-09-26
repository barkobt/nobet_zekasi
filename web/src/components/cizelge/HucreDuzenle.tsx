"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";
import { GOREV, type Cell } from "@/lib/cizelge";
import type { components } from "@/lib/api-types";

type CellResult = components["schemas"]["CellResult"];

const VARDIYALAR = [
  { deger: "GUNDUZ", ad: "Gündüz" },
  { deger: "GECE", ad: "Gece" },
  { deger: "IZIN", ad: "İzin" },
  { deger: "BOS", ad: "Boş" },
] as const;

/**
 * Hücreye tıklayınca açılan küçük pencere. Kaydedilen hücre source='manuel',
 * is_locked=true olur — solver ona dokunmaz.
 *
 * Kural uyarıları ENGELLEMEZ: sorumlu hemşire gerçekliği bildiğinde yazabilmeli,
 * sistem yalnız neyin ihlal edildiğini söyler (docs/ekran-haritasi.md E-09).
 */
export function HucreDuzenle({
  draftId, staffId, staffName, gun, cell, absence, children, onKaydedildi,
}: {
  draftId: number;
  staffId: number;
  staffName: string;
  gun: string;
  cell?: Cell;
  absence?: string;
  children: React.ReactNode;
  onKaydedildi: () => void;
}) {
  const [acik, setAcik] = useState(false);
  const [vardiya, setVardiya] = useState<string>(
    cell ? cell.shift_code : absence ? "IZIN" : "BOS",
  );
  const [gorevler, setGorevler] = useState<string[]>(cell?.tasks ?? []);
  const [uyarilar, setUyarilar] = useState<string[]>([]);

  const kaydet = useMutation({
    mutationFn: () =>
      api<CellResult>(`/drafts/${draftId}/cells`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          staff_id: staffId, work_date: gun,
          shift_code: vardiya,
          tasks: vardiya === "GUNDUZ" || vardiya === "GECE" ? gorevler : [],
        }),
      }),
    onSuccess: (r) => {
      onKaydedildi();
      if ((r.warnings ?? []).length) setUyarilar(r.warnings ?? []);
      else setAcik(false);
    },
  });

  const acilirken = (a: boolean) => {
    setAcik(a);
    if (a) {
      setVardiya(cell ? cell.shift_code : absence ? "IZIN" : "BOS");
      setGorevler(cell?.tasks ?? []);
      setUyarilar([]);
    }
  };

  const vardiyaSecili = vardiya === "GUNDUZ" || vardiya === "GECE";

  return (
    <Popover open={acik} onOpenChange={acilirken}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="w-[260px] p-3" align="center">
        <div className="mb-2" style={{ fontSize: "var(--text-xs)" }}>
          <span className="font-medium">{staffName}</span>
          <span className="text-muted-foreground"> · {gun.slice(8)}.{gun.slice(5, 7)}</span>
        </div>

        <div className="mb-3 grid grid-cols-2 gap-1">
          {VARDIYALAR.map((v) => (
            <button
              key={v.deger}
              type="button"
              onClick={() => setVardiya(v.deger)}
              aria-pressed={vardiya === v.deger}
              className={
                "h-8 rounded-md border transition-colors " +
                (vardiya === v.deger
                  ? "border-brand bg-brand text-white"
                  : "hover:bg-accent")
              }
              style={{ fontSize: "var(--text-xs)" }}
            >
              {v.ad}
            </button>
          ))}
        </div>

        {vardiyaSecili && (
          <div className="mb-3">
            <span className="mb-1 block text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              Görev
            </span>
            <div className="flex gap-1">
              {Object.entries(GOREV).map(([kod, g]) => {
                const secili = gorevler.includes(kod);
                return (
                  <button
                    key={kod}
                    type="button"
                    onClick={() =>
                      setGorevler((v) => (secili ? v.filter((x) => x !== kod) : [...v, kod]))
                    }
                    aria-pressed={secili}
                    title={g.tam}
                    className={
                      "h-7 flex-1 rounded-sm border transition-colors " +
                      (secili ? "border-brand bg-brand-soft text-brand" : "hover:bg-accent")
                    }
                    style={{ fontSize: "var(--text-xs)" }}
                  >
                    {g.kisa}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Uyarı engellemez, bildirir */}
        {uyarilar.length > 0 && (
          <div className="mb-2">
            {uyarilar.map((u) => (
              <p key={u} className="text-danger" style={{ fontSize: "var(--text-xs)" }}>{u}</p>
            ))}
            <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              Kaydedildi.
            </p>
          </div>
        )}

        <div className="flex gap-2">
          <Button size="sm" className="flex-1" onClick={() => kaydet.mutate()}
                  disabled={kaydet.isPending}>
            {kaydet.isPending ? "…" : "Kaydet"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => setAcik(false)}>Kapat</Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
