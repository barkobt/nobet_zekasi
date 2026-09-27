"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock, Play } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import { aralikEtiketi, type Draft, type SolveAccepted } from "@/lib/taslak";
import type { components } from "@/lib/api-types";

type Constraint = components["schemas"]["Constraint"];

export default function KurallarSayfasi() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["constraints"],
    queryFn: () => api<Constraint[]>("/constraints"),
  });

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Kural Seti</h1>
        <YenidenCoz />
      </div>

      <div className="rounded-lg border bg-card">
        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} kisa />
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[70px]">Kod</TableHead>
                <TableHead className="w-[240px]">Kural</TableHead>
                <TableHead className="w-[90px]">Kapsam</TableHead>
                <TableHead className="w-[100px]">Kaynak</TableHead>
                <TableHead className="w-[130px]">Tip</TableHead>
                <TableHead className="w-[90px] text-right">Ağırlık</TableHead>
                <TableHead>Parametreler</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((k) => <Satir key={k.id} kural={k} />)}
            </TableBody>
          </Table>
        )}
      </div>

      <p className="mt-2 px-1 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        Kurallar kodda değil veritabanında; değiştirmek için yeniden dağıtım gerekmez.
        Kaynağı Yasal olanlar gevşetilemez.
      </p>
    </AppShell>
  );
}

function Satir({ kural }: { kural: Constraint }) {
  const qc = useQueryClient();
  const [agirlik, setAgirlik] = useState(String(kural.default_weight ?? ""));

  const guncelle = useMutation({
    mutationFn: (govde: Record<string, unknown>) =>
      api<Constraint>(`/constraints/${kural.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(govde),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["constraints"] });
      qc.invalidateQueries({ queryKey: ["need-templates"] });
    },
  });

  const paramGuncelle = useMutation({
    mutationFn: ({ id, deger }: { id: number; deger: number }) =>
      api<Constraint[]>(`/constraint-params/${id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ param_value: deger }),
      }),
    onSuccess: (yeni) => qc.setQueryData(["constraints"], yeni),
  });

  return (
    <TableRow className="h-10">
      <TableCell className="text-muted-foreground">{kural.catalog_code ?? ""}</TableCell>
      <TableCell>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="font-medium">{kural.name}</span>
          </TooltipTrigger>
          {kural.description && (
            <TooltipContent side="right" className="max-w-[320px]">
              {kural.description}
            </TooltipContent>
          )}
        </Tooltip>
      </TableCell>
      <TableCell className="text-muted-foreground">{kural.scope_label}</TableCell>
      <TableCell className="text-muted-foreground">
        <span className="flex items-center gap-1">
          {kural.source_label}
          {kural.locked && (
            <Lock size={16} strokeWidth={1.75} className="opacity-40" aria-label="Gevşetilemez" />
          )}
        </span>
      </TableCell>

      <TableCell>
        {kural.locked ? (
          <span className="text-muted-foreground">Zorunlu</span>
        ) : (
          <div className="flex rounded-md border p-0.5">
            {[true, false].map((hard) => (
              <button
                key={String(hard)}
                type="button"
                onClick={() =>
                  // Esneğe çevirirken ağırlık ZORUNLU: sunucu ağırlıksız isteği
                  // 422 ile reddediyor (eskiden sessizce 50 yazılıyordu).
                  guncelle.mutate(
                    hard
                      ? { is_hard: true }
                      : { is_hard: false, default_weight: kural.default_weight ?? 50 },
                  )
                }
                aria-pressed={kural.is_hard === hard}
                disabled={guncelle.isPending}
                className={
                  "rounded-sm px-2 py-0.5 transition-colors " +
                  (kural.is_hard === hard
                    ? "bg-brand text-white"
                    : "text-muted-foreground hover:text-foreground")
                }
                style={{ fontSize: "var(--text-xs)" }}
              >
                {hard ? "Zorunlu" : "Esnek"}
              </button>
            ))}
          </div>
        )}
      </TableCell>

      <TableCell className="text-right">
        {kural.is_hard ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          <Input
            type="number"
            min={1}
            max={1000}
            value={agirlik}
            onChange={(e) => setAgirlik(e.target.value)}
            onBlur={() =>
              Number(agirlik) !== kural.default_weight &&
              Number(agirlik) >= 1 &&
              guncelle.mutate({ default_weight: Number(agirlik) })
            }
            className="ml-auto h-8 w-20 text-right"
            aria-label={`${kural.name} ağırlığı`}
          />
        )}
      </TableCell>

      <TableCell>
        <div className="flex flex-wrap items-center gap-2">
          {(kural.params ?? []).length === 0 && (
            <span className="text-muted-foreground">—</span>
          )}
          {(kural.params ?? []).map((p) => (
            <Parametre
              key={p.id}
              etiket={p.description ?? p.param_key}
              deger={p.param_value}
              // Kural kilitliyse parametresi de kilitli: sunucu 403 döndürüyor,
              // arayüz de düzenlenebilir göstermemeli.
              kilitli={kural.locked}
              onKaydet={(d) => paramGuncelle.mutate({ id: p.id, deger: d })}
            />
          ))}
        </div>
      </TableCell>
    </TableRow>
  );
}

