"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { ExcelDugmesi } from "@/components/ExcelDugmesi";
import { HataKutusu } from "@/components/HataKutusu";
import { YazdirDugmesi } from "@/components/rapor/YazdirDugmesi";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import type { Draft } from "@/lib/taslak";

type Kisi = {
  staff_id: number; full_name: string; role_name: string;
  total_hours: number; night_count: number; weekend_count: number;
  target_hours: number | null; diff_hours: number | null;
  gross_hours: number; overtime_hours: number;
};
type Eksik = {
  day: string; shift_name: string; slot_name: string;
  assigned: number; required: number; missing: number;
};
type Rapor = {
  draft_id: number; draft_name: string; unit_name: string; status: string;
  period_label: string; target_note: string | null;
  people: Kisi[]; shortfalls: Eksik[];
};

const sayi = (n: number) => n.toLocaleString("tr-TR", { maximumFractionDigits: 1 });
const AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
const tarih = (iso: string) => {
  const d = new Date(iso);
  return `${d.getDate()} ${AY[d.getMonth()]} ${d.getFullYear()}`;
};

/** Tıklanabilir başlık. Varsayılan yön sayısal kolonlarda azalan. */
function Basligi<T>({
  alan, etiket, sirala, sag,
}: {
  alan: keyof T; etiket: string;
  sirala: { alan: keyof T; artan: boolean; degistir: (a: keyof T) => void };
  sag?: boolean;
}) {
  const aktif = sirala.alan === alan;
  return (
    <TableHead className={sag ? "text-right" : undefined}>
      <button
        onClick={() => sirala.degistir(alan)}
        className={
          "inline-flex items-center gap-1 hover:text-foreground " +
          (aktif ? "text-foreground" : "")
        }
      >
        {etiket}
        {aktif &&
          (sirala.artan
            ? <ArrowUp size={12} strokeWidth={1.75} />
            : <ArrowDown size={12} strokeWidth={1.75} />)}
      </button>
    </TableHead>
  );
}

function useSirala<T>(varsayilan: keyof T) {
  const [alan, setAlan] = useState<keyof T>(varsayilan);
  const [artan, setArtan] = useState(true);
  const degistir = (a: keyof T) => {
    if (a === alan) setArtan((v) => !v);
    else { setAlan(a); setArtan(typeof a === "string" && a.includes("name")); }
  };
  const uygula = (satirlar: T[]) =>
    [...satirlar].sort((a, b) => {
      const x = a[alan], y = b[alan];
      if (x === y) return 0;
      if (x === null) return 1;
      if (y === null) return -1;
      const k = typeof x === "string"
        ? (x as string).localeCompare(y as string, "tr")
        : Number(x) - Number(y);
      return artan ? k : -k;
    });
  return { alan, artan, degistir, uygula };
}

