"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";


import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import {
  IZIN_TURU, MUSAITLIK_TURU, basHarf, bugun, tarih,
  type PersonDetail, type PersonRow,
} from "@/lib/personel";
import { Kunye } from "./Kunye";
import { Alan, Bolum, Bos, EkleDugmesi, Hata, Ikili, SatirKart } from "./parcalar";

/** E-04 sağ panel: Künye · Sözleşme · Müsaitlik · Devamsızlık · Uyumsuzluk. */
export function DetayPaneli({
  staffId, herkes, onKapat,
}: { staffId: number | null; herkes: PersonRow[]; onKapat: () => void }) {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["person", staffId],
    queryFn: () => api<PersonDetail>(`/people/${staffId}`),
    enabled: staffId !== null,
  });

  const tazele = (yeni: PersonDetail) => {
    qc.setQueryData(["person", staffId], yeni);
    qc.invalidateQueries({ queryKey: ["people"] });
  };

  return (
    <Sheet open={staffId !== null} onOpenChange={(a) => !a && onKapat()}>
      <SheetContent className="flex w-[600px] flex-col gap-0 p-0 sm:max-w-[600px]">
        <SheetHeader className="border-b p-6">
          <div className="flex items-center gap-3">
            <span
              aria-hidden
              className="flex size-11 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
              style={{ fontSize: "var(--text-base)", fontWeight: 600 }}
            >
              {data ? basHarf(data.full_name) : ""}
            </span>
            <div className="min-w-0">
              <SheetTitle style={{ fontSize: "var(--text-base)" }}>
                {data?.full_name ?? "…"}
              </SheetTitle>
              <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                {data?.role_name}
              </span>
            </div>
          </div>

          {data && (
            <div className="mt-2 flex flex-wrap gap-1">
              <Badge variant="secondary" className="h-5 rounded-sm px-1.5 font-normal"
                     style={{ fontSize: "var(--text-xs)" }}>
                {data.eligibility_label}
              </Badge>
              {data.status_label && (
                <Badge variant="secondary" className="h-5 rounded-sm px-1.5 font-normal"
                       style={{ fontSize: "var(--text-xs)" }}>
                  {data.status_label}
                </Badge>
              )}
              {data.sicil_no && (
                <Badge variant="secondary" className="h-5 rounded-sm px-1.5 font-normal"
                       style={{ fontSize: "var(--text-xs)" }}>
                  Sicil {data.sicil_no}
                </Badge>
              )}
            </div>
          )}
        </SheetHeader>

        {data && (
          <Tabs defaultValue="kunye" className="flex min-h-0 flex-1 flex-col">
            {/* Sekmeler kesilmesin: dar panelde yatay kaydırılır */}
            {/* Sade metin sekmeler, hepsi tek satırda. Yatay kaydırma YOK. */}
            <TabsList className="mx-6 mt-4 h-auto w-[calc(100%-3rem)] justify-start gap-1 rounded-none border-b bg-transparent p-0">
              {[
                ["kunye", "Künye"], ["sozlesme", "Sözleşme"], ["musaitlik", "Müsaitlik"],
                ["devamsizlik", "İzinler"], ["uyumsuzluk", "Uyumsuzluk"],
              ].map(([deger, ad]) => (
                <TabsTrigger
                  key={deger}
                  value={deger}
                  className="rounded-none border-b-2 border-transparent bg-transparent px-2 pb-2 pt-1 data-[state=active]:border-brand data-[state=active]:bg-transparent data-[state=active]:shadow-none"
                >
                  {ad}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="kunye" className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              <Kunye kisi={data} herkes={herkes} onKaydet={tazele} onSilindi={onKapat} />
            </TabsContent>

            <TabsContent value="sozlesme" className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              <Sozlesme kisi={data} onKaydet={tazele} />
            </TabsContent>

            <TabsContent value="musaitlik" className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              <Musaitlik kisi={data} onKaydet={tazele} />
            </TabsContent>

            <TabsContent value="devamsizlik" className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              <Devamsizlik kisi={data} onKaydet={tazele} />
            </TabsContent>

            <TabsContent value="uyumsuzluk" className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              <Uyumsuzluk kisi={data} herkes={herkes} onKaydet={tazele} />
            </TabsContent>
          </Tabs>
        )}
      </SheetContent>
    </Sheet>
  );
}

/* ------------------------------------------------------------ Sözleşme */
function Sozlesme({ kisi, onKaydet }: { kisi: PersonDetail; onKaydet: (d: PersonDetail) => void }) {
  const [ac, setAc] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<number | null>(null);
  const [form, setForm] = useState({ valid_from: bugun(), valid_to: "", monthly_target_hours: "" });

  const sil = useMutation({
    mutationFn: (id: number) =>
      api<PersonDetail>(`/people/${kisi.id}/contracts/${id}`, { method: "DELETE" }),
    onSuccess: onKaydet,
  });

  const ekle = useMutation({
    mutationFn: () =>
      // Aynı form hem ekleme hem düzenleme için: yalnız yol ve yöntem değişiyor.
      api<PersonDetail>(
        duzenlenen ? `/people/${kisi.id}/contracts/${duzenlenen}` : `/people/${kisi.id}/contracts`,
        {
        method: duzenlenen ? "PATCH" : "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          valid_from: form.valid_from,
          valid_to: form.valid_to || null,
          monthly_target_hours: form.monthly_target_hours ? Number(form.monthly_target_hours) : null,
        }),
        },
      ),
    onSuccess: (d) => { onKaydet(d); setAc(false); setDuzenlenen(null); },
  });

  return (
    <div className="grid gap-2">
      {(kisi.contracts ?? []).length === 0 && <Bos>Sözleşme kaydı yok.</Bos>}
      {(kisi.contracts ?? []).map((c) => (
        <SatirKart
          key={c.id}
          onSil={() => sil.mutate(c.id)}
          onDuzenle={() => {
            setForm({
              valid_from: c.valid_from, valid_to: c.valid_to ?? "",
              monthly_target_hours: c.monthly_target_hours ? String(c.monthly_target_hours) : "",
            });
            setDuzenlenen(c.id);
            setAc(true);
          }}
        >
          <span className="flex items-baseline justify-between gap-3">
            <span>{tarih(c.valid_from)} – {c.valid_to ? tarih(c.valid_to) : "açık"}</span>
            <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {c.monthly_target_hours ? `${c.monthly_target_hours} sa` : "kural varsayılanı"}
            </span>
          </span>
        </SatirKart>
      ))}

      {ac ? (
        <div className="grid gap-2 rounded-md border p-3">
          <Ikili>
            <Alan etiket="Başlangıç">
              <Input type="date" value={form.valid_from}
                     onChange={(e) => setForm({ ...form, valid_from: e.target.value })} />
            </Alan>
            <Alan etiket="Bitiş">
              <Input type="date" value={form.valid_to}
                     onChange={(e) => setForm({ ...form, valid_to: e.target.value })} />
            </Alan>
          </Ikili>
          <Alan etiket="Aylık hedef saat">
            <Input type="number" placeholder="boşsa kural varsayılanı"
                   value={form.monthly_target_hours}
                   onChange={(e) => setForm({ ...form, monthly_target_hours: e.target.value })} />
          </Alan>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => ekle.mutate()} disabled={ekle.isPending}>
              {duzenlenen ? "Güncelle" : "Ekle"}
            </Button>
            <Button size="sm" variant="outline"
                    onClick={() => { setAc(false); setDuzenlenen(null); }}>İptal</Button>
          </div>
          {ekle.isError && <Hata>{(ekle.error as Error).message}</Hata>}
        </div>
      ) : (
        <EkleDugmesi onClick={() => { setDuzenlenen(null); setAc(true); }}>Sözleşme ekle</EkleDugmesi>
      )}
    </div>
  );
}

