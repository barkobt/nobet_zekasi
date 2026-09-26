"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { SolveAccepted, SolverRun } from "@/lib/taslak";

/**
 * "Çöz" → POST ile solver_runs kaydı açılır, arka planda çalışır; bu bileşen
 * GET ile durum yoklar (kuyruk sistemi yok, kararlaştırılan tasarım).
 * Yoklama yalnızca koşu sürerken açıktır; bittiğinde kendiliğinden durur.
 */
export function CozDugmesi({ draftId, calisanRunId }: { draftId: number; calisanRunId?: number }) {
  const [runId, setRunId] = useState<number | null>(calisanRunId ?? null);
  const qc = useQueryClient();

  const baslat = useMutation({
    mutationFn: () =>
      api<SolveAccepted>(`/drafts/${draftId}/solve`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ time_limit_s: 60 }),
      }),
    onSuccess: (d) => setRunId(d.run_id),
  });

  const { data: kosu } = useQuery({
    queryKey: ["solver-run", runId],
    queryFn: () => api<SolverRun>(`/solver-runs/${runId}`),
    enabled: runId !== null,
    // 1 saniyede bir yokla; koşu bitince yoklamayı kapat.
    refetchInterval: (q) => (q.state.data?.status === "CALISIYOR" ? 1000 : false),
  });

  useEffect(() => {
    if (kosu && kosu.status !== "CALISIYOR") {
      qc.invalidateQueries({ queryKey: ["drafts"] });
      setRunId(null);
    }
  }, [kosu, qc]);

  const suruyor = baslat.isPending || kosu?.status === "CALISIYOR" || runId !== null;

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => baslat.mutate()}
      disabled={suruyor}
      aria-label="Bu taslağı çöz"
    >
      {suruyor ? (
        <>
          <Loader2 size={16} strokeWidth={1.75} className="animate-spin" />
          Çalışıyor…
        </>
      ) : (
        <>
          <Play size={16} strokeWidth={1.75} />
          Çöz
        </>
      )}
    </Button>
  );
}
