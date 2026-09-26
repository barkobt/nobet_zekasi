"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { sayi, tarih, type DiagnosticGroup, type Draft, type SolverRun } from "@/lib/taslak";

export default function TeshisSayfasi() {
  return (
    <Suspense fallback={null}>
      <Icerik />
    </Suspense>
  );
}

function Icerik() {
  const runId = useSearchParams().get("run");

  const { data: kosu } = useQuery({
    queryKey: ["solver-run", runId],
    queryFn: () => api<SolverRun>(`/solver-runs/${runId}`),
    enabled: !!runId,
  });

  const { data: gruplar, isLoading } = useQuery({
    queryKey: ["diagnostics", runId],
    queryFn: () => api<DiagnosticGroup[]>(`/solver-runs/${runId}/diagnostics`),
    enabled: !!runId,
  });

  const { data: taslaklar } = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api<Draft[]>("/drafts"),
  });
  const taslak = taslaklar?.find((t) => t.id === kosu?.draft_id);

  if (!runId) {
    return (
      <AppShell>
        <h1 className="mb-4" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
          Çözüm Teşhisi
        </h1>
        <div className="flex flex-col items-center gap-3 rounded-lg border bg-card p-10">
          <p className="text-muted-foreground">Bir çalıştırma seçilmedi.</p>
          <Button asChild>
            <Link href="/taslaklar">Taslaklara git</Link>
          </Button>
        </div>
      </AppShell>
    );
  }

  const toplam = gruplar?.reduce((a, g) => a + g.count, 0) ?? 0;

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
            {/* Stub çalışmasında "Çözüm Teşhisi" demiyoruz: çözüm değil, kopya. */}
            {kosu?.diagnostics_label ?? "Çözüm Teşhisi"}
          </h1>
          {taslak && (
            <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {taslak.name}
            </span>
          )}
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/taslaklar">
            <ChevronLeft size={16} strokeWidth={1.75} />
            Taslaklar
          </Link>
        </Button>
      </div>

      {kosu?.is_reference_copy && (
        <div className="mb-3 rounded-lg border bg-card px-4 py-3">
          <p style={{ fontSize: "var(--text-base)" }}>
            Bu çalıştırma gerçek bir çözüm değil: referans hafta hedef aya kopyalandı.
          </p>
          <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            Aşağıdakiler kopyalanan çizelgenin kapsama eksikleri. Gerçek çözücü
            devreye girince bu liste çözümün kendi teşhisleriyle değişecek.
          </p>
        </div>
      )}

      <div className="rounded-lg border bg-card">
        {isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : !gruplar || gruplar.length === 0 ? (
          <p className="p-6 text-muted-foreground">Eksik yok.</p>
        ) : (
          <>
            <div className="flex items-baseline gap-2 border-b px-4 py-3">
              <span className="font-semibold text-danger" style={{ fontSize: "var(--text-xl)" }}>
                {toplam}
              </span>
              <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                gün-vardiya · {gruplar.length} kural
              </span>
            </div>

            <ul>
              {gruplar.map((g) => (
                <li key={g.constraint_code ?? "—"} className="border-b px-4 py-3 last:border-0">
                  <div className="flex items-baseline justify-between gap-4">
                    <div className="flex items-baseline gap-2">
                      {g.catalog_code && (
                        <Badge
                          variant="secondary"
                          className="h-5 rounded-sm px-1.5 font-normal"
                          style={{ fontSize: "var(--text-xs)" }}
                        >
                          {g.catalog_code}
                        </Badge>
                      )}
                      <span className="font-medium">{g.constraint_name}</span>
                    </div>
                    <span className="shrink-0 font-semibold text-danger">{g.count}</span>
                  </div>

                  {g.first_date && (
                    <p className="mt-0.5 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                      {tarih(g.first_date)} – {tarih(g.last_date!)}
                    </p>
                  )}

                  <ul className="mt-1.5">
                    {(g.samples ?? []).map((s) => (
                      <li
                        key={s.id}
                        className="text-muted-foreground"
                        style={{ fontSize: "var(--text-xs)" }}
                      >
                        {s.work_date && `${tarih(s.work_date)} · `}
                        {s.message}
                      </li>
                    ))}
                    {g.count > (g.samples ?? []).length && (
                      <li className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                        … ve {sayi(g.count - (g.samples ?? []).length)} tane daha
                      </li>
                    )}
                  </ul>

                  {g.samples?.[0]?.suggestion && (
                    <p className="mt-1.5" style={{ fontSize: "var(--text-xs)" }}>
                      {g.samples[0].suggestion}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </AppShell>
  );
}
