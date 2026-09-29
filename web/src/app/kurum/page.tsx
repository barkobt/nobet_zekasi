"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, sunucuAciklamasi } from "@/lib/api";
import type { components } from "@/lib/api-types";

type Setting = components["schemas"]["Setting"];
type SettingList = components["schemas"]["SettingList"];

/**
 * E-14 Kurum — çıktılarda görünen kurum adı.
 *
 * NEDEN ayrı ekran: bu metin koda gömülü olamaz (hastane adının üründe
 * geçmemesi yasal bir gereklilik) ve "hangi sayaç görünsün" sorusuyla ilgisi
 * yok. DESIGN §1: her ekranın tek bir ana sorusu vardır.
 */
export default function KurumSayfasi() {
  const qc = useQueryClient();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api<SettingList>("/settings"),
  });

  const kurum = data?.settings.find((a) => a.key === "org_name") ?? null;

  // Sunucudan geleni EZMEDEN üstte duran taslak: kullanıcı yazmaya
  // başlamadıysa (null) her zaman sunucudaki değer görünür.
  const [taslak, setTaslak] = useState<string | null>(null);
  const deger = taslak ?? kurum?.value ?? "";
  const degisti = kurum !== null && deger !== kurum.value;

  const kaydet = useMutation({
    mutationFn: (value: string) =>
      api<Setting>("/settings/org_name", {
        method: "PUT",
        body: JSON.stringify({ value }),
      }),
    onSuccess: (yeni) => {
      qc.setQueryData<SettingList>(["settings"], (e) =>
        e ? { settings: e.settings.map((a) => (a.key === yeni.key ? yeni : a)) } : e,
      );
      setTaslak(null);
    },
  });

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Kurum</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Excel çıktılarının başlığında birim adının önünde görünen ad.
          </p>
        </div>
        <Button onClick={() => kaydet.mutate(deger)} disabled={!degisti || kaydet.isPending}>
          {kaydet.isPending ? "Kaydediliyor…" : "Kaydet"}
        </Button>
      </div>

      {kaydet.error ? (
        <div className="mb-4">
          <HataKutusu
            hata={new Error(sunucuAciklamasi(kaydet.error) ?? "Kaydedilemedi.")}
            onTekrar={() => kaydet.mutate(deger)}
            kisa
          />
        </div>
      ) : null}

      <div className="rounded-lg border bg-card p-6">
        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} kisa />
        ) : isLoading ? (
          <p className="text-muted-foreground">Yükleniyor…</p>
        ) : kurum === null ? (
          <p className="text-muted-foreground">Kurum adı ayarı bulunamadı.</p>
        ) : (
          <div className="max-w-[420px]">
            <label
              htmlFor="kurum-adi"
              className="mb-1.5 block text-muted-foreground"
              style={{ fontSize: "var(--text-xs)" }}
            >
              {kurum.label}
            </label>
            <Input
              id="kurum-adi"
              value={deger}
              maxLength={120}
              onChange={(e) => setTaslak(e.target.value)}
              placeholder="Boş bırakılabilir"
            />
            <p className="mt-2 text-sm text-muted-foreground">{kurum.description}</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
