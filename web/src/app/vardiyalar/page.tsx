"use client";

import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type ShiftType = components["schemas"]["ShiftType"];

/** E-01: salt okunur liste (MVP kapsamı). */
export default function VardiyalarSayfasi() {
  const { data, isLoading } = useQuery({
    queryKey: ["shift-types"],
    queryFn: () => api<ShiftType[]>("/shift-types"),
  });

  return (
    <AppShell>
      <h1 className="mb-4" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
        Vardiya Tanımları
      </h1>

      <div className="rounded-lg border bg-card">
        {isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[130px]">Kod</TableHead>
                <TableHead className="w-[260px]">Ad</TableHead>
                <TableHead className="w-[140px]">Saat</TableHead>
                <TableHead className="w-[100px] text-right">Süre</TableHead>
                <TableHead className="w-[150px]">Ertesi güne taşar</TableHead>
                <TableHead>Durum</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((v) => (
                <TableRow key={v.id} className="h-10">
                  <TableCell className="text-muted-foreground">{v.code}</TableCell>
                  <TableCell className="font-medium">{v.name}</TableCell>
                  <TableCell>
                    {v.start_time.slice(0, 5)} – {v.end_label}
                  </TableCell>
                  <TableCell className="text-right">{v.duration_hours} sa</TableCell>
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
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <p className="mt-2 px-1 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        24 saatlik vardiyalar tanımlı ama kullanılmıyor (C-018). Açılmaları için
        şablonda yer almaları gerekir.
      </p>
    </AppShell>
  );
}
