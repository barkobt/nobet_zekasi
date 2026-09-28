"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type Preference = components["schemas"]["Preference"];

/** Tercih anahtarı: kullanıcı başına veritabanında (localStorage DEĞİL) —
 *  sunum makinesinden ya da başka bir tarayıcıdan aynı görünüm açılsın. */
export const DETAY_ANAHTARI = "cizelge_detaylar";

export function useDetaylar() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["pref", DETAY_ANAHTARI],
    queryFn: () => api<Preference>(`/prefs/${DETAY_ANAHTARI}`),
  });
  const acik = data?.value === true;

  const yaz = useMutation({
    mutationFn: (deger: boolean) =>
      api<Preference>(`/prefs/${DETAY_ANAHTARI}`, {
        method: "PUT",
        body: JSON.stringify({ pref_key: DETAY_ANAHTARI, value: deger }),
      }),
    onSuccess: (y) => qc.setQueryData(["pref", DETAY_ANAHTARI], y),
  });

  return { acik, cevir: () => yaz.mutate(!acik), bekliyor: yaz.isPending };
}

export function DetayDugmesi() {
  const { acik, cevir, bekliyor } = useDetaylar();
  return (
    <Button variant="ghost" size="sm" onClick={cevir} disabled={bekliyor}>
      {acik ? <EyeOff size={16} strokeWidth={1.75} /> : <Eye size={16} strokeWidth={1.75} />}
      {acik ? "Detayları gizle" : "Detayları göster"}
    </Button>
  );
}
