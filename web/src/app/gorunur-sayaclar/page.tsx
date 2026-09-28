"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api, sunucuAciklamasi } from "@/lib/api";
import type { components } from "@/lib/api-types";

type Counter = components["schemas"]["Counter"];
type CounterList = components["schemas"]["CounterList"];

export default function GorunurSayaclarSayfasi() {
  const qc = useQueryClient();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["counters"],
    queryFn: () => api<CounterList>("/counters"),
  });

  // Yerel taslak: kullanıcı birkaç anahtarı çevirip bir kez kaydeder.
  const [taslak, setTaslak] = useState<Counter[] | null>(null);
  useEffect(() => {
    if (data) setTaslak(data.counters);
  }, [data]);

  const kaydet = useMutation({
    mutationFn: (liste: Counter[]) =>
      api<CounterList>("/counters", {
        method: "PUT",
        body: JSON.stringify(
          liste
            .filter((c) => !c.always_shown)
            .map((c) => ({ key: c.key, weekly_on: c.weekly_on, monthly_on: c.monthly_on })),
        ),
      }),
    onSuccess: (yeni) => {
      qc.setQueryData(["counters"], yeni);
      // Izgara sayaçları bu ayardan besleniyor: kaydedince yenilensin.
      qc.invalidateQueries({ queryKey: ["schedule"] });
      setTaslak(yeni.counters);
    },
  });

  const degisti =
    taslak !== null &&
    data !== undefined &&
    taslak.some((c, i) => {
      const o = data.counters[i];
      return c.weekly_on !== o.weekly_on || c.monthly_on !== o.monthly_on;
    });

  function cevir(key: string, alan: "weekly_on" | "monthly_on", deger: boolean) {
    setTaslak((eski) =>
      (eski ?? []).map((c) => (c.key === key ? { ...c, [alan]: deger } : c)),
    );
  }

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Görünür sayaçlar</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Çizelgede satır özetinde hangi sayaçların görüneceğini seçin. Haftalık ve
            aylık görünüm ayrı ayarlanır.
          </p>
        </div>
        <Button
          onClick={() => taslak && kaydet.mutate(taslak)}
          disabled={!degisti || kaydet.isPending}
        >
          {kaydet.isPending ? "Kaydediliyor…" : "Kaydet"}
        </Button>
      </div>

      {kaydet.error ? (
        <div className="mb-4">
          <HataKutusu
            hata={new Error(sunucuAciklamasi(kaydet.error) ?? "Kaydedilemedi.")}
            onTekrar={() => taslak && kaydet.mutate(taslak)}
            kisa
          />
        </div>
      ) : null}

      <div className="rounded-lg border bg-card">
        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} kisa />
        ) : isLoading || taslak === null ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[110px]">Haftalık</TableHead>
                <TableHead className="w-[110px]">Aylık</TableHead>
                <TableHead className="w-[80px]">Kod</TableHead>
                <TableHead className="w-[260px]">Sayaç</TableHead>
                <TableHead>Açıklama</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {taslak.map((c) => (
                <TableRow key={c.key}>
                  <TableCell>
                    <Anahtar
                      acik={c.weekly_on}
                      kilitli={c.always_shown}
                      etiket={`${c.label} — haftalık görünüm`}
                      onDegis={(v) => cevir(c.key, "weekly_on", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <Anahtar
                      acik={c.monthly_on}
                      kilitli={c.always_shown}
                      etiket={`${c.label} — aylık görünüm`}
                      onDegis={(v) => cevir(c.key, "monthly_on", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <span
                      className="inline-flex h-5 items-center rounded px-1.5 text-xs"
                      style={{ background: "var(--brand-soft)", color: "var(--brand)" }}
                    >
                      {c.badge}
                    </span>
                  </TableCell>
                  <TableCell style={{ fontWeight: 500 }}>{c.label}</TableCell>
                  <TableCell className="text-muted-foreground">{c.description}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <p className="mt-3 text-sm text-muted-foreground">
        G, N ve S her zaman görünür, kapatılamaz. Diğer sayaçlar çizelgede
        &quot;Detayları göster&quot; açıkken görünür.
      </p>
    </AppShell>
  );
}

function Anahtar({
  acik, kilitli, etiket, onDegis,
}: {
  acik: boolean;
  kilitli: boolean;
  etiket: string;
  onDegis: (deger: boolean) => void;
}) {
  if (kilitli) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
            <Lock size={14} aria-hidden />
            Açık
          </span>
        </TooltipTrigger>
        <TooltipContent>Bu sayaç her zaman görünür, kapatılamaz.</TooltipContent>
      </Tooltip>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <Switch checked={acik} onCheckedChange={onDegis} aria-label={etiket} />
      <span className="text-sm text-muted-foreground">{acik ? "Açık" : "Kapalı"}</span>
    </div>
  );
}
