"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { PersonDetail } from "@/lib/personel";
import type { components } from "@/lib/api-types";

type DeleteResult = components["schemas"]["DeleteResult"];

/**
 * Ataması olan personel SİLİNMEZ, pasife alınır — geçmiş çizelgeler korunmalı
 * (veritabanı da fk_assignments_staff RESTRICT ile buna zorluyor).
 * Düğme bu yüzden duruma göre ad değiştiriyor: sessizce farklı bir şey yapmak yerine
 * ne olacağını baştan söylüyor.
 */
export function SilmeBolumu({
  kisi, onSilindi, kompakt,
}: { kisi: PersonDetail; onSilindi: () => void; kompakt?: boolean }) {
  const qc = useQueryClient();
  const silinebilir = kisi.can_delete;

  const sil = useMutation({
    mutationFn: () => api<DeleteResult>(`/people/${kisi.id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["people"] });
      onSilindi();
    },
  });

  // kompakt: başlık satırında yalnız düğme durur; ne olacağını onay penceresi anlatır.
  const govde = (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="outline" size="sm" className="text-danger hover:text-danger">
            <Trash2 size={14} strokeWidth={1.75} />
            {silinebilir ? "Sil" : "Pasife al"}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontSize: "var(--text-base)" }}>
              {silinebilir ? `${kisi.full_name} silinsin mi?` : `${kisi.full_name} pasife alınsın mı?`}
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontSize: "var(--text-xs)" }}>
              {silinebilir
                ? "Bu kişinin hiç ataması yok; kaydı tamamen silinecek. Geri alınamaz."
                : `${kisi.assignment_count} atamada geçtiği için kaydı silinemez. Pasife alınırsa ` +
                  "listelerden ve çözümden düşer, geçmiş çizelgeler olduğu gibi kalır."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Vazgeç</AlertDialogCancel>
            <AlertDialogAction onClick={() => sil.mutate()}>
              {silinebilir ? "Sil" : "Pasife al"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
  );

  if (kompakt) return govde;
  return (
    <section className="border-t pt-4">
      <p className="mb-2 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {silinebilir
          ? "Bu kişinin hiç ataması yok, kaydı tamamen silinebilir."
          : "Personel yeni taslaklarda yer almaz, geçmiş korunur."}
      </p>
      {govde}
    </section>
  );
}
