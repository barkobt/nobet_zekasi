"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, sunucuAciklamasi } from "@/lib/api";
import {
  ISTEK_GUCU, ISTEK_TURU, IZIN_TURU, basHarf, bugun, tarih,
  type PersonDetail, type PersonRow,
} from "@/lib/personel";
import { Kunye } from "./Kunye";
import { SilmeBolumu } from "./SilmeBolumu";
import { Alan, Bos, EkleDugmesi, Hata, Ikili, SatirKart } from "./parcalar";

/** E-04 detay paneli: Yetkinlikler · Sözleşme · Devamsızlık · İstekler · Uyumsuzluk · Haftalık desen. */
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
    // Yetkinlik, istek ve izin değişikliği çizelgeyi ve matrisi de etkiler.
    qc.invalidateQueries({ queryKey: ["schedule"] });
    qc.invalidateQueries({ queryKey: ["competency-matrix"] });
  };

  if (staffId === null) return null;

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-lg border bg-card">
      {/* Başlık: sicil · AD SOYAD · Düzenle · Sil */}
      <div className="flex items-start justify-between gap-3 border-b px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden
            className="flex size-11 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
            style={{ fontSize: "var(--text-base)", fontWeight: 600 }}
          >
            {data ? basHarf(data.full_name) : ""}
          </span>
          <div className="min-w-0">
            <div className="flex items-baseline gap-2">
              {data?.sicil_no && (
                <span className="text-muted-foreground tabular-nums"
                      style={{ fontSize: "var(--text-xs)" }}>
                  {data.sicil_no}
                </span>
              )}
              <h2 className="truncate" style={{ fontSize: "var(--text-base)", fontWeight: 600 }}>
                {data?.full_name ?? "…"}
              </h2>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                {data?.role_name}
              </span>
              {data && (
                <Badge variant="secondary" className="h-5 rounded-sm px-1.5 font-normal"
                       style={{ fontSize: "var(--text-xs)" }}>
                  {data.eligibility_label}
                </Badge>
              )}
              {data?.status_label && (
                <Badge variant="secondary" className="h-5 rounded-sm px-1.5 font-normal"
                       style={{ fontSize: "var(--text-xs)" }}>
                  {data.status_label}
                </Badge>
              )}
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {data && <DuzenlePenceresi kisi={data} herkes={herkes} onKaydet={tazele} />}
          {data && <SilmeBolumu kisi={data} onSilindi={onKapat} kompakt />}
          <Button variant="ghost" size="icon" onClick={onKapat} aria-label="Detayı kapat">
            <X size={16} strokeWidth={1.75} />
          </Button>
        </div>
      </div>

      {data && (
        <Tabs defaultValue="yetkinlik" className="flex min-h-0 flex-1 flex-col">
          <TabsList className="mx-5 h-auto w-[calc(100%-2.5rem)] justify-start gap-4 rounded-none border-b bg-transparent p-0">
            {[
              ["yetkinlik", "Yetkinlikler"], ["sozlesme", "Sözleşme"],
              ["devamsizlik", "Devamsızlık"], ["istekler", "İstekler"],
              ["uyumsuzluk", "Uyumsuzluk"],
              // Desen sekmesi yalnız deseni OLANDA görünür: 20 kişiden 2'sinde
              // dolu, hepsine boş sekme göstermek gürültü olurdu.
              ...((data.weekly_pattern ?? []).length > 0
                ? [["desen", "Haftalık desen"]]
                : []),
            ].map(([deger, ad]) => (
              <TabsTrigger
                key={deger}
                value={deger}
                className="whitespace-nowrap rounded-none border-b-2 border-transparent bg-transparent px-1 pb-2 pt-2 data-[state=active]:border-brand data-[state=active]:bg-transparent data-[state=active]:shadow-none"
              >
                {ad}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="yetkinlik" className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <Yetkinlikler kisi={data} onKaydet={tazele} />
          </TabsContent>
          <TabsContent value="sozlesme" className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <Sozlesme kisi={data} onKaydet={tazele} />
          </TabsContent>
          <TabsContent value="devamsizlik" className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <Devamsizlik kisi={data} onKaydet={tazele} />
          </TabsContent>
          <TabsContent value="istekler" className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <Istekler kisi={data} onKaydet={tazele} />
          </TabsContent>
          <TabsContent value="uyumsuzluk" className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <Uyumsuzluk kisi={data} herkes={herkes} onKaydet={tazele} />
          </TabsContent>
          <TabsContent value="desen" className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <HaftalikDesen kisi={data} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}

/* ------------------------------------------------------- Düzenle penceresi */
function DuzenlePenceresi({
  kisi, herkes, onKaydet,
}: { kisi: PersonDetail; herkes: PersonRow[]; onKaydet: (d: PersonDetail) => void }) {
  const [ac, setAc] = useState(false);
  return (
    <Dialog open={ac} onOpenChange={setAc}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Pencil size={14} strokeWidth={1.75} />
          Düzenle
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] max-w-[560px] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{kisi.full_name}</DialogTitle>
        </DialogHeader>
        <Kunye
          kisi={kisi}
          herkes={herkes}
          onKaydet={(d) => { onKaydet(d); setAc(false); }}
        />
      </DialogContent>
    </Dialog>
  );
}

/* ---------------------------------------------------------- Yetkinlikler */
function Yetkinlikler({
  kisi, onKaydet,
}: { kisi: PersonDetail; onKaydet: (d: PersonDetail) => void }) {
  // Seçim yerel: kullanıcı birkaç kutu işaretleyip bir kez kaydeder.
  const mevcut = (kisi.competencies ?? []).filter((c) => c.has).map((c) => c.code);
  const [secim, setSecim] = useState<string[] | null>(null);
  const liste = secim ?? mevcut;

  const kaydet = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}/competencies`, {
        method: "PUT", body: JSON.stringify({ codes: liste }),
      }),
    onSuccess: (d) => { onKaydet(d); setSecim(null); },
  });

  const degisti =
    secim !== null &&
    (secim.length !== mevcut.length || secim.some((k) => !mevcut.includes(k)));

  const gruplar = ["Görevler", "Yetkiler"];

  return (
    <div className="grid gap-4">
      {gruplar.map((g) => {
        const uyeler = (kisi.competencies ?? []).filter((c) => c.group_label === g);
        if (uyeler.length === 0) return null;
        return (
          <div key={g} className="grid gap-2">
            <span className="text-muted-foreground"
                  style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}>
              {g.toLocaleUpperCase("tr")}
            </span>
            {uyeler.map((c) => (
              <label key={c.code} className="flex items-center gap-2.5">
                <Checkbox
                  checked={liste.includes(c.code)}
                  onCheckedChange={(v) =>
                    setSecim(
                      v ? [...liste, c.code] : liste.filter((k) => k !== c.code),
                    )
                  }
                />
                <span>{c.name}</span>
                <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {c.code}
                </span>
              </label>
            ))}
          </div>
        );
      })}

      <div className="flex gap-2">
        <Button size="sm" onClick={() => kaydet.mutate()} disabled={!degisti || kaydet.isPending}>
          {kaydet.isPending ? "Kaydediliyor…" : "Kaydet"}
        </Button>
        {degisti && (
          <Button size="sm" variant="outline" onClick={() => setSecim(null)}>Vazgeç</Button>
        )}
      </div>
      <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        Yetkinlik kaldırılınca solver o kişiye o görevi bir daha vermez; geçmiş
        çizelgelerdeki rozetler durur.
      </p>
    </div>
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
function Istekler({
  kisi, onKaydet,
}: { kisi: PersonDetail; onKaydet: (d: PersonDetail) => void }) {
  const [ac, setAc] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<number | null>(null);
  const [form, setForm] = useState({
    target_date: bugun(), end_date: "", rule_type: "BOS_GUN",
    strength: "MUMKUNSE", note: "",
  });

  const ekle = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}/availability`, {
        method: "POST",
        body: JSON.stringify({
          target_date: form.target_date,
          // Boş bırakılırsa tek gün: sunucu end_date yoksa target_date kullanıyor.
          end_date: form.end_date || null,
          rule_type: form.rule_type,
          strength: form.strength,
          note: form.note || null,
        }),
      }),
    onSuccess: (d) => { onKaydet(d); setAc(false); },
  });

  const guncelle = useMutation({
    mutationFn: (v: { id: number; alan: Record<string, string> }) =>
      api<PersonDetail>(`/people/${kisi.id}/availability/${v.id}`, {
        method: "PATCH", body: JSON.stringify(v.alan),
      }),
    onSuccess: (d) => { onKaydet(d); setDuzenlenen(null); },
  });

  const sil = useMutation({
    mutationFn: (id: number) =>
      api<PersonDetail>(`/people/${kisi.id}/availability/${id}`, { method: "DELETE" }),
    onSuccess: onKaydet,
  });

  const istekler = kisi.availability ?? [];

  return (
    <div className="grid gap-2">
      <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
        <strong className="font-medium">Kesin</strong> istek katı kuraldır, çözüm onu bozamaz.
        <strong className="font-medium"> Mümkünse</strong> tercihtir: karşılanamazsa
        çözüm teşhisinde &quot;karşılanamayan tercih&quot; olarak görünür.
      </p>

      {istekler.length === 0 && <Bos>Kayıtlı istek yok.</Bos>}

      {istekler.map((m) => (
        <div key={m.id} className="rounded-md border px-3 py-2">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <span className="font-medium">{m.summary}</span>
              <Badge variant="secondary" className="ml-2 h-5 rounded-sm px-1.5 font-normal"
                     style={{ fontSize: "var(--text-xs)" }}>
                {m.strength_label}
              </Badge>
              {m.note && (
                <p className="truncate text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                  {m.note}
                </p>
              )}
            </div>
            <div className="flex shrink-0 gap-1">
              <Button variant="ghost" size="icon"
                      onClick={() => setDuzenlenen(duzenlenen === m.id ? null : m.id)}
                      aria-label="İsteği düzenle">
                <Pencil size={14} strokeWidth={1.75} />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => sil.mutate(m.id)}
                      aria-label="İsteği sil">
                <Trash2 size={14} strokeWidth={1.75} />
              </Button>
            </div>
          </div>

          {duzenlenen === m.id && (
            <div className="mt-2 grid gap-2 border-t pt-2">
              <Ikili>
                <Alan etiket="Tür">
                  <select className="h-9 w-full rounded-md border bg-card px-2"
                          defaultValue={m.rule_type}
                          onChange={(e) =>
                            guncelle.mutate({ id: m.id, alan: { rule_type: e.target.value } })}>
                    {ISTEK_TURU.map((t) => <option key={t.deger} value={t.deger}>{t.ad}</option>)}
                  </select>
                </Alan>
                <Alan etiket="Güç">
                  <select className="h-9 w-full rounded-md border bg-card px-2"
                          defaultValue={m.strength}
                          onChange={(e) =>
                            guncelle.mutate({ id: m.id, alan: { strength: e.target.value } })}>
                    {ISTEK_GUCU.map((t) => <option key={t.deger} value={t.deger}>{t.ad}</option>)}
                  </select>
                </Alan>
              </Ikili>
            </div>
          )}
        </div>
      ))}

      {ac ? (
        <div className="grid gap-2 rounded-md border p-3">
          <Ikili>
            <Alan etiket="Başlangıç">
              <Input type="date" value={form.target_date}
                     onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
            </Alan>
            <Alan etiket="Bitiş (boşsa tek gün)">
              <Input type="date" value={form.end_date}
                     onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </Alan>
          </Ikili>
          <Ikili>
            <Alan etiket="Tür">
              <select className="h-9 w-full rounded-md border bg-card px-2" value={form.rule_type}
                      onChange={(e) => setForm({ ...form, rule_type: e.target.value })}>
                {ISTEK_TURU.map((t) => <option key={t.deger} value={t.deger}>{t.ad}</option>)}
              </select>
            </Alan>
            <Alan etiket="Güç">
              <select className="h-9 w-full rounded-md border bg-card px-2" value={form.strength}
                      onChange={(e) => setForm({ ...form, strength: e.target.value })}>
                {ISTEK_GUCU.map((t) => <option key={t.deger} value={t.deger}>{t.ad}</option>)}
              </select>
            </Alan>
          </Ikili>
          <Alan etiket="Not">
            <Input value={form.note} placeholder="isteğe bağlı"
                   onChange={(e) => setForm({ ...form, note: e.target.value })} />
          </Alan>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => ekle.mutate()} disabled={ekle.isPending}>Ekle</Button>
            <Button size="sm" variant="outline" onClick={() => setAc(false)}>İptal</Button>
          </div>
          {ekle.isError && (
            <p className="text-danger" style={{ fontSize: "var(--text-xs)" }} role="alert">
              {sunucuAciklamasi(ekle.error) ?? "İstek eklenemedi."}
            </p>
          )}
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

/**
 * Kişiye özel haftalık desen (migration 024). SALT OKUNUR.
 *
 * NEDEN düzenlenemez: desen değişmek, yayındaki çizelgeyi baştan çözmeyi
 * gerektirir. Buradan sessizce değiştirilirse ekranda duran çizelge kuralına
 * uymayan bir hâle düşer. Değişiklik bugün seed ile yapılıyor.
 */
function HaftalikDesen({ kisi }: { kisi: PersonDetail }) {
  const desen = kisi.weekly_pattern ?? [];
  if (desen.length === 0) return <Bos>Bu kişide haftalık sabit desen yok.</Bos>;

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Haftalık sabit program. Solver bu satırları kural olarak uygular; hafta
        Pazartesi–Pazar takvim haftasıdır.
      </p>
      <div className="overflow-hidden rounded-lg border">
        <table className="w-full" style={{ fontSize: "var(--text-sm)" }}>
          <thead>
            <tr className="border-b bg-muted/40 text-left text-muted-foreground">
              <th className="px-3 py-2 font-medium" style={{ fontSize: "var(--text-xs)" }}>Gün</th>
              <th className="px-3 py-2 font-medium" style={{ fontSize: "var(--text-xs)" }}>Kural</th>
              <th className="px-3 py-2 font-medium" style={{ fontSize: "var(--text-xs)" }}>Vardiya</th>
            </tr>
          </thead>
          <tbody>
            {desen.map((d) => (
              <tr key={d.isodow} className="border-b last:border-0">
                <td className="px-3 py-2" style={{ fontWeight: 500 }}>{d.day_label}</td>
                <td className="px-3 py-2">{d.kind_label}</td>
                <td className="px-3 py-2 text-muted-foreground">{d.shift_name ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
