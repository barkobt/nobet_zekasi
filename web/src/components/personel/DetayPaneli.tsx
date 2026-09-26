"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import {
  CALISMA_TIPI, IZIN_TURU, MUSAITLIK_TURU, bugun, tarih,
  type PersonDetail, type PersonRow, type Role,
} from "@/lib/personel";

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
  const { data: roller } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api<Role[]>("/people/roles"),
  });

  const tazele = (yeni: PersonDetail) => {
    qc.setQueryData(["person", staffId], yeni);
    qc.invalidateQueries({ queryKey: ["people"] });
  };

  return (
    <Sheet open={staffId !== null} onOpenChange={(a) => !a && onKapat()}>
      <SheetContent className="w-[460px] sm:max-w-[460px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle style={{ fontSize: "var(--text-base)" }}>
            {data?.full_name ?? "…"}
          </SheetTitle>
          {data && (
            <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {data.role_name}
              {data.status_label && ` · ${data.status_label}`}
            </span>
          )}
        </SheetHeader>

        {data && (
          <Tabs defaultValue="kunye" className="mt-4 px-4 pb-6">
            <TabsList className="w-full">
              <TabsTrigger value="kunye">Künye</TabsTrigger>
              <TabsTrigger value="sozlesme">Sözleşme</TabsTrigger>
              <TabsTrigger value="musaitlik">Müsaitlik</TabsTrigger>
              <TabsTrigger value="devamsizlik">Devamsızlık</TabsTrigger>
              <TabsTrigger value="uyumsuzluk">Uyumsuzluk</TabsTrigger>
            </TabsList>

            <TabsContent value="kunye" className="mt-4">
              <Kunye kisi={data} roller={roller ?? []} onKaydet={tazele} />
            </TabsContent>

            <TabsContent value="sozlesme" className="mt-4">
              <Sozlesme kisi={data} onKaydet={tazele} />
            </TabsContent>

            <TabsContent value="musaitlik" className="mt-4">
              <Musaitlik kisi={data} onKaydet={tazele} />
            </TabsContent>

            <TabsContent value="devamsizlik" className="mt-4">
              <Devamsizlik kisi={data} onKaydet={tazele} />
            </TabsContent>

            <TabsContent value="uyumsuzluk" className="mt-4">
              <Uyumsuzluk kisi={data} herkes={herkes} onKaydet={tazele} />
            </TabsContent>
          </Tabs>
        )}
      </SheetContent>
    </Sheet>
  );
}

/* ---------------------------------------------------------------- Künye */
function Kunye({
  kisi, roller, onKaydet,
}: { kisi: PersonDetail; roller: Role[]; onKaydet: (d: PersonDetail) => void }) {
  const [form, setForm] = useState({
    first_name: kisi.first_name, last_name: kisi.last_name,
    sicil_no: kisi.sicil_no ?? "", role_code: kisi.role_code,
    shift_eligibility: kisi.shift_eligibility, note: kisi.note ?? "",
  });

  const kaydet = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...form, sicil_no: form.sicil_no || null }),
      }),
    onSuccess: onKaydet,
  });

  return (
    <div className="grid gap-3">
      <Ikili>
        <Alan etiket="Ad">
          <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
        </Alan>
        <Alan etiket="Soyad">
          <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        </Alan>
      </Ikili>

      <Ikili>
        <Alan etiket="Sicil">
          {/* Boşsa boş kalır; uydurma değer yazılmaz (DESIGN §7) */}
          <Input value={form.sicil_no} placeholder="—"
                 onChange={(e) => setForm({ ...form, sicil_no: e.target.value })} />
        </Alan>
        <Alan etiket="Rol">
          <select
            className="h-9 w-full rounded-md border bg-card px-2"
            value={form.role_code}
            onChange={(e) => setForm({ ...form, role_code: e.target.value })}
          >
            {roller.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
          </select>
        </Alan>
      </Ikili>

      <Alan etiket="Çalışma tipi">
        <select
          className="h-9 w-full rounded-md border bg-card px-2"
          value={form.shift_eligibility}
          onChange={(e) => setForm({ ...form, shift_eligibility: e.target.value as never })}
        >
          {CALISMA_TIPI.map((c) => <option key={c.deger} value={c.deger}>{c.ad}</option>)}
        </select>
      </Alan>

      <Alan etiket="Not">
        <Input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
      </Alan>

      {kisi.buddy_name && (
        <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          Eğitmen: {kisi.buddy_name}
        </p>
      )}

      <Button onClick={() => kaydet.mutate()} disabled={kaydet.isPending} className="mt-1">
        {kaydet.isPending ? "Kaydediliyor…" : "Kaydet"}
      </Button>
      {kaydet.isError && <Hata>{(kaydet.error as Error).message}</Hata>}
    </div>
  );
}

