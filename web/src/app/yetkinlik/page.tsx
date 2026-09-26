"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronDown, ChevronRight, Pencil } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type Matrix = components["schemas"]["CompetencyMatrix"];
type Competency = components["schemas"]["Competency"];
type Row = components["schemas"]["MatrixRow"];

const KISA: Record<string, string> = {
  IV: "IV", IM: "İM", HASTA_ILT: "İLET", SHIFT_YETKILISI: "LİDER", SAYIM: "SAYIM",
  TRIYAJ: "TRY", AMBULANS: "AMB", GOZLEM: "GÖZ",
};

/** Çizelgedeki gruplamanın aynısı — iki ekran aynı zihinsel düzeni paylaşsın. */
const GRUPLAR: { ad: string; roller: string[] | null }[] = [
  { ad: "Sorumlu & Eğitim", roller: ["Sorumlu Hemşire", "Eğitim Hemşiresi"] },
  { ad: "Ekip Liderleri", roller: ["Ekip Lideri (Shift Yetkilisi)"] },
  { ad: "Hemşireler", roller: null },
];

export default function YetkinlikSayfasi() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["competency-matrix"],
    queryFn: () => api<Matrix>("/competency-matrix"),
  });

  const [duzenle, setDuzenle] = useState(false);
  const [taslak, setTaslak] = useState<Map<number, Set<string>>>(new Map());
  const [kapali, setKapali] = useState<Set<string>>(new Set());
  const [uyari, setUyari] = useState(false);
  const [vurgu, setVurgu] = useState<{ satir: number | null; sutun: string | null }>({
    satir: null, sutun: null,
  });

  const kaydet = useMutation({
    mutationFn: async () => {
      // Değişen her kutucuk için tek tek istek: 20×8 matriste en fazla birkaç tanesi
      // değişir, toplu uç açmaya değmez.
      for (const [staffId, kodlar] of taslak) {
        const eski = new Set(data!.rows.find((r) => r.staff_id === staffId)?.codes ?? []);
        for (const c of [...data!.tasks, ...data!.qualifications]) {
          const yeniVar = kodlar.has(c.code);
          if (yeniVar !== eski.has(c.code)) {
            await api<Matrix>(`/people/${staffId}/competencies/${c.code}?ver=${yeniVar}`, {
              method: "PUT",
            });
          }
        }
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["competency-matrix"] });
      setDuzenle(false);
      setTaslak(new Map());
    },
  });

  const sutunlar = useMemo(
    () => [...(data?.tasks ?? []), ...(data?.qualifications ?? [])],
    [data],
  );

  const degisiklikVar = useMemo(() => {
    if (!data) return false;
    for (const [staffId, kodlar] of taslak) {
      const eski = new Set(data.rows.find((r) => r.staff_id === staffId)?.codes ?? []);
      if (kodlar.size !== eski.size) return true;
      for (const k of kodlar) if (!eski.has(k)) return true;
    }
    return false;
  }, [data, taslak]);

  if (!data) {
    return (
      <AppShell>
        <Baslik />
        <div className="rounded-lg border bg-card p-6">
          <p className="text-muted-foreground">Yükleniyor…</p>
        </div>
      </AppShell>
    );
  }

  const varMi = (r: Row, kod: string) =>
    (taslak.get(r.staff_id) ?? new Set(r.codes ?? [])).has(kod);

  const degistir = (r: Row, kod: string) => {
    setTaslak((m) => {
      const y = new Map(m);
      const mevcut = new Set(y.get(r.staff_id) ?? r.codes ?? []);
      mevcut.has(kod) ? mevcut.delete(kod) : mevcut.add(kod);
      y.set(r.staff_id, mevcut);
      return y;
    });
  };

  // Düzenleme modunda sütun toplamı taslağa göre sayılır: değişiklik anında görünsün.
  const toplam = (c: Competency) =>
    data.rows.filter((r) => varMi(r, c.code)).length;

  const gruplar = GRUPLAR.map((g, i) => ({
    ...g,
    satirlar: data.rows.filter((r) =>
      g.roller ? g.roller.includes(r.role_name)
               : !GRUPLAR.slice(0, i).some((o) => o.roller?.includes(r.role_name)),
    ),
  })).filter((g) => g.satirlar.length > 0);

  const cikmayiDene = () => (degisiklikVar ? setUyari(true) : setDuzenle(false));

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Yetkinlik Matrisi</h1>
        {duzenle ? (
          <div className="flex gap-2">
            <Button variant="outline" onClick={cikmayiDene}>Vazgeç</Button>
            <Button onClick={() => kaydet.mutate()} disabled={!degisiklikVar || kaydet.isPending}>
              {kaydet.isPending ? "Kaydediliyor…" : "Kaydet"}
            </Button>
          </div>
        ) : (
          <Button onClick={() => setDuzenle(true)}>
            <Pencil size={16} strokeWidth={1.75} />
            Düzenle
          </Button>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full border-collapse" style={{ fontSize: "var(--text-base)" }}>
          <thead>
            <tr>
              <th rowSpan={2} className="sticky left-0 z-20 w-[220px] min-w-[220px] border-b border-r bg-card p-0 text-left align-bottom">
                <span className="block px-3 pb-2 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  Personel
                </span>
              </th>
              <th colSpan={data.tasks.length}
                  className="border-b bg-background px-2 py-1.5 text-muted-foreground"
                  style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}>
                GÖREV
              </th>
              <th colSpan={data.qualifications.length}
                  className="border-b border-l bg-background px-2 py-1.5 text-muted-foreground"
                  style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}>
                YETKİ
              </th>
            </tr>
            <tr>
              {sutunlar.map((c, i) => (
                <th
                  key={c.code}
                  onMouseEnter={() => setVurgu((v) => ({ ...v, sutun: c.code }))}
                  onMouseLeave={() => setVurgu((v) => ({ ...v, sutun: null }))}
                  className={
                    "w-[74px] border-b bg-card px-1 py-2 font-medium " +
                    (i === data.tasks.length ? "border-l " : "") +
                    (vurgu.sutun === c.code ? "bg-accent" : "")
                  }
                  style={{ fontSize: "var(--text-xs)" }}
                >
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="cursor-default">{KISA[c.code] ?? c.code}</span>
                    </TooltipTrigger>
                    <TooltipContent>{c.name}</TooltipContent>
                  </Tooltip>
                </th>
              ))}
            </tr>
          </thead>

          {gruplar.map((grup) => {
            const acik = !kapali.has(grup.ad);
            return (
              <tbody key={grup.ad}>
                <tr>
                  <th colSpan={sutunlar.length + 1}
                      className="sticky left-0 z-10 border-b bg-background p-0 text-left">
                    <button
                      type="button"
                      onClick={() =>
                        setKapali((v) => {
                          const y = new Set(v);
                          y.has(grup.ad) ? y.delete(grup.ad) : y.add(grup.ad);
                          return y;
                        })
                      }
                      aria-expanded={acik}
                      className="flex h-9 w-full items-center gap-1.5 px-3 text-muted-foreground hover:text-foreground"
                      style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
                    >
                      {acik ? <ChevronDown size={16} strokeWidth={1.75} />
                            : <ChevronRight size={16} strokeWidth={1.75} />}
                      <span className="uppercase">{grup.ad}</span>
                      <span className="normal-case">({grup.satirlar.length})</span>
                    </button>
                  </th>
                </tr>

                {acik && grup.satirlar.map((r) => (
                  <tr
                    key={r.staff_id}
                    onMouseEnter={() => setVurgu((v) => ({ ...v, satir: r.staff_id }))}
                    onMouseLeave={() => setVurgu((v) => ({ ...v, satir: null }))}
                    className={"border-b last:border-0 " + (vurgu.satir === r.staff_id ? "bg-accent" : "")}
                  >
                    <th className={
                      "sticky left-0 z-10 border-r p-0 text-left font-normal " +
                      (vurgu.satir === r.staff_id ? "bg-accent" : "bg-card")
                    }>
                      <div className="flex h-10 items-center gap-2 px-3">
                        <span className="truncate font-medium">{r.full_name}</span>
                        {r.is_orientation && (
                          <span className="shrink-0 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                            ory.
                          </span>
                        )}
                      </div>
                    </th>

                    {sutunlar.map((c, i) => {
                      const var_ = varMi(r, c.code);
                      const kesisim = vurgu.satir === r.staff_id || vurgu.sutun === c.code;
                      return (
                        <td
                          key={c.code}
                          onMouseEnter={() => setVurgu({ satir: r.staff_id, sutun: c.code })}
                          className={
                            "h-10 text-center " + (i === data.tasks.length ? "border-l " : "") +
                            (kesisim ? "bg-accent" : "")
                          }
                        >
                          {duzenle ? (
                            <input
                              type="checkbox"
                              checked={var_}
                              onChange={() => degistir(r, c.code)}
                              className="size-4 accent-brand"
                              aria-label={`${r.full_name} — ${c.name}`}
                            />
                          ) : (
                            // Görüntüleme modunda boş kutu YOK: varsa işaret, yoksa boş
                            var_ && (
                              <Check
                                size={16}
                                strokeWidth={2.5}
                                className="mx-auto text-brand"
                                aria-label={`${r.full_name} — ${c.name}: var`}
                              />
                            )
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            );
          })}

          <tfoot className="sticky bottom-0">
            <tr className="border-t bg-background">
              <th className="sticky left-0 z-10 border-r bg-background p-0 text-left font-normal">
                <span className="block px-3 py-2 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  Toplam
                </span>
              </th>
              {sutunlar.map((c, i) => (
                <td key={c.code}
                    className={
                      "px-1 py-2 text-center font-medium " +
                      (i === data.tasks.length ? "border-l " : "") +
                      (vurgu.sutun === c.code ? "bg-accent" : "")
                    }>
                  {toplam(c)}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>

      <p className="mt-2 px-1 text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        Sütun altındaki sayı o yetkinliğe sahip aktif personel sayısıdır. Düşük bir sayı
        çizelgenin çözülememesinin en sık sebebidir.
      </p>

      {/* Kayıtsız çıkış uyarısı */}
      <Dialog open={uyari} onOpenChange={setUyari}>
        <DialogContent className="sm:max-w-[360px]">
          <DialogHeader>
            <DialogTitle style={{ fontSize: "var(--text-base)" }}>Kaydedilmemiş değişiklik</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            Vazgeçerseniz yaptığınız işaretlemeler kaybolur.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUyari(false)}>Düzenlemeye dön</Button>
            <Button onClick={() => { setUyari(false); setDuzenle(false); setTaslak(new Map()); }}>
              Vazgeç
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

const Baslik = () => (
  <h1 className="mb-4" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
    Yetkinlik Matrisi
  </h1>
);