function Parametre({
  etiket, deger, kilitli, onKaydet,
}: { etiket: string; deger: number; kilitli?: boolean; onKaydet: (d: number) => void }) {
  const [v, setV] = useState(String(deger));
  if (kilitli) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="flex h-8 w-16 items-center justify-center rounded-md border bg-background text-muted-foreground">
            {deger}
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[280px]">
          {etiket} — yasal kural, değiştirilemez
        </TooltipContent>
      </Tooltip>
    );
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="flex items-center gap-1">
          <Input
            type="number"
            value={v}
            onChange={(e) => setV(e.target.value)}
            onBlur={() => Number(v) !== deger && onKaydet(Number(v))}
            className="h-8 w-16"
            aria-label={etiket}
          />
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[280px]">{etiket}</TooltipContent>
    </Tooltip>
  );
}

/** Kural değişti → hangi taslağı yeniden çözelim? (E-03 → E-08 kısayolu) */
function YenidenCoz() {
  const [acik, setAcik] = useState(false);
  const [secili, setSecili] = useState<string>("");
  const { data: taslaklar } = useQuery({
    queryKey: ["drafts"], queryFn: () => api<Draft[]>("/drafts"),
  });

  const coz = useMutation({
    mutationFn: () =>
      api<SolveAccepted>(`/drafts/${secili}/solve`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ time_limit_s: 60 }),
      }),
    onSuccess: () => setAcik(false),
  });

  const secenekler = taslaklar ?? [];

  return (
    <Dialog open={acik} onOpenChange={setAcik}>
      <DialogTrigger asChild>
        <Button>
          <Play size={16} strokeWidth={1.75} />
          Yeniden çöz
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle style={{ fontSize: "var(--text-base)" }}>Yeniden çöz</DialogTitle>
        </DialogHeader>
        <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          Değişen kurallar yalnızca yeni çalıştırmada geçerli olur; mevcut çizelgeler
          kendiliğinden güncellenmez.
        </p>
        <select
          className="h-9 w-full rounded-md border bg-card px-2"
          value={secili}
          onChange={(e) => setSecili(e.target.value)}
          aria-label="Taslak seç"
        >
          <option value="">Taslak seçin</option>
          {secenekler.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} · {aralikEtiketi(t.period_start, t.period_end)}
            </option>
          ))}
        </select>
        <DialogFooter>
          <Button variant="outline" onClick={() => setAcik(false)}>İptal</Button>
          <Button onClick={() => coz.mutate()} disabled={!secili || coz.isPending}>
            {coz.isPending ? "Başlatılıyor…" : "Çöz"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
