"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Lock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type NeedTemplate = components["schemas"]["NeedTemplate"];
type TemplateRow = components["schemas"]["TemplateRow"];

/** E-06 ikinci sekmesi: vardiya × görev, min kişi sayısı düzenlenebilir. */
export function Sablon() {
  const { data, isLoading } = useQuery({
    queryKey: ["need-templates"],
    queryFn: () => api<NeedTemplate[]>("/need-templates"),
  });

  if (isLoading) return <p className="p-6 text-muted-foreground">Yükleniyor…</p>;
  if (!data?.length) return <p className="p-6 text-muted-foreground">Şablon yok.</p>;

  return (
    <div className="space-y-4">
      {data.map((nt) => (
        <div key={nt.id} className="rounded-lg border bg-card">
          <div className="border-b px-4 py-3">
            <span className="font-medium">{nt.name}</span>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[120px]">Vardiya</TableHead>
                <TableHead className="w-[160px]">Görev</TableHead>
                <TableHead className="w-[110px]">En az kişi</TableHead>
                <TableHead>Bağlı kural</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {nt.rows.map((r) => <Satir key={r.id} satir={r} />)}
            </TableBody>
          </Table>
        </div>
      ))}
    </div>
  );
}

function Satir({ satir }: { satir: TemplateRow }) {
  const [deger, setDeger] = useState(String(satir.min_count));
  const qc = useQueryClient();

  const kaydet = useMutation({
    mutationFn: () =>
      api<TemplateRow>(`/need-template-rows/${satir.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ min_count: Number(deger) }),
      }),
    onSuccess: () => {
      // Şablon değişince kapsama sayıları da değişir; ikisini birden tazele.
      qc.invalidateQueries({ queryKey: ["need-templates"] });
      qc.invalidateQueries({ queryKey: ["demand"] });
      qc.invalidateQueries({ queryKey: ["schedule"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  const degisti = deger !== String(satir.min_count);
  const gecerli = Number(deger) >= 1 && Number(deger) <= 50;

  return (
    <TableRow className="h-10">
      <TableCell className="text-muted-foreground">{satir.shift_name}</TableCell>
      <TableCell className="font-medium">{satir.slot_label}</TableCell>
      <TableCell>
        <div className="flex items-center gap-1.5">
          <Input
            type="number"
            min={1}
            max={50}
            value={deger}
            onChange={(e) => setDeger(e.target.value)}
            className="h-8 w-16"
            aria-label={`${satir.shift_name} ${satir.slot_label} en az kişi`}
          />
          {degisti && (
            <Button
              size="sm"
              onClick={() => kaydet.mutate()}
              disabled={!gecerli || kaydet.isPending}
            >
              {kaydet.isPending ? "…" : "Kaydet"}
            </Button>
          )}
          {!degisti && kaydet.isSuccess && (
            <Check size={16} strokeWidth={1.75} className="text-muted-foreground" />
          )}
        </div>
      </TableCell>
      <TableCell>
        {satir.constraint_name ? (
          <span className="flex items-center gap-1.5">
            {satir.catalog_code && (
              <Badge
                variant="secondary"
                className="h-5 rounded-sm px-1.5 font-normal"
                style={{ fontSize: "var(--text-xs)" }}
              >
                {satir.catalog_code}
              </Badge>
            )}
            <span className="text-muted-foreground">{satir.constraint_name}</span>
            {satir.is_hard && (
              <Lock size={16} strokeWidth={1.75} className="opacity-40" aria-label="Zorunlu kural" />
            )}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </TableCell>
    </TableRow>
  );
}