/* ------------------------------------------------------------ Sözleşme */
function Sozlesme({ kisi, onKaydet }: { kisi: PersonDetail; onKaydet: (d: PersonDetail) => void }) {
  const [ac, setAc] = useState(false);
  const [form, setForm] = useState({ valid_from: bugun(), valid_to: "", monthly_target_hours: "" });

  const ekle = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}/contracts`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          valid_from: form.valid_from,
          valid_to: form.valid_to || null,
          monthly_target_hours: form.monthly_target_hours ? Number(form.monthly_target_hours) : null,
        }),
      }),
    onSuccess: (d) => { onKaydet(d); setAc(false); },
  });

  return (
    <div className="grid gap-2">
      {(kisi.contracts ?? []).length === 0 && <Bos>Sözleşme kaydı yok.</Bos>}
      {(kisi.contracts ?? []).map((c) => (
        <div key={c.id} className="rounded-md border px-3 py-2">
          <div className="flex items-baseline justify-between">
            <span>{tarih(c.valid_from)} – {c.valid_to ? tarih(c.valid_to) : "açık"}</span>
            <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
              {c.monthly_target_hours ? `${c.monthly_target_hours} sa` : "kural varsayılanı"}
            </span>
          </div>
        </div>
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
            <Button size="sm" onClick={() => ekle.mutate()} disabled={ekle.isPending}>Ekle</Button>
            <Button size="sm" variant="outline" onClick={() => setAc(false)}>İptal</Button>
          </div>
          {ekle.isError && <Hata>{(ekle.error as Error).message}</Hata>}
        </div>
      ) : (
        <EkleDugmesi onClick={() => setAc(true)}>Sözleşme ekle</EkleDugmesi>
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

/* ------------------------------------------------------ küçük parçalar */
const Ikili = ({ children }: { children: React.ReactNode }) => (
  <div className="grid grid-cols-2 gap-2">{children}</div>
);

function Alan({ etiket, children }: { etiket: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <Label style={{ fontSize: "var(--text-xs)" }}>{etiket}</Label>
      {children}
    </div>
  );
}

const Bos = ({ children }: { children: React.ReactNode }) => (
  <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>{children}</p>
);

const Hata = ({ children }: { children: React.ReactNode }) => (
  <p className="text-danger" style={{ fontSize: "var(--text-xs)" }}>{children}</p>
);

function SatirKart({ children, onSil }: { children: React.ReactNode; onSil: () => void }) {
  return (
    <div className="flex items-center justify-between rounded-md border px-3 py-2">
      <span>{children}</span>
      <Button variant="ghost" size="icon" onClick={onSil} aria-label="Sil">
        <Trash2 size={16} strokeWidth={1.75} />
      </Button>
    </div>
  );
}

function EkleDugmesi({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <Button variant="outline" size="sm" onClick={onClick} className="justify-start">
      <Plus size={16} strokeWidth={1.75} />
      {children}
    </Button>
  );
}
