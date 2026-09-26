"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Loader2, Menu, Play } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { Izgara } from "@/components/cizelge/Izgara";
import { TaslakPaneli } from "@/components/taslak/TaslakPaneli";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { sayi, type Schedule } from "@/lib/cizelge";
import { aralikEtiketi, type Draft, type SolveAccepted, type SolverRun } from "@/lib/taslak";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const gunEkle = (i: string, n: number) => {
  const d = new Date(i + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return iso(d);
};

export default function TaslakSayfasi({ params }: { params: Promise<{ id: string }> }) {
  const draftId = Number(use(params).id);
  const qc = useQueryClient();
  const [panel, setPanel] = useState(false);
  const [runId, setRunId] = useState<number | null>(null);

  const { data: taslak } = useQuery({
    queryKey: ["draft", draftId],
    queryFn: () => api<Draft>(`/drafts/${draftId}`),
  });

  // Görünen aralık: taslağın kendi dönemi. Uzun dönemde haftaya bölünür.
  const [ofset, setOfset] = useState(0);
  const bas = taslak ? gunEkle(taslak.period_start, ofset * 7) : null;
  const sonrakiHafta = bas ? gunEkle(bas, 6) : null;
  const taslakSon = taslak ? gunEkle(taslak.period_end, -1) : null;
  const son = sonrakiHafta && taslakSon
    ? (sonrakiHafta > taslakSon ? taslakSon : sonrakiHafta)
    : null;

  const { data: cizelge, isLoading } = useQuery({
    queryKey: ["schedule", draftId, bas, son],
    queryFn: () => api<Schedule>(`/drafts/${draftId}/schedule?from=${bas}&to=${son}`),
    enabled: !!bas && !!son,
  });

  const tazele = () => {
    qc.invalidateQueries({ queryKey: ["schedule", draftId] });
    qc.invalidateQueries({ queryKey: ["draft", draftId] });
  };

  const coz = useMutation({
    mutationFn: () =>
      api<SolveAccepted>(`/drafts/${draftId}/solve`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ time_limit_s: 60 }),
      }),
    onSuccess: (d) => setRunId(d.run_id),
  });

  const { data: kosu } = useQuery({
    queryKey: ["solver-run", runId],
    queryFn: () => api<SolverRun>(`/solver-runs/${runId}`),
    enabled: runId !== null,
    refetchInterval: (q) => (q.state.data?.status === "CALISIYOR" ? 1000 : false),
  });

  if (kosu && kosu.status !== "CALISIYOR" && runId !== null) {
    setRunId(null);
    tazele();
  }

  const calisiyor = coz.isPending || runId !== null;
  const sonHafta = taslak && bas && gunEkle(bas, 7) > gunEkle(taslak.period_end, -1);

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-3">
          <Button variant="ghost" size="icon" asChild aria-label="Taslaklara dön">
            <Link href="/taslaklar"><ChevronLeft size={16} strokeWidth={1.75} /></Link>
          </Button>
          <h1 className="truncate" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
            {taslak?.name ?? "…"}
          </h1>
          {taslak && (
            <span className="shrink-0 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {aralikEtiketi(taslak.period_start, taslak.period_end)}
            </span>
          )}
          {taslak?.last_run?.is_reference_copy && (
            <Badge variant="secondary" className="h-5 shrink-0 rounded-sm px-1.5 font-normal"
                   style={{ fontSize: "var(--text-xs)" }}>
              Referans kopya
            </Badge>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {taslak && taslak.day_count > 7 && (
            <>
              <Button variant="outline" size="icon" aria-label="Önceki hafta"
                      disabled={ofset === 0} onClick={() => setOfset((o) => o - 1)}>
                <ChevronLeft size={16} strokeWidth={1.75} />
              </Button>
              <Button variant="outline" size="icon" aria-label="Sonraki hafta"
                      disabled={!!sonHafta} onClick={() => setOfset((o) => o + 1)}>
                <ChevronRight size={16} strokeWidth={1.75} />
              </Button>
            </>
          )}

          <Button onClick={() => coz.mutate()} disabled={calisiyor} className="ml-1">
            {calisiyor ? (
              <><Loader2 size={16} strokeWidth={1.75} className="animate-spin" />Çözülüyor…</>
            ) : (
              <><Play size={16} strokeWidth={1.75} />Çöz</>
            )}
          </Button>

          <Button variant="outline" size="icon" onClick={() => setPanel(true)} aria-label="Taslak menüsü">
            <Menu size={16} strokeWidth={1.75} />
          </Button>
        </div>
      </div>

      {isLoading || !cizelge ? (
        <div className="rounded-lg border bg-card p-6">
          <p className="text-muted-foreground">Yükleniyor…</p>
        </div>
      ) : (
        <>
          <Izgara data={cizelge} draftId={draftId} onDegisti={tazele} />

          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 px-1">
            <Ozet etiket="Atanan saat" deger={`${sayi(cizelge.summary.total_hours)} sa`} />
            <Ozet etiket="Adalet farkı" deger={`${sayi(cizelge.summary.fairness_gap)} sa`} />
            <Ozet etiket="Eksik slot" deger={String(cizelge.summary.shortfall_count)}
                  vurgu={cizelge.summary.shortfall_count > 0} />
          </div>

          {(cizelge.notes ?? []).length > 0 && (
            <div className="mt-2 px-1">
              {(cizelge.notes ?? []).map((n) => (
                <p key={n} className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {n}
                </p>
              ))}
            </div>
          )}
        </>
      )}

      {taslak && (
        <TaslakPaneli acik={panel} onKapat={() => setPanel(false)} taslak={taslak} />
      )}
    </AppShell>
  );
}

function Ozet({ etiket, deger, vurgu }: { etiket: string; deger: string; vurgu?: boolean }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>{etiket}</span>
      <span className={vurgu ? "font-semibold text-danger" : "font-medium"}>{deger}</span>
    </span>
  );
}
