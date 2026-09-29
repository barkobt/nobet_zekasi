"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { HataKutusu } from "@/components/HataKutusu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api, sunucuAciklamasi } from "@/lib/api";
import type { components } from "@/lib/api-types";

type ShiftType = components["schemas"]["ShiftType"];

/**
 * E-01: vardiya listesi. Tek düzenlenebilir alan MOLA.
 *
 * NEDEN mola burada: molalar mesaiye dahil değil (migration 023) ve süreleri
 * kuruma göre değişir. Koda gömülü olsaydı her değişiklik yeni dağıtım
 * demekti — "hardcode yok" ilkesi. Saat aralığının kendisi düzenlenebilir
 * değil: vardiya saatini değiştirmek çizelgeyi ve dinlenme kurallarını
 * etkiler, o ayrı bir iş.
 */
export default function VardiyalarSayfasi() {
  const qc = useQueryClient();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["shift-types"],
    queryFn: () => api<ShiftType[]>("/shift-types"),
  });

  // Kullanıcının yazdığı değer sunucudan geleni EZMEDEN üstte durur.
  const [ortu, setOrtu] = useState<Record<number, string>>({});

  const kaydet = useMutation({
    mutationFn: ({ id, dakika }: { id: number; dakika: number }) =>
      api<ShiftType[]>(`/shift-types/${id}/break`, {
        method: "PUT",
        body: JSON.stringify({ break_minutes: dakika }),
      }),
    onSuccess: (yeni, { id }) => {
      qc.setQueryData(["shift-types"], yeni);
      // Kaydedilen satırın örtüsü kalkar: bundan sonra sunucudaki değer görünür.
      setOrtu((e) => Object.fromEntries(
        Object.entries(e).filter(([k]) => Number(k) !== id),
      ));
      // Saat sayaçları, adalet farkı ve raporlar net süreden besleniyor.
      qc.invalidateQueries({ queryKey: ["schedule"] });
      qc.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

  return (
    <AppShell>
      <h1 className="mb-1" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
        Vardiya Tanımları
      </h1>
      <p className="mb-4 text-sm text-muted-foreground">
        Molalar mesaiye dahil değildir. Aylık 200 saat hedefi, haftalık referans,
        adalet farkı ve raporlar net süreyle ölçülür.
      </p>

      {kaydet.error ? (
        <div className="mb-4">
          <HataKutusu
            hata={new Error(sunucuAciklamasi(kaydet.error) ?? "Kaydedilemedi.")}
            onTekrar={() => kaydet.reset()}
            kisa
          />
        </div>
      ) : null}

      <div className="rounded-lg border bg-card">
        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} kisa />
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[120px]">Kod</TableHead>
                <TableHead className="w-[240px]">Ad</TableHead>
                <TableHead className="w-[140px]">Saat</TableHead>
                <TableHead className="w-[90px] text-right">Brüt</TableHead>
                <TableHead className="w-[180px]">Mola (dk)</TableHead>
                <TableHead className="w-[110px] text-right">Net</TableHead>
                <TableHead className="w-[130px]">Ertesi güne taşar</TableHead>
                <TableHead>Durum</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((v) => {
                const yazilan = ortu[v.id];
                const deger = yazilan ?? String(v.break_minutes);
                const sayi = Number(deger);
                const gecerli = deger !== "" && Number.isInteger(sayi) && sayi >= 0;
                const degisti = gecerli && sayi !== v.break_minutes;

                return (
                  <TableRow key={v.id} className="h-12">
                    <TableCell className="text-muted-foreground">{v.code}</TableCell>
                    <TableCell className="font-medium">{v.name}</TableCell>
                    <TableCell>
                      {v.start_time.slice(0, 5)} – {v.end_label}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {v.duration_hours} sa
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Input
                          value={deger}
                          inputMode="numeric"
                          aria-label={`${v.name} molası, dakika`}
                          className="h-8 w-[76px]"
                          onChange={(e) =>
                            setOrtu((o) => ({ ...o, [v.id]: e.target.value.replace(/\D/g, "") }))
                          }
                        />
                        {degisti && (
                          <Button
                            size="sm"
                            className="h-8"
                            disabled={kaydet.isPending}
                            onClick={() => kaydet.mutate({ id: v.id, dakika: sayi })}
                          >
                            Kaydet
                          </Button>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-medium">{v.net_label}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {v.crosses_midnight ? "Evet" : ""}
                    </TableCell>
                    <TableCell>
                      {!v.is_active && (
                        <Badge
                          variant="secondary"
                          className="h-5 rounded-sm px-1.5 font-normal"
                          style={{ fontSize: "var(--text-xs)" }}
                        >
                          Kullanılmıyor
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      <p className="mt-2 px-1 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        Bitiş saati brüt süreden gelir: mola vardiyanın içinde geçer, çıkış saati
        değişmez. 24 saatlik vardiyalar tanımlı ama kullanılmıyor (C-018).
      </p>
    </AppShell>
  );
}
