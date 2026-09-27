"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { YeniTaslak } from "@/components/taslak/YeniTaslak";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { aralikEtiketi, type Draft } from "@/lib/taslak";

/** Durum rozeti: taslağın gerçekte ne olduğunu tek kelimeyle söyler. */
function durumRozeti(t: Draft): { ad: string; vurgu?: boolean } {
  if (t.status === "yayinlandi") return { ad: "Yayınlandı" };
  if (t.status === "arsiv") return { ad: "Arşiv" };
  if (t.last_run?.is_reference_copy) return { ad: "Referans kopya" };
  if (t.last_run?.status === "INFEASIBLE") return { ad: "Çözülemedi", vurgu: true };
  if (t.last_run) return { ad: "Çözüldü" };
  return { ad: "Taslak" };
}

export default function TaslaklarSayfasi() {
  const router = useRouter();
  const qc = useQueryClient();
  const [silinecek, setSilinecek] = useState<Draft | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["drafts"], queryFn: () => api<Draft[]>("/drafts"),
  });

  const sil = useMutation({
    mutationFn: (id: number) => api<void>(`/drafts/${id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["drafts"] }); setSilinecek(null); },
  });

  const kopyala = useMutation({
    mutationFn: (t: Draft) =>
      api<Draft>(`/drafts/${t.id}/copy`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ name: `${t.name} (kopya)` }),
      }),
    onSuccess: (yeni) => {
      qc.invalidateQueries({ queryKey: ["drafts"] });
      router.push(`/taslaklar/${yeni.id}`);
    },
  });

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Taslaklar</h1>
        <YeniTaslak />
      </div>

      <div className="rounded-lg border bg-card">
        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} kisa />
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : !data?.length ? (
          <div className="flex flex-col items-center gap-3 p-10">
            <p className="text-muted-foreground">Henüz taslak yok.</p>
            <YeniTaslak />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[320px]">Taslak</TableHead>
                <TableHead className="w-[220px]">Dönem</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead className="w-[60px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((t) => {
                const rozet = durumRozeti(t);
                return (
                  <TableRow
                    key={t.id}
                    className="h-11 cursor-pointer"
                    onClick={() => router.push(`/taslaklar/${t.id}`)}
                    tabIndex={0}
                    onKeyDown={(e) => e.key === "Enter" && router.push(`/taslaklar/${t.id}`)}
                  >
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
                        className={"h-5 rounded-sm px-1.5 font-normal " + (rozet.vurgu ? "text-danger" : "")}
                        style={{ fontSize: "var(--text-xs)" }}
                      >
                        {rozet.ad}
                      </Badge>
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" aria-label="Taslak işlemleri">
                            <MoreHorizontal size={16} strokeWidth={1.75} />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => kopyala.mutate(t)}>
                            Kopyala
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSilinecek(t)}>
                            Sil
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      <AlertDialog open={silinecek !== null} onOpenChange={(a) => !a && setSilinecek(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontSize: "var(--text-base)" }}>
              {silinecek?.name} silinsin mi?
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontSize: "var(--text-xs)" }}>
              Taslağın {silinecek?.assignment_count} ataması ve çalıştırma geçmişi de
              silinecek. Geri alınamaz.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Vazgeç</AlertDialogCancel>
            <AlertDialogAction onClick={() => silinecek && sil.mutate(silinecek.id)}>
              Sil
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
