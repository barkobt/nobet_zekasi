"use client";

import { Fragment, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { DetayPaneli } from "@/components/personel/DetayPaneli";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { CALISMA_TIPI, basHarf, type PersonDetail, type PersonRow, type Role } from "@/lib/personel";

export default function PersonelSayfasi() {
  const [arama, setArama] = useState("");
  const [rolFiltre, setRolFiltre] = useState("");
  const [tipFiltre, setTipFiltre] = useState("");
  const [secili, setSecili] = useState<number | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["people"],
    queryFn: () => api<PersonRow[]>("/people"),
  });

  // Arama ve filtreler istemcide: 20 kişi, sunucuya gitmeye değmez.
  const satirlar = useMemo(() => {
    const q = arama.trim().toLocaleLowerCase("tr");
    return (data ?? []).filter(
      (p) =>
        (!q || p.full_name.toLocaleLowerCase("tr").includes(q)
            || (p.sicil_no ?? "").toLocaleLowerCase("tr").includes(q)) &&
        (!rolFiltre || p.role_code === rolFiltre) &&
        (!tipFiltre || p.shift_eligibility === tipFiltre),
    );
  }, [data, arama, rolFiltre, tipFiltre]);

  const gruplar = useMemo(() => {
    // Yetkinlik Matrisi ile AYNI gruplama: iki ekran aynı zihinsel düzeni paylaşsın.
    const tanim: { ad: string; roller: string[] | null }[] = [
      { ad: "Sorumlu & Eğitim", roller: ["sorumlu_hemsire", "egitim_hemsire"] },
      { ad: "Ekip Liderleri", roller: ["shift_yetkilisi"] },
      { ad: "Hemşireler", roller: null },
    ];
    return tanim
      .map((g, i) => ({
        ad: g.ad,
        satirlar: satirlar.filter((p) =>
          g.roller ? g.roller.includes(p.role_code)
                   : !tanim.slice(0, i).some((o) => o.roller?.includes(p.role_code)),
        ),
      }))
      .filter((g) => g.satirlar.length > 0);
  }, [satirlar]);

  const roller = useMemo(() => {
    const m = new Map<string, string>();
    (data ?? []).forEach((p) => m.set(p.role_code, p.role_name));
    return [...m.entries()];
  }, [data]);

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Personel</h1>
        <YeniPersonel />
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search
            size={16}
            strokeWidth={1.75}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 opacity-50"
          />
          <Input
            value={arama}
            onChange={(e) => setArama(e.target.value)}
            placeholder="Ad veya sicil ara"
            className="h-9 w-[220px] pl-8"
            aria-label="Personel ara"
          />
        </div>

        <select
          className="h-9 rounded-md border bg-card px-2 text-muted-foreground"
          value={rolFiltre}
          onChange={(e) => setRolFiltre(e.target.value)}
          aria-label="Rol filtresi"
        >
          <option value="">Tüm roller</option>
          {roller.map(([kod, ad]) => <option key={kod} value={kod}>{ad}</option>)}
        </select>

        <select
          className="h-9 rounded-md border bg-card px-2 text-muted-foreground"
          value={tipFiltre}
          onChange={(e) => setTipFiltre(e.target.value)}
          aria-label="Çalışma tipi filtresi"
        >
          <option value="">Tüm çalışma tipleri</option>
          {CALISMA_TIPI.map((c) => <option key={c.deger} value={c.deger}>{c.ad}</option>)}
        </select>

        {satirlar.length !== (data?.length ?? 0) && (
          <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            {satirlar.length} / {data?.length} kişi
          </span>
        )}
      </div>

      <div className="rounded-lg border bg-card">
        {error ? (
          <p className="p-6 text-danger">Personel listesi alınamadı.</p>
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : satirlar.length === 0 ? (
          <p className="p-6 text-muted-foreground">Eşleşen kişi yok.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[280px]">Ad Soyad</TableHead>
                <TableHead className="w-[220px]">Rol</TableHead>
                <TableHead className="w-[160px]">Çalışma tipi</TableHead>
                <TableHead>Durum</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* Sicil, aylık hedef ve sözleşme tablodan çıktı: herkeste aynı ya da boş.
                  İkisi de detay panelinde duruyor (26.09 kararı). */}
              {gruplar.map((grup) => (
                <Fragment key={grup.ad}>
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={4} className="h-9 bg-background py-0">
                      <span
                        className="text-muted-foreground"
                        style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
                      >
                        {grup.ad.toLocaleUpperCase("tr")}
                        <span className="ml-1.5 normal-case">({grup.satirlar.length})</span>
                      </span>
                    </TableCell>
                  </TableRow>

                  {grup.satirlar.map((p) => (
                    <TableRow
                      key={p.id}
                      className="h-11 cursor-pointer"
                      onClick={() => setSecili(p.id)}
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setSecili(p.id)}
                    >
                      <TableCell>
                        <span className="flex items-center gap-2.5">
                          <span
                            aria-hidden
                            className="flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
                            style={{ fontSize: "var(--text-xs)" }}
                          >
                            {basHarf(p.full_name)}
                          </span>
                          <span className="font-medium">{p.full_name}</span>
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{p.role_name}</TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className="h-5 rounded-sm px-1.5 font-normal"
                          style={{ fontSize: "var(--text-xs)" }}
                        >
                          {p.eligibility_label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{p.status_label}</TableCell>
                    </TableRow>
                  ))}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <DetayPaneli staffId={secili} herkes={data ?? []} onKapat={() => setSecili(null)} />
    </AppShell>
  );
}

function YeniPersonel() {
  const [acik, setAcik] = useState(false);
  const [form, setForm] = useState({
    first_name: "", last_name: "", sicil_no: "",
    role_code: "hemsire", shift_eligibility: "gunduz_gece",
  });
  const qc = useQueryClient();
  const { data: roller } = useQuery({
    queryKey: ["roles"], queryFn: () => api<Role[]>("/people/roles"),
  });

  const ekle = useMutation({
    mutationFn: () =>
      api<PersonDetail>("/people", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...form, sicil_no: form.sicil_no || null }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["people"] });
      setAcik(false);
      setForm({ first_name: "", last_name: "", sicil_no: "", role_code: "hemsire", shift_eligibility: "gunduz_gece" });
    },
  });

  const gecerli = form.first_name.trim() && form.last_name.trim();

  return (
    <Dialog open={acik} onOpenChange={setAcik}>
      <DialogTrigger asChild>
        <Button>
          <Plus size={16} strokeWidth={1.75} />
          Personel ekle
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle style={{ fontSize: "var(--text-base)" }}>Personel ekle</DialogTitle>
        </DialogHeader>

        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-1.5">
              <Label style={{ fontSize: "var(--text-xs)" }}>Ad</Label>
              <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </div>
            <div className="grid gap-1.5">
              <Label style={{ fontSize: "var(--text-xs)" }}>Soyad</Label>
              <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label style={{ fontSize: "var(--text-xs)" }}>Sicil</Label>
            <Input value={form.sicil_no} placeholder="isteğe bağlı"
                   onChange={(e) => setForm({ ...form, sicil_no: e.target.value })} />
          </div>
          <div className="grid gap-1.5">
            <Label style={{ fontSize: "var(--text-xs)" }}>Rol</Label>
            <select className="h-9 w-full rounded-md border bg-card px-2" value={form.role_code}
                    onChange={(e) => setForm({ ...form, role_code: e.target.value })}>
              {(roller ?? []).map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
            </select>
          </div>
          <div className="grid gap-1.5">
            <Label style={{ fontSize: "var(--text-xs)" }}>Çalışma tipi</Label>
            <select className="h-9 w-full rounded-md border bg-card px-2" value={form.shift_eligibility}
                    onChange={(e) => setForm({ ...form, shift_eligibility: e.target.value })}>
              {CALISMA_TIPI.map((c) => <option key={c.deger} value={c.deger}>{c.ad}</option>)}
            </select>
          </div>
          {ekle.isError && (
            <p className="text-danger" style={{ fontSize: "var(--text-xs)" }}>
              {(ekle.error as Error).message}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setAcik(false)}>İptal</Button>
          <Button onClick={() => ekle.mutate()} disabled={!gecerli || ekle.isPending}>
            {ekle.isPending ? "Ekleniyor…" : "Ekle"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
