"use client";

import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type Staff = components["schemas"]["Staff"];

const CALISMA_TIPI: Record<string, string> = {
  gunduz_gece: "Gündüz + Gece",
  sadece_gunduz: "Yalnız gündüz",
  sadece_gece: "Yalnız gece",
};

/**
 * Rozet etiketleri (DESIGN §5): kısa kod rozette, tam adı tooltip'te.
 * Ham veritabanı kodları (HASTA_ILT, SHIFT_YETKILISI) arayüze çıkmaz — DESIGN §7.
 */
const ROZET: Record<string, { kisa: string; tam: string }> = {
  IV:              { kisa: "IV",    tam: "IV kateterizasyon / damar yolu" },
  IM:              { kisa: "İM",    tam: "İM enjeksiyon" },
  HASTA_ILT:       { kisa: "İLET",  tam: "Hasta iletişimi" },
  SHIFT_YETKILISI: { kisa: "LİDER", tam: "Ekip lideri (shift yetkilisi)" },
  SAYIM:           { kisa: "SAYIM", tam: "Sayım yetkisi" },
  TRIYAJ:          { kisa: "TRY",   tam: "Triyaj" },
  AMBULANS:        { kisa: "AMB",   tam: "Ambulans görevi" },
  GOZLEM:          { kisa: "GÖZ",   tam: "Gözlem alanı" },
};

export default function PersonelSayfasi() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["staff"],
    queryFn: () => api<Staff[]>("/staff"),
  });

  return (
    <AppShell>
      {/* DESIGN §4: sayfa başlığı satırı — solda başlık 20px/600 */}
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Personel</h1>
        {data && (
          <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            {data.length} kişi
          </span>
        )}
      </div>

      <div className="rounded-lg border bg-card">
        {error ? (
          // DESIGN §5: boş/hata durumu tek cümle.
          <p className="p-6 text-danger">Personel listesi alınamadı.</p>
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[220px]">Ad Soyad</TableHead>
                <TableHead className="w-[200px]">Rol</TableHead>
                <TableHead className="w-[150px]">Çalışma tipi</TableHead>
                <TableHead>Yetkinlikler</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data!.map((kisi) => (
                <TableRow key={kisi.id} className="h-10">
                  <TableCell className="font-medium">
                    {kisi.full_name}
                    {kisi.is_orientation && (
                      <span
                        className="ml-2 text-muted-foreground"
                        style={{ fontSize: "var(--text-xs)" }}
                        title={kisi.buddy_name ? `Eğitmen: ${kisi.buddy_name}` : undefined}
                      >
                        oryantasyon
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{kisi.role_name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {CALISMA_TIPI[kisi.shift_eligibility] ?? kisi.shift_eligibility}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {(kisi.competency_codes ?? []).length === 0 ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        (kisi.competency_codes ?? []).map((kod) => (
                          <Tooltip key={kod}>
                            <TooltipTrigger asChild>
                              <Badge
                                variant="secondary"
                                className="h-5 rounded-sm px-1.5 font-normal"
                                style={{ fontSize: "var(--text-xs)" }}
                              >
                                {ROZET[kod]?.kisa ?? kod}
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent>{ROZET[kod]?.tam ?? kod}</TooltipContent>
                          </Tooltip>
                        ))
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </AppShell>
  );
}
