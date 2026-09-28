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
export const OZET_ANAHTARI = "cizelge_ozet_paneli";

/** Veritabanında duran açık/kapalı tercihi (localStorage DEĞİL). */
function useTercih(anahtar: string) {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["pref", anahtar],
    queryFn: () => api<Preference>(`/prefs/${anahtar}`),
  });
  const acik = data?.value === true;

  const yaz = useMutation({
    mutationFn: (deger: boolean) =>
      api<Preference>(`/prefs/${anahtar}`, {
        method: "PUT",
        body: JSON.stringify({ pref_key: anahtar, value: deger }),
      }),
    onSuccess: (y) => qc.setQueryData(["pref", anahtar], y),
  });

  return { acik, cevir: () => yaz.mutate(!acik), bekliyor: yaz.isPending };
}

export const useDetaylar = () => useTercih(DETAY_ANAHTARI);
export const useOzetPaneli = () => useTercih(OZET_ANAHTARI);

export function DetayDugmesi() {
  const { acik, cevir, bekliyor } = useDetaylar();
  return (
    <Button variant="ghost" size="sm" onClick={cevir} disabled={bekliyor}>
      {acik ? <EyeOff size={16} strokeWidth={1.75} /> : <Eye size={16} strokeWidth={1.75} />}
      {acik ? "Detayları gizle" : "Detayları göster"}
    </Button>
  );
}
