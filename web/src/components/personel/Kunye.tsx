"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { CALISMA_TIPI, type PersonDetail, type PersonRow, type Role } from "@/lib/personel";
import { Alan, Bolum, Hata, Ikili } from "./parcalar";

type Form = {
  first_name: string; last_name: string; sicil_no: string; role_code: string;
  shift_eligibility: PersonDetail["shift_eligibility"];
  is_orientation: boolean; buddy_staff_id: string;
  is_active: boolean; note: string;
};

const formaCevir = (k: PersonDetail): Form => ({
  first_name: k.first_name, last_name: k.last_name, sicil_no: k.sicil_no ?? "",
  role_code: k.role_code, shift_eligibility: k.shift_eligibility,
  is_orientation: k.is_orientation, buddy_staff_id: k.buddy_staff_id ? String(k.buddy_staff_id) : "",
  is_active: k.is_active, note: k.note ?? "",
});

export function Kunye({
  kisi, herkes, onKaydet,
}: {
  kisi: PersonDetail;
  herkes: PersonRow[];
  onKaydet: (d: PersonDetail) => void;
}) {
  const [form, setForm] = useState<Form>(() => formaCevir(kisi));
  const baslangic = JSON.stringify(formaCevir(kisi));
  const degisti = JSON.stringify(form) !== baslangic;

  // Form sıfırlaması için effect YOK: bileşen artık Düzenle penceresinin içinde,
  // pencere her açılışta yeniden kuruluyor ve form o kişiyle başlıyor.

  const { data: roller } = useQuery({
    queryKey: ["roles"], queryFn: () => api<Role[]>("/people/roles"),
  });

  const kaydet = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/people/${kisi.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          ...form,
          sicil_no: form.sicil_no.trim() || null,
          buddy_staff_id: form.buddy_staff_id ? Number(form.buddy_staff_id) : null,
        }),
      }),
    onSuccess: onKaydet,
  });

  const guncelle = (y: Partial<Form>) => setForm((f) => ({ ...f, ...y }));

  return (
    <div className="flex min-h-full flex-col">
      <div className="grid gap-6">
        <Bolum baslik="Kimlik">
          <Ikili>
            <Alan etiket="Ad">
              <Input value={form.first_name} onChange={(e) => guncelle({ first_name: e.target.value })} />
            </Alan>
            <Alan etiket="Soyad">
              <Input value={form.last_name} onChange={(e) => guncelle({ last_name: e.target.value })} />
            </Alan>
          </Ikili>
          <Ikili>
            <Alan etiket="Sicil">
              {/* Boşsa alan gerçekten boş: "—" bir DEĞER gibi görünüyordu */}
              <Input value={form.sicil_no} placeholder="Sicil no"
                     onChange={(e) => guncelle({ sicil_no: e.target.value })} />
            </Alan>
            <Alan etiket="Rol">
              <select className="h-9 w-full rounded-md border bg-card px-2"
                      value={form.role_code}
                      onChange={(e) => guncelle({ role_code: e.target.value })}>
                {(roller ?? []).map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
              </select>
            </Alan>
          </Ikili>
        </Bolum>

        <Bolum baslik="Çalışma">
          <Alan etiket="Çalışma tipi">
            <select className="h-9 w-full rounded-md border bg-card px-2"
                    value={form.shift_eligibility}
                    onChange={(e) => guncelle({ shift_eligibility: e.target.value as never })}>
              {CALISMA_TIPI.map((c) => <option key={c.deger} value={c.deger}>{c.ad}</option>)}
            </select>
          </Alan>

          <Anahtar
            etiket="Oryantasyonda"
            acik={form.is_orientation}
            onDegis={(v) => guncelle({ is_orientation: v, buddy_staff_id: v ? form.buddy_staff_id : "" })}
          />

          {/* Şema kuralı: oryantasyondaysa eğitmen zorunlu. Alan yalnız o zaman görünür. */}
          {form.is_orientation && (
            <Alan etiket="Eğitmen">
              <select className="h-9 w-full rounded-md border bg-card px-2"
                      value={form.buddy_staff_id}
                      onChange={(e) => guncelle({ buddy_staff_id: e.target.value })}>
                <option value="">Seçin</option>
                {herkes.filter((h) => h.id !== kisi.id).map((h) => (
                  <option key={h.id} value={h.id}>{h.full_name}</option>
                ))}
              </select>
            </Alan>
          )}
        </Bolum>

        <Bolum baslik="Durum">
          <Anahtar
            etiket="Aktif"
            acik={form.is_active}
            onDegis={(v) => guncelle({ is_active: v })}
            not={form.is_active ? undefined : "Pasif personel listelerden ve çözümden düşer."}
          />
        </Bolum>

        <Bolum baslik="Not">
          <Textarea
            rows={3}
            value={form.note}
            onChange={(e) => guncelle({ note: e.target.value })}
            placeholder="Serbest not"
          />
        </Bolum>

        {kaydet.isError && <Hata>{(kaydet.error as Error).message}</Hata>}
      </div>

      {/* Kaydet formun altında, akışın içinde. Eskiden yan panele göre
          "sticky bottom-0 -mx-6" idi; Düzenle penceresinde kaydırma kabı
          olmadığı için pencerenin ortasında asılı kalıyordu. */}
      <div className="mt-2 flex gap-2 border-t pt-4">
        <Button onClick={() => kaydet.mutate()} disabled={!degisti || kaydet.isPending}>
          {kaydet.isPending ? "Kaydediliyor…" : "Kaydet"}
        </Button>
        <Button variant="outline" onClick={() => setForm(formaCevir(kisi))} disabled={!degisti}>
          Vazgeç
        </Button>
      </div>
    </div>
  );
}

/**
 * Tek anahtar bileşeni — "Oryantasyonda" ve "Aktif" aynı görünsün diye.
 * Kapalı: açık gri zemin + beyaz topuz. Açık: --brand zemin.
 */
function Anahtar({
  etiket, acik, onDegis, not,
}: { etiket: string; acik: boolean; onDegis: (v: boolean) => void; not?: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <Label style={{ fontSize: "var(--text-base)" }}>{etiket}</Label>
        {not && (
          <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>{not}</p>
        )}
      </div>
      <Switch
        checked={acik}
        onCheckedChange={onDegis}
        aria-label={etiket}
        className="shrink-0 data-[state=checked]:bg-brand data-[state=unchecked]:bg-muted-foreground/35"
      />
    </div>
  );
}
