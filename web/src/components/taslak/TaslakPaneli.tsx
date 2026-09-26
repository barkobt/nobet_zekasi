"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Send, Stethoscope } from "lucide-react";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { api } from "@/lib/api";
import { sayi, tarih, type DiagnosticGroup, type Draft } from "@/lib/taslak";

/** ☰ paneli: üç büyük kart, başka bir şey yok (DESIGN §1: tek soru, az kart). */
export function TaslakPaneli({
  acik, onKapat, taslak,
}: { acik: boolean; onKapat: () => void; taslak: Draft }) {
  const [gorunum, setGorunum] = useState<"menu" | "analiz">("menu");
  const [yayinla, setYayinla] = useState(false);
  const router = useRouter();
  const qc = useQueryClient();

  const kopyala = useMutation({
    mutationFn: () =>
      api<Draft>(`/drafts/${taslak.id}/copy`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ name: `${taslak.name} (kopya)` }),
      }),
    onSuccess: (yeni) => {
      qc.invalidateQueries({ queryKey: ["drafts"] });
      onKapat();
      router.push(`/taslaklar/${yeni.id}`);
    },
  });

  const uygula = useMutation({
    mutationFn: () => api<Draft>(`/drafts/${taslak.id}/publish`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["draft", taslak.id] });
      qc.invalidateQueries({ queryKey: ["drafts"] });
      setYayinla(false);
      onKapat();
    },
  });

  return (
    <>
      <Sheet open={acik} onOpenChange={(a) => { if (!a) { onKapat(); setGorunum("menu"); } }}>
        <SheetContent className="flex w-[480px] flex-col gap-0 p-0 sm:max-w-[480px]">
          <SheetHeader className="border-b p-6">
            <SheetTitle style={{ fontSize: "var(--text-base)" }}>
              {gorunum === "analiz" ? (taslak.last_run?.diagnostics_label ?? "Analiz") : taslak.name}
            </SheetTitle>
          </SheetHeader>

          <div className="min-h-0 flex-1 overflow-y-auto p-6">
            {gorunum === "menu" ? (
              <div className="grid gap-3">
                <Kart
                  ikon={<Stethoscope size={20} strokeWidth={1.75} />}
                  baslik="Analiz"
                  aciklama={
                    taslak.last_run
                      ? `${taslak.last_run.diagnostic_count} kalem · ${taslak.shortfall_count} eksik slot`
                      : "Henüz çalıştırılmadı"
                  }
                  onClick={() => setGorunum("analiz")}
                  pasif={!taslak.last_run}
                />
                <Kart
                  ikon={<Send size={20} strokeWidth={1.75} />}
                  baslik="Taslağı uygula"
                  aciklama={
                    taslak.status === "yayinlandi"
                      ? "Bu taslak zaten yayınlandı"
                      : "Yayınlanır ve Nöbet Çizelgesi'nde görünür"
                  }
                  onClick={() => setYayinla(true)}
                  pasif={taslak.status === "yayinlandi"}
                />
                <Kart
                  ikon={<Copy size={20} strokeWidth={1.75} />}
                  baslik="Kopyala"
                  aciklama="Aynı dönem, aynı atamalar, yeni taslak"
                  onClick={() => kopyala.mutate()}
                />
              </div>
            ) : (
              <Analiz runId={taslak.last_run?.id ?? null} geri={() => setGorunum("menu")} />
            )}
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog open={yayinla} onOpenChange={setYayinla}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontSize: "var(--text-base)" }}>
              Taslak uygulansın mı?
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontSize: "var(--text-xs)" }}>
              {taslak.name} yayınlanacak ve Nöbet Çizelgesi ekranında görünecek.
              Aynı dönemde başka bir yayınlanmış çizelge varsa işlem reddedilir.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {uygula.isError && (
            <p className="text-danger" style={{ fontSize: "var(--text-xs)" }}>
              {(uygula.error as Error).message}
            </p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel>Vazgeç</AlertDialogCancel>
            <AlertDialogAction onClick={(e) => { e.preventDefault(); uygula.mutate(); }}>
              {uygula.isPending ? "Uygulanıyor…" : "Uygula"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function Kart({
  ikon, baslik, aciklama, onClick, pasif,
}: {
  ikon: React.ReactNode; baslik: string; aciklama: string;
  onClick: () => void; pasif?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pasif}
      className="flex items-start gap-3 rounded-lg border bg-card p-4 text-left transition-colors hover:border-brand disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-border"
    >
      <span className="mt-0.5 shrink-0 text-muted-foreground">{ikon}</span>
      <span className="min-w-0">
        <span className="block font-medium">{baslik}</span>
        <span className="block text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          {aciklama}
        </span>
      </span>
    </button>
  );
}

/** E-10 içeriği buraya taşındı: ayrı menü öğesi yok. */
function Analiz({ runId, geri }: { runId: number | null; geri: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["diagnostics", runId],
    queryFn: () => api<DiagnosticGroup[]>(`/solver-runs/${runId}/diagnostics`),
    enabled: runId !== null,
  });

  if (isLoading) return <p className="text-muted-foreground">Yükleniyor…</p>;
  if (!data?.length) return <p className="text-muted-foreground">Eksik yok.</p>;

  const toplam = data.reduce((a, g) => a + g.count, 0);

  return (
    <div>
      <button type="button" onClick={geri}
              className="mb-4 text-muted-foreground hover:text-foreground"
              style={{ fontSize: "var(--text-xs)" }}>
        ‹ Geri
      </button>

      <div className="mb-3 flex items-baseline gap-2">
        <span className="font-semibold text-danger" style={{ fontSize: "var(--text-xl)" }}>
          {toplam}
        </span>
        <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          gün-vardiya · {data.length} kural
        </span>
      </div>

      <ul className="grid gap-3">
        {data.map((g) => (
          <li key={g.constraint_code ?? "—"} className="rounded-lg border p-3">
            <div className="flex items-baseline justify-between gap-3">
              <span className="flex items-baseline gap-2">
                {g.catalog_code && (
                  <Badge variant="secondary" className="h-5 rounded-sm px-1.5 font-normal"
                         style={{ fontSize: "var(--text-xs)" }}>
                    {g.catalog_code}
                  </Badge>
                )}
                <span className="font-medium">{g.constraint_name}</span>
              </span>
              <span className="shrink-0 font-semibold text-danger">{g.count}</span>
            </div>
            {g.first_date && (
              <p className="mt-0.5 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                {tarih(g.first_date)} – {tarih(g.last_date!)}
              </p>
            )}
            <ul className="mt-1.5">
              {(g.samples ?? []).map((s) => (
                <li key={s.id} className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {s.work_date && `${tarih(s.work_date)} · `}{s.message}
                </li>
              ))}
              {g.count > (g.samples ?? []).length && (
                <li className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  … ve {sayi(g.count - (g.samples ?? []).length)} tane daha
                </li>
              )}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
