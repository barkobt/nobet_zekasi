"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { Izgara } from "@/components/cizelge/Izgara";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { sayi, type Schedule } from "@/lib/cizelge";
import type { components } from "@/lib/api-types";

type DraftOzet = components["schemas"]["Draft"];

/** pzt + 6 gün (kapsayıcı son gün) */
const bitisHesap = (pzt: string) => {
  const d = new Date(pzt + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + 6);
  return d.toISOString().slice(0, 10);
};

/**
 * E-09: yalnızca YAYINLANMIŞ çizelgeyi gösterir ve SALT OKUNURDUR.
 * Düzenleme taslak içinden yapılır (/taslaklar/[id]) — yayınlanmış bir çizelgeyi
 * kazara değiştirmek, kimsenin haberi olmadan nöbeti değiştirmek demektir.
 */
const REFERANS_PZT = "2026-09-21";

const isoGun = (d: Date) => d.toISOString().slice(0, 10);
const haftaKaydir = (pzt: string, adet: number) => {
  const d = new Date(pzt + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + adet * 7);
  return isoGun(d);
};

const AY_ADI = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
const araliktaEtiket = (pzt: string) => {
  const b = new Date(pzt + "T00:00:00Z");
  const s = new Date(b); s.setUTCDate(s.getUTCDate() + 6);
  const ayB = AY_ADI[b.getUTCMonth()], ayS = AY_ADI[s.getUTCMonth()];
  return ayB === ayS
    ? `${b.getUTCDate()}–${s.getUTCDate()} ${ayS} ${s.getUTCFullYear()}`
    : `${b.getUTCDate()} ${ayB} – ${s.getUTCDate()} ${ayS} ${s.getUTCFullYear()}`;
};

export default function CizelgeSayfasi() {
  return (
    <Suspense fallback={null}>
      <Icerik />
    </Suspense>
  );
}

function Icerik() {
  const [pzt, setPzt] = useState(REFERANS_PZT);

  // Seçili haftayla çakışan YAYINLANMIŞ taslak
  const { data: taslaklar } = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api<DraftOzet[]>("/drafts"),
  });
  const yayinlanan = (taslaklar ?? []).find(
    (t) => t.status === "yayinlandi" && t.period_start <= bitisHesap(pzt) && t.period_end > pzt,
  );
  const taslakId = yayinlanan?.id;
  const son = haftaKaydir(pzt, 1);
  const bitis = isoGun(new Date(new Date(son + "T00:00:00Z").getTime() - 86400000));

  const { data, isLoading, error } = useQuery({
    queryKey: ["schedule", taslakId, pzt],
    queryFn: () => api<Schedule>(`/drafts/${taslakId}/schedule?from=${pzt}&to=${bitis}`),
    enabled: taslakId !== undefined,
  });

  return (
    <AppShell>
      {/* DESIGN §4: sayfa başlığı satırı — solda başlık, sağda hafta gezgini */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Nöbet Çizelgesi</h1>
          {data && (
            <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {data.draft.name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            aria-label="Önceki hafta"
            onClick={() => setPzt((p) => haftaKaydir(p, -1))}
          >
            <ChevronLeft size={16} strokeWidth={1.75} />
          </Button>
          <span className="min-w-[150px] text-center font-medium">{araliktaEtiket(pzt)}</span>
          <Button
            variant="outline"
            size="icon"
            aria-label="Sonraki hafta"
            onClick={() => setPzt((p) => haftaKaydir(p, 1))}
          >
            <ChevronRight size={16} strokeWidth={1.75} />
          </Button>
        </div>
      </div>

      {taslakId === undefined && taslaklar ? (
        // DESIGN §5: boş durum tek cümle + tek eylem
        <div className="flex flex-col items-center gap-3 rounded-lg border bg-card p-12">
          <p className="text-muted-foreground">Bu hafta için yayınlanmış çizelge yok.</p>
          <Button asChild><Link href="/taslaklar">Taslaklara git</Link></Button>
        </div>
      ) : error ? (
        <div className="rounded-lg border bg-card p-6">
          <p className="text-danger">Çizelge alınamadı.</p>
        </div>
      ) : isLoading || !data ? (
        <div className="rounded-lg border bg-card p-6">
          <p className="text-muted-foreground">Yükleniyor…</p>
        </div>
      ) : (
        <>
          {/* draftId verilmiyor → hücreler düzenlenemez */}
          <Izgara data={data} />

          {/* DESIGN §6 alt barı */}
          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 px-1">
            <Ozet etiket="Atanan saat" deger={`${sayi(data!.summary.total_hours)} sa`} />
            <Ozet etiket="Fazla mesai" deger={`${sayi(data!.summary.overtime_hours)} sa`} />
            <Ozet etiket="Adalet farkı" deger={`${sayi(data!.summary.fairness_gap)} sa`} />
            <Ozet
              etiket="Eksik slot"
              deger={String(data!.summary.shortfall_count)}
              vurgu={data.summary.shortfall_count > 0}
            />
          </div>

          {(data.notes ?? []).length > 0 && (
            <div className="mt-2 px-1">
              {(data.notes ?? []).map((n) => (
                <p key={n} className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {n}
                </p>
              ))}
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}

function Ozet({ etiket, deger, vurgu }: { etiket: string; deger: string; vurgu?: boolean }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {etiket}
      </span>
      <span className={vurgu ? "font-semibold text-danger" : "font-medium"}>{deger}</span>
    </span>
  );
}