/* ----------------------------------------------------------- Müsaitlik */
function Musaitlik({ kisi, onKaydet }: { kisi: PersonDetail; onKaydet: (d: PersonDetail) => void }) {
  const [ac, setAc] = useState(false);
  const [form, setForm] = useState({ target_date: bugun(), rule_type: "off_talebi" });

  const ekle = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}/availability`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify(form),
      }),
    onSuccess: (d) => { onKaydet(d); setAc(false); },
  });
  const sil = useMutation({
    mutationFn: (id: number) =>
      api<PersonDetail>(`/people/${kisi.id}/availability/${id}`, { method: "DELETE" }),
    onSuccess: onKaydet,
  });

  return (
    <div className="grid gap-2">
      <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        Çalışma tipi (gündüz / gece) Künye sekmesinde. Burada gün bazlı istekler durur.
      </p>
      {(kisi.availability ?? []).length === 0 && <Bos>Gün bazlı istek yok.</Bos>}
      {(kisi.availability ?? []).map((m) => (
        <SatirKart key={m.id} onSil={() => sil.mutate(m.id)}>
          {tarih(m.target_date)} · {m.type_label}
        </SatirKart>
      ))}

      {ac ? (
        <div className="grid gap-2 rounded-md border p-3">
          <Ikili>
            <Alan etiket="Gün">
              <Input type="date" value={form.target_date}
                     onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
            </Alan>
            <Alan etiket="Tür">
              <select className="h-9 w-full rounded-md border bg-card px-2" value={form.rule_type}
                      onChange={(e) => setForm({ ...form, rule_type: e.target.value })}>
                {MUSAITLIK_TURU.map((t) => <option key={t.deger} value={t.deger}>{t.ad}</option>)}
              </select>
            </Alan>
          </Ikili>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => ekle.mutate()} disabled={ekle.isPending}>Ekle</Button>
            <Button size="sm" variant="outline" onClick={() => setAc(false)}>İptal</Button>
          </div>
        </div>
      ) : (
        <EkleDugmesi onClick={() => setAc(true)}>İstek ekle</EkleDugmesi>
      )}
    </div>
  );
}

/* --------------------------------------------------------- Devamsızlık */
function Devamsizlik({ kisi, onKaydet }: { kisi: PersonDetail; onKaydet: (d: PersonDetail) => void }) {
  const [ac, setAc] = useState(false);
  const [form, setForm] = useState({ start: bugun(), end: bugun(), absence_type: "yillik_izin" });

  const ekle = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}/absences`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify(form),
      }),
    onSuccess: (d) => { onKaydet(d); setAc(false); },
  });
  const sil = useMutation({
    mutationFn: (id: number) =>
      api<PersonDetail>(`/people/${kisi.id}/absences/${id}`, { method: "DELETE" }),
    onSuccess: onKaydet,
  });

  return (
    <div className="grid gap-2">
      {(kisi.absences ?? []).length === 0 && <Bos>Devamsızlık kaydı yok.</Bos>}
      {(kisi.absences ?? []).map((a) => (
        <SatirKart key={a.id} onSil={() => sil.mutate(a.id)}>
          {tarih(a.start)} – {tarih(a.end)} · {a.type_label}
        </SatirKart>
      ))}

      {ac ? (
        <div className="grid gap-2 rounded-md border p-3">
          <Ikili>
            <Alan etiket="Başlangıç">
              <Input type="date" value={form.start}
                     onChange={(e) => setForm({ ...form, start: e.target.value })} />
            </Alan>
            <Alan etiket="Bitiş">
              <Input type="date" value={form.end}
                     onChange={(e) => setForm({ ...form, end: e.target.value })} />
            </Alan>
          </Ikili>
          <Alan etiket="Tür">
            <select className="h-9 w-full rounded-md border bg-card px-2" value={form.absence_type}
                    onChange={(e) => setForm({ ...form, absence_type: e.target.value })}>
              {IZIN_TURU.map((t) => <option key={t.deger} value={t.deger}>{t.ad}</option>)}
            </select>
          </Alan>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => ekle.mutate()} disabled={ekle.isPending}>Ekle</Button>
            <Button size="sm" variant="outline" onClick={() => setAc(false)}>İptal</Button>
          </div>
          {ekle.isError && <Hata>{(ekle.error as Error).message}</Hata>}
        </div>
      ) : (
        <EkleDugmesi onClick={() => setAc(true)}>Devamsızlık ekle</EkleDugmesi>
      )}
    </div>
  );
}

