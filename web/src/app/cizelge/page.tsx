"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { ExcelDugmesi } from "@/components/ExcelDugmesi";
import { Izgara } from "@/components/cizelge/Izgara";
import { DonemGezgini } from "@/components/cizelge/DonemGezgini";
import { DetayDugmesi, useDetaylar } from "@/components/cizelge/DetayDugmesi";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { sayi, type Schedule } from "@/lib/cizelge";
import { aralik, iso as isoGun, type Olcek } from "@/lib/donem";
import type { components } from "@/lib/api-types";

type DraftOzet = components["schemas"]["Draft"];


/**
 * E-09: yalnızca YAYINLANMIŞ çizelgeyi gösterir ve SALT OKUNURDUR.
 * Düzenleme taslak içinden yapılır (/taslaklar/[id]) — yayınlanmış bir çizelgeyi
 * kazara değiştirmek, kimsenin haberi olmadan nöbeti değiştirmek demektir.
 */
const REFERANS_GUN = "2026-09-21";



export default function CizelgeSayfasi() {
  return (
    <Suspense fallback={null}>
      <Icerik />
    </Suspense>
  );
}

function Icerik() {
  // Görünen aralık: hafta HER ZAMAN Pazartesi–Pazar, ay 1'inden sonuna.
  const [olcek, setOlcek] = useState<Olcek>("hafta");
  const [capa, setCapa] = useState(new Date(REFERANS_GUN + "T00:00:00Z"));
  const [gorunenBas, gorunenSon] = aralik(capa, olcek);
  const pzt = isoGun(gorunenBas);
  const bitis = isoGun(gorunenSon);
  const { acik: detaylar } = useDetaylar();

  // Seçili haftayla çakışan YAYINLANMIŞ taslak
  const { data: taslaklar } = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api<DraftOzet[]>("/drafts"),
  });
  const yayinlanan = (taslaklar ?? []).find(
    (t) => t.status === "yayinlandi" && t.period_start <= bitis && t.period_end > pzt,
  );
  const taslakId = yayinlanan?.id;

  const { data, isLoading, error } = useQuery({
    queryKey: ["schedule", taslakId, pzt, bitis],
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
          {taslakId !== undefined && <ExcelDugmesi draftId={taslakId} />}
          <DonemGezgini olcek={olcek} capa={capa} onCapa={setCapa} onOlcek={setOlcek} />
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
          <Izgara data={data} detaylar={detaylar} />

          {/* DESIGN §6 alt barı — görünen dönemin toplamları */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-1 px-1">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
              <Ozet etiket="Toplam saat" deger={`${sayi(data.summary.total_hours)} sa`} />
              <Ozet etiket="Toplam gece" deger={String(data.summary.total_nights ?? 0)} />
              <Ozet
                etiket="Eksik vardiya"
                deger={String(data.summary.shortfall_count)}
                vurgu={data.summary.shortfall_count > 0}
              />
            </div>
            <DetayDugmesi />
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
