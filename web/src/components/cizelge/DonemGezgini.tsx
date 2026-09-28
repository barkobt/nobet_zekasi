"use client";

import { CalendarDays, Check, ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { donemEtiketi, kaydir, type Olcek } from "@/lib/donem";

/**
 * Üst bardaki dönem gezgini: ‹ dönem › + takvim ikonundan Haftalık / Aylık.
 * Etiket haftalıkta "Hafta 45 · 2–8 Kas 2026", aylıkta "Kasım 2026".
 */
export function DonemGezgini({
  olcek, capa, onCapa, onOlcek,
}: {
  olcek: Olcek;
  capa: Date;
  onCapa: (yeni: Date) => void;
  onOlcek: (yeni: Olcek) => void;
}) {
  const secenekler: { deger: Olcek; ad: string }[] = [
    { deger: "hafta", ad: "Haftalık" },
    { deger: "ay", ad: "Aylık" },
  ];

  return (
    <div className="flex items-center gap-1">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="icon" aria-label="Görünüm seç">
            <CalendarDays size={16} strokeWidth={1.75} />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {secenekler.map((s) => (
            <DropdownMenuItem key={s.deger} onClick={() => onOlcek(s.deger)}>
              <Check
                size={14}
                strokeWidth={2}
                className={olcek === s.deger ? "" : "invisible"}
                aria-hidden
              />
              {s.ad}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <Button
        variant="outline"
        size="icon"
        aria-label={olcek === "hafta" ? "Önceki hafta" : "Önceki ay"}
        onClick={() => onCapa(kaydir(capa, olcek, -1))}
      >
        <ChevronLeft size={16} strokeWidth={1.75} />
      </Button>

      <span className="min-w-[215px] text-center font-medium tabular-nums">
        {donemEtiketi(capa, olcek)}
      </span>

      <Button
        variant="outline"
        size="icon"
        aria-label={olcek === "hafta" ? "Sonraki hafta" : "Sonraki ay"}
        onClick={() => onCapa(kaydir(capa, olcek, 1))}
      >
        <ChevronRight size={16} strokeWidth={1.75} />
      </Button>
    </div>
  );
}
