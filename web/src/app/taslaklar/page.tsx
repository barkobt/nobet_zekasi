"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Stethoscope } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { CozDugmesi } from "@/components/taslak/CozDugmesi";
import { YeniTaslak } from "@/components/taslak/YeniTaslak";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import { DURUM_ADI, aralikEtiketi, sayi, tarih, type Draft } from "@/lib/taslak";

export default function TaslaklarSayfasi() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api<Draft[]>("/drafts"),
  });

  return (
    <AppShell>
      {/* DESIGN §4: ekranda TEK birincil buton */}
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Taslaklar</h1>
        <YeniTaslak />
      </div>

      <div className="rounded-lg border bg-card">
        {error ? (
          <p className="p-6 text-danger">Taslaklar alınamadı.</p>
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : data!.length === 0 ? (
          // DESIGN §5: boş durum tek cümle + tek eylem
          <div className="flex flex-col items-center gap-3 p-10">
            <p className="text-muted-foreground">Henüz taslak yok.</p>
            <YeniTaslak />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[220px]">Taslak</TableHead>
                <TableHead className="w-[140px]">Dönem</TableHead>
                <TableHead className="w-[96px]">Durum</TableHead>
                <TableHead className="w-[92px] text-right">Atanan saat</TableHead>
                <TableHead className="w-[92px] text-right">Fazla mesai</TableHead>
                <TableHead className="w-[92px] text-right">Adalet farkı</TableHead>
                <TableHead className="w-[76px] text-right">Eksik slot</TableHead>
                <TableHead className="w-[170px]">Son çalıştırma</TableHead>
                <TableHead className="w-[150px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data!.map((t) => (
                <TableRow key={t.id} className="h-10">
                  <TableCell className="font-medium">{t.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {aralikEtiketi(t.period_start, t.period_end)}
                    <span className="ml-1.5 opacity-60" style={{ fontSize: "var(--text-xs)" }}>
                      {t.day_count} gün
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className="h-5 rounded-sm px-1.5 font-normal"
                      style={{ fontSize: "var(--text-xs)" }}
                    >
                      {DURUM_ADI[t.status] ?? t.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{sayi(t.total_hours)}</TableCell>
                  <TableCell className="text-right">{sayi(t.overtime_hours)}</TableCell>
                  <TableCell className="text-right">{sayi(t.fairness_gap)}</TableCell>
                  <TableCell className="text-right">
                    {/* DESIGN §2: yalnızca eksik olan kırmızı */}
                    <span className={t.shortfall_count > 0 ? "font-semibold text-danger" : "text-muted-foreground"}>
                      {t.shortfall_count}
                    </span>
                  </TableCell>
                  <TableCell>
                    <SonKosu draft={t} />
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <CozDugmesi
                        draftId={t.id}
                        calisanRunId={
                          t.last_run?.status === "CALISIYOR" ? t.last_run.id : undefined
                        }
                      />
                      {t.last_run && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button variant="ghost" size="icon" asChild aria-label="Teşhis">
                              <Link href={`/teshis?run=${t.last_run.id}`}>
                                <Stethoscope size={16} strokeWidth={1.75} />
                              </Link>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>{t.last_run.diagnostics_label}</TooltipContent>
                        </Tooltip>
                      )}
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="ghost" size="icon" asChild aria-label="Çizelge">
                            <Link href={`/cizelge?draft=${t.id}`}>
                              <CalendarDays size={16} strokeWidth={1.75} />
                            </Link>
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Çizelgeyi aç</TooltipContent>
                      </Tooltip>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </AppShell>
  );
}

function SonKosu({ draft }: { draft: Draft }) {
  const k = draft.last_run;
  if (!k) return <span className="text-muted-foreground">—</span>;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex flex-col leading-tight">
          {/* Stub çalışmasında "Çözüldü" yazmıyoruz: gerçek çözücü değil,
              referans haftanın kopyası. Etiket API'den geliyor, model.py
              devreye girince kendiliğinden kalkar. */}
          <span className={k.status === "INFEASIBLE" || k.status === "HATA" ? "text-danger" : ""}>
            {k.status_label}
          </span>
          <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            {k.finished_at ? tarih(k.finished_at.slice(0, 10)) : "sürüyor"}
            {k.elapsed_s != null && ` · ${sayi(k.elapsed_s)} sn`}
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent side="left">
        <div className="min-w-[180px]">
          <div className="flex justify-between gap-4">
            <span>Atama</span><span>{k.assignment_count}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span>{k.diagnostics_label}</span><span>{k.diagnostic_count}</span>
          </div>
          {k.is_reference_copy && (
            <p className="mt-1 max-w-[220px] opacity-70">
              Referans hafta hedef aya kopyalandı. Gerçek çözüm değil.
            </p>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