/* ---------------------------------------------------------- Uyumsuzluk */
function Uyumsuzluk({
  kisi, herkes, onKaydet,
}: { kisi: PersonDetail; herkes: PersonRow[]; onKaydet: (d: PersonDetail) => void }) {
  const [ac, setAc] = useState(false);
  const secilebilir = herkes.filter(
    (h) => h.id !== kisi.id && !(kisi.conflicts ?? []).some((c) => c.other_staff_id === h.id),
  );
  const [secili, setSecili] = useState(() => String(secilebilir[0]?.id ?? ""));

  const ekle = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}/conflicts`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ other_staff_id: Number(secili) }),
      }),
    onSuccess: (d) => { onKaydet(d); setAc(false); },
  });
  const sil = useMutation({
    mutationFn: (id: number) =>
      api<PersonDetail>(`/people/${kisi.id}/conflicts/${id}`, { method: "DELETE" }),
    onSuccess: onKaydet,
  });

  return (
    <div className="grid gap-2">
      <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        Aynı vardiyaya yazılırlarsa ceza uygulanır (C-013, soft kural).
      </p>
      {(kisi.conflicts ?? []).length === 0 && <Bos>Uyumsuz kişi yok.</Bos>}
      {(kisi.conflicts ?? []).map((c) => (
        <SatirKart key={c.other_staff_id} onSil={() => sil.mutate(c.other_staff_id)}>
          {c.other_name}
        </SatirKart>
      ))}

      {ac ? (
        <div className="grid gap-2 rounded-md border p-3">
          <Alan etiket="Kişi">
            <select className="h-9 w-full rounded-md border bg-card px-2" value={secili}
                    onChange={(e) => setSecili(e.target.value)}>
              {secilebilir.map((h) => <option key={h.id} value={h.id}>{h.full_name}</option>)}
            </select>
          </Alan>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => ekle.mutate()} disabled={ekle.isPending || !secili}>
              Ekle
            </Button>
            <Button size="sm" variant="outline" onClick={() => setAc(false)}>İptal</Button>
          </div>
        </div>
      ) : (
        secilebilir.length > 0 && <EkleDugmesi onClick={() => setAc(true)}>Kişi ekle</EkleDugmesi>
      )}
    </div>
  );
}
