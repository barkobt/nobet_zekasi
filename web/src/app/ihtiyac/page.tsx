"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { DonemGezgini } from "@/components/anasayfa/DonemGezgini";
import { GunKarti } from "@/components/ihtiyac/GunKarti";
import { Sablon } from "@/components/ihtiyac/Sablon";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { aralik, iso, kaydir, type Olcek } from "@/lib/donem";
import { sayi } from "@/lib/taslak";
import type { components } from "@/lib/api-types";

type Demand = components["schemas"]["Demand"];

export default function IhtiyacSayfasi() {
  return (
    <Suspense fallback={null}>
      <Icerik />
    </Suspense>
  );
}

function Icerik() {
  // Sekme adreste tutuluyor: derin bağlantı verilebilsin ve yenilemede kaybolmasın.
  const router = useRouter();
  const sekme = useSearchParams().get("sekme") === "sablon" ? "sablon" : "haftalik";
  const [olcek, setOlcek] = useState<Olcek>("hafta");
  const [capa, setCapa] = useState(() => new Date(Date.UTC(2026, 8, 21))); // 21 Eyl 2026
  const [bas, son] = aralik(capa, olcek);

  const { data, isLoading } = useQuery({
    queryKey: ["demand", iso(bas), iso(son)],
    queryFn: () => api<Demand>(`/demand?from=${iso(bas)}&to=${iso(son)}`),
  });

  return (
    <AppShell>
      <h1 className="mb-4" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
        İhtiyaç
      </h1>

      <Tabs value={sekme} onValueChange={(v) => router.replace(`/ihtiyac?sekme=${v}`)}>
        <TabsList>
          <TabsTrigger value="haftalik">Haftalık görünüm</TabsTrigger>
          <TabsTrigger value="sablon">Şablon</TabsTrigger>
        </TabsList>

        <TabsContent value="haftalik" className="mt-4">
          <div className="mb-4">
            <DonemGezgini
              etiket={data?.period_label ?? "…"}
              olcek={olcek}
              onKaydir={(yon) => setCapa((c) => kaydir(c, olcek, yon))}
              onOlcek={setOlcek}
            />
          </div>

          {data && (
            <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-1 rounded-lg border bg-card px-4 py-3">
              <Ozet etiket="Minimum kadro" deger={`${sayi(data.total.required_hours)} sa`} />
              <Ozet etiket="Atanan" deger={`${sayi(data.total.assigned_hours)} sa`} />
              <Ozet
                etiket="Eksik slot"
                deger={String(data.total.shortfall_count)}
                vurgu={data.total.shortfall_count > 0}
              />
              {data.draft?.is_reference_copy && (
                <Badge
                  variant="secondary"
                  className="h-5 rounded-sm px-1.5 font-normal"
                  style={{ fontSize: "var(--text-xs)" }}
                >
                  Referans kopya
                </Badge>
              )}
            </div>
          )}

          {isLoading ? (
            <div className="rounded-lg border bg-card p-6">
              <p className="text-muted-foreground">Yükleniyor…</p>
            </div>
          ) : !data?.days.length ? (
            <div className="rounded-lg border bg-card p-10 text-center">
              <p className="text-muted-foreground">Bu dönem için çizelge yok.</p>
            </div>
          ) : (
            <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3">
              {data.days.map((g) => <GunKarti key={g.day} gun={g} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="sablon" className="mt-4">
          <Sablon />
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}

function Ozet({ etiket, deger, vurgu }: { etiket: string; deger: string; vurgu?: boolean }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        {etiket}
      </span>
      <span className={vurgu ? "font-semibold text-danger" : "font-medium"}>{deger}</span>
    </span>
  );
}
