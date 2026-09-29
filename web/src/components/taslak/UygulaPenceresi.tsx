"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { api } from "@/lib/api";
import type { Draft } from "@/lib/taslak";
import type { components } from "@/lib/api-types";

type PublishPreview = components["schemas"]["PublishPreview"];

/**
 * "Taslağı uygula" onayı. Hem taslak panelinden hem taslaklar listesindeki
 * ikondan açılıyor — akış TEK yerde dursun ki iki giriş noktası zamanla
 * birbirinden ayrılmasın.
 *
 * Uygulamadan ÖNCE ne kaybolacağını söylüyor: hangi çizelge arşive gidecek,
 * hangi kısmı yayından kalkacak, kaç elle değişiklik yok olacak.
 */
export function UygulaPenceresi({
  taslak, acik, onKapat, onBitti,
}: {
  taslak: Draft;
  acik: boolean;
  onKapat: () => void;
  onBitti?: () => void;
}) {
  const qc = useQueryClient();

  const { data: onizleme } = useQuery({
    queryKey: ["publish-preview", taslak.id],
    queryFn: () => api<PublishPreview>(`/drafts/${taslak.id}/publish-preview`),
    enabled: acik,
  });

  const uygula = useMutation({
    mutationFn: () => api<Draft>(`/drafts/${taslak.id}/publish`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["draft", taslak.id] });
      qc.invalidateQueries({ queryKey: ["drafts"] });
      qc.invalidateQueries({ queryKey: ["publish-preview"] });
      qc.invalidateQueries({ queryKey: ["schedule"] });
      onKapat();
      onBitti?.();
    },
  });

  return (
    <AlertDialog open={acik} onOpenChange={(a) => !a && onKapat()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle style={{ fontSize: "var(--text-base)" }}>
            Taslak uygulansın mı?
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div style={{ fontSize: "var(--text-xs)" }} className="grid gap-1.5">
              <p>{taslak.name} yayınlanacak ve Nöbet Çizelgesi ekranında görünecek.</p>

              {(onizleme?.archived_names ?? []).map((ad) => (
                <p key={ad}>Mevcut çizelge “{ad}” arşive alınacak.</p>
              ))}
              {onizleme?.uncovered_label && (
                <p>Eski çizelgenin {onizleme.uncovered_label} kısmı da yayından kalkacak.</p>
              )}
              {(onizleme?.manual_change_count ?? 0) > 0 && (
                <p className="text-danger">
                  Mevcut çizelgede {onizleme!.manual_change_count} elle yapılmış değişiklik
                  var; yeni çizelgede olmayacak.
                </p>
              )}
            </div>
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
  );
}
