"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { DonemGezgini } from "@/components/anasayfa/DonemGezgini";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { aralik, iso, kaydir, type Olcek } from "@/lib/donem";
import { sayi } from "@/lib/taslak";
import type { components } from "@/lib/api-types";

type Overview = components["schemas"]["Overview"];

/**
 * Ana sayfa (DESIGN §6): ortada TEK kart, başka bir şey yok.
 * Tek soru: "Bu dönemde kadro yetiyor mu?"
 */
export default function AnaSayfa() {
  const [olcek, setOlcek] = useState<Olcek>("ay");
  const [capa, setCapa] = useState(() => new Date(Date.UTC(2026, 9, 1))); // Ekim 2026
  const [bas, son] = aralik(capa, olcek);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["overview", iso(bas), iso(son)],
    queryFn: () => api<Overview>(`/overview?from=${iso(bas)}&to=${iso(son)}`),
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-[720px]">
        <div className="mb-6">
          <DonemGezgini
            etiket={data?.period_label ?? "…"}
            olcek={olcek}
            onKaydir={(yon) => setCapa((c) => kaydir(c, olcek, yon))}
            onOlcek={setOlcek}
            birim={data?.unit_name}
          />
        </div>

        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} />
        ) : isLoading ? (
          <div className="rounded-lg border bg-card p-10">
            <p className="text-muted-foreground">Yükleniyor…</p>
          </div>
        ) : !data?.draft ? (
          // DESIGN §5: boş durum tek cümle + tek eylem
          <div className="flex flex-col items-center gap-3 rounded-lg border bg-card p-12">
            <p className="text-muted-foreground">Bu dönem için çizelge yok.</p>
            <Button asChild>
              <Link href="/taslaklar">Taslak oluştur</Link>
            </Button>
          </div>
        ) : (
          <Link
            href={`/cizelge?draft=${data.draft.id}`}
            className="block rounded-lg border bg-card transition-colors hover:border-brand"
          >
            <div className="border-b px-6 py-4">
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-medium">{data.period_label}</span>
                <span className="flex shrink-0 gap-1">
                  {data.draft.is_reference_copy && (
                    <Badge
                      variant="secondary"
                      className="h-5 rounded-sm px-1.5 font-normal"
                      style={{ fontSize: "var(--text-xs)" }}
                    >
                      Referans kopya
                    </Badge>
                  )}
                  {!data.draft.is_published && (
                    <Badge
                      variant="secondary"
                      className="h-5 rounded-sm px-1.5 font-normal"
                      style={{ fontSize: "var(--text-xs)" }}
                    >
                      taslak
                    </Badge>
                  )}
                </span>
              </div>
              <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                {data.draft.name}
              </span>
            </div>

            <div className="px-6 py-8">
              {/* DESIGN §5 KPI: büyük sayı + tek satır etiket, trend oku yok */}
              <div className="flex items-baseline gap-2">
                <span style={{ fontSize: "var(--text-xl)", fontWeight: 600 }}>
                  {sayi(data.assigned_hours)}
                </span>
                <span className="text-muted-foreground" style={{ fontSize: "var(--text-lg)" }}>
                  / {sayi(data.required_hours)}
                </span>
              </div>
              {/* "Gereken" değil "Minimum kadro": atananın bunu aşması normaldir
                  (200 saatlik sözleşmeler, sorumlu ve oryantasyon saatleri). */}
              <span
                className="flex items-center gap-1 text-muted-foreground"
                style={{ fontSize: "var(--text-xs)" }}
              >
                Atanan saat / minimum kadro
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label="Minimum kadro nasıl hesaplanır"
                      onClick={(e) => e.preventDefault()}
                      className="inline-flex"
                    >
                      <Info size={16} strokeWidth={1.75} className="opacity-60" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    Vardiya başına en az kişi × vardiya süresi
                  </TooltipContent>
                </Tooltip>
              </span>
            </div>

            <div className="grid grid-cols-3 border-t">
              {/* Stub referans haftayı kopyalıyor: "kural ihlali" demek yanıltıcı olur,
                  fazla mesai ve adalet farkı da bir ÇÖZÜMÜN kalitesini ölçer. */}
              <Deger
                etiket={data.violation_label}
                deger={String(data.violation_count)}
                vurgu={!data.draft.is_reference_copy && data.violation_count > 0}
              />
              <Deger
                etiket="Fazla mesai"
                deger={data.overtime_hours == null ? "—" : `${sayi(data.overtime_hours)} sa`}
                cizgi
              />
              <Deger
                etiket="Adalet farkı"
                deger={data.fairness_gap == null ? "—" : `${sayi(data.fairness_gap)} sa`}
                cizgi
              />
            </div>
          </Link>
        )}
      </div>
    </AppShell>
  );
}

function Deger({
  etiket, deger, vurgu, cizgi,
}: { etiket: string; deger: string; vurgu?: boolean; cizgi?: boolean }) {
  return (
    <div className={"px-6 py-4 " + (cizgi ? "border-l" : "")}>
      <div className={vurgu ? "font-semibold text-danger" : "font-medium"}>{deger}</div>
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {etiket}
      </span>
    </div>
  );
}
