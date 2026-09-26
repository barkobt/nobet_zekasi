"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Olcek } from "@/lib/donem";

/** DESIGN §4 üst şeridi: ‹ dönem › · Hafta/Ay geçişi · birim. */
export function DonemGezgini({
  etiket, olcek, onKaydir, onOlcek, birim,
}: {
  etiket: string;
  olcek: Olcek;
  onKaydir: (yon: number) => void;
  onOlcek: (o: Olcek) => void;
  birim?: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-1">
        <Button variant="outline" size="icon" aria-label="Önceki dönem" onClick={() => onKaydir(-1)}>
          <ChevronLeft size={16} strokeWidth={1.75} />
        </Button>
        <span className="min-w-[160px] text-center font-medium">{etiket}</span>
        <Button variant="outline" size="icon" aria-label="Sonraki dönem" onClick={() => onKaydir(1)}>
          <ChevronRight size={16} strokeWidth={1.75} />
        </Button>
      </div>

      <div className="flex items-center gap-3">
        {/* Hafta/Ay geçişi: iki durumlu, seçili olan dolu */}
        <div className="flex rounded-md border p-0.5">
          {(["hafta", "ay"] as const).map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => onOlcek(o)}
              aria-pressed={olcek === o}
              className={
                "rounded-sm px-3 py-1 transition-colors " +
                (olcek === o ? "bg-brand text-white" : "text-muted-foreground hover:text-foreground")
              }
              style={{ fontSize: "var(--text-xs)" }}
            >
              {o === "hafta" ? "Hafta" : "Ay"}
            </button>
          ))}
        </div>

        {birim && (
          <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            {birim}
          </span>
        )}
      </div>
    </div>
  );
}