export default function RaporlarSayfasi() {
  const [secim, setSecim] = useState<number | null>(null);

  const taslaklar = useQuery({
    queryKey: ["drafts"], queryFn: () => api<Draft[]>("/drafts"),
  });

  // Varsayılan yayındaki çizelge; effect'le state kurmak yerine türetiyoruz.
  const seciliId =
    secim ??
    (taslaklar.data?.find((t) => t.status === "yayinlandi") ?? taslaklar.data?.[0])?.id ??
    null;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["report", seciliId],
    queryFn: () => api<Rapor>(`/drafts/${seciliId}/report`),
    enabled: seciliId !== null,
  });

  const kisiSirala = useSirala<Kisi>("full_name");
  const eksikSirala = useSirala<Eksik>("day");
  const kisiler = useMemo(
    () => (data ? kisiSirala.uygula(data.people) : []),
    [data, kisiSirala.alan, kisiSirala.artan], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const eksikler = useMemo(
    () => (data ? eksikSirala.uygula(data.shortfalls) : []),
    [data, eksikSirala.alan, eksikSirala.artan], // eslint-disable-line react-hooks/exhaustive-deps
  );

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Raporlar</h1>
        <Select
          value={seciliId ? String(seciliId) : undefined}
          onValueChange={(v) => setSecim(Number(v))}
        >
          <SelectTrigger className="w-[360px] yazdirma-gizle">
            <SelectValue placeholder="Taslak seçin" />
          </SelectTrigger>
          <SelectContent>
            {(taslaklar.data ?? []).map((t) => (
              <SelectItem key={t.id} value={String(t.id)}>
                {t.name}
                {t.status === "yayinlandi" ? " · Yayında" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error ? (
        <HataKutusu hata={error} onTekrar={() => refetch()} />
      ) : isLoading || !data ? (
        <p className="text-muted-foreground">Yükleniyor…</p>
      ) : (
        <div className="space-y-6">
          {/* --- Bölüm 1: Kişi özeti ------------------------------------- */}
          <section data-bolum="kisi" className="rounded-lg border bg-card">
            <header className="flex items-center justify-between gap-4 border-b px-4 py-3">
              <div>
                <h2 style={{ fontWeight: 600 }}>Kişi özeti</h2>
                <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {data.period_label}
                  {data.target_note ? ` · ${data.target_note}` : ""}
                </p>
              </div>
              <div className="flex gap-2 yazdirma-gizle">
                <ExcelDugmesi
                  draftId={data.draft_id} dosya="export-ozet.xlsx"
                  etiket="Excel" boyut="sm"
                />
                <YazdirDugmesi bolum="kisi" />
              </div>
            </header>

            <Table>
              <TableHeader>
                <TableRow>
                  <Basligi<Kisi> alan="full_name" etiket="Personel" sirala={kisiSirala} />
                  <Basligi<Kisi> alan="role_name" etiket="Rol" sirala={kisiSirala} />
                  <Basligi<Kisi> alan="total_hours" etiket="Toplam saat" sirala={kisiSirala} sag />
                  <Basligi<Kisi> alan="night_count" etiket="Gece" sirala={kisiSirala} sag />
                  <Basligi<Kisi> alan="weekend_count" etiket="Hafta sonu" sirala={kisiSirala} sag />
                  <Basligi<Kisi> alan="target_hours" etiket="Hedef" sirala={kisiSirala} sag />
                  <Basligi<Kisi> alan="diff_hours" etiket="Fark" sirala={kisiSirala} sag />
                  <Basligi<Kisi> alan="gross_hours" etiket="Brüt saat" sirala={kisiSirala} sag />
                  <Basligi<Kisi> alan="overtime_hours" etiket="Mesai" sirala={kisiSirala} sag />
                </TableRow>
              </TableHeader>
              <TableBody>
                {kisiler.map((k) => (
                  <TableRow key={k.staff_id}>
                    <TableCell className="font-medium">{k.full_name}</TableCell>
                    <TableCell className="text-muted-foreground">{k.role_name}</TableCell>
                    <TableCell className="text-right">{sayi(k.total_hours)}</TableCell>
                    <TableCell className="text-right">{k.night_count}</TableCell>
                    <TableCell className="text-right">{k.weekend_count}</TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {k.target_hours === null ? "—" : sayi(k.target_hours)}
                    </TableCell>
                    <TableCell
                      className={
                        "text-right " +
                        (k.diff_hours !== null && k.diff_hours < 0 ? "text-danger font-medium" : "")
                      }
                    >
                      {k.diff_hours === null
                        ? "—"
                        : `${k.diff_hours > 0 ? "+" : ""}${sayi(k.diff_hours)}`}
                    </TableCell>
                    {/* Brüt = molalar dahil; mesai = haftalık brüt 51 sa üstü (O-001) */}
                    <TableCell className="text-right text-muted-foreground">
                      {sayi(k.gross_hours ?? 0)}
                    </TableCell>
                    <TableCell className="text-right">{sayi(k.overtime_hours ?? 0)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>

          {/* --- Bölüm 2: Eksikler --------------------------------------- */}
          <section data-bolum="eksik" className="rounded-lg border bg-card">
            <header className="flex items-center justify-between gap-4 border-b px-4 py-3">
              <div>
                <h2 style={{ fontWeight: 600 }}>Eksikler</h2>
                <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {data.period_label}
                </p>
              </div>
              <div className="flex gap-2 yazdirma-gizle">
                <ExcelDugmesi
                  draftId={data.draft_id} dosya="export-eksikler.xlsx"
                  etiket="Excel" boyut="sm"
                />
                <YazdirDugmesi bolum="eksik" />
              </div>
            </header>

            {eksikler.length === 0 ? (
              <p className="px-4 py-6 text-muted-foreground">Bu dönemde eksik yok.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <Basligi<Eksik> alan="day" etiket="Gün" sirala={eksikSirala} />
                    <Basligi<Eksik> alan="shift_name" etiket="Vardiya" sirala={eksikSirala} />
                    <Basligi<Eksik> alan="slot_name" etiket="Görev" sirala={eksikSirala} />
                    <Basligi<Eksik> alan="assigned" etiket="Atanan" sirala={eksikSirala} sag />
                    <Basligi<Eksik> alan="required" etiket="Gereken" sirala={eksikSirala} sag />
                    <Basligi<Eksik> alan="missing" etiket="Eksik" sirala={eksikSirala} sag />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {eksikler.map((e, i) => (
                    <TableRow key={`${e.day}-${e.shift_name}-${e.slot_name}-${i}`}>
                      <TableCell>{tarih(e.day)}</TableCell>
                      <TableCell>{e.shift_name}</TableCell>
                      <TableCell className="text-muted-foreground">{e.slot_name}</TableCell>
                      <TableCell className="text-right">{e.assigned}</TableCell>
                      <TableCell className="text-right">{e.required}</TableCell>
                      <TableCell className="text-right font-medium text-danger">
                        {e.missing}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
